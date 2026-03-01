"""
Google Sheets Setup & Connection Test
======================================
1. Adds the regeneration_feedback tab (if missing)
2. Adds headers to video_submissions (if empty)
3. Tests reading genres, genre tabs, and writing submissions

Usage:
    python setup_and_test_sheets.py
"""

import json
from pathlib import Path

# --- CONFIG ---
SHEET_ID = "1w4teWGFkdX1VsMIdt3orIRkZ30-fHkfZOhW7w3Ck-QE"
READER_KEY = Path("reference-reader-key.json")
WRITER_KEY = Path("data-writer-key.json")

# Submission headers
VIDEO_HEADERS = [
    "user_hash", "genre", "script_text", "hook_pattern", "word_count",
    "duration", "views_14d", "retention_avg", "likes", "caption_style",
    "voice_id", "music_mood", "timestamp"
]
REGEN_HEADERS = [
    "user_hash", "genre", "complaint_type", "notes", "timestamp"
]


def get_service(key_path, readonly=True):
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"] if readonly else [
        "https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(str(key_path), scopes=scope)
    return build("sheets", "v4", credentials=creds)


def get_tab_names(service):
    meta = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    return [s["properties"]["title"] for s in meta["sheets"]]


def setup_submissions(service):
    """Add regeneration_feedback tab and headers if missing."""
    tabs = get_tab_names(service)
    print(f"\n📋 Current tabs: {tabs}")

    # 1. Add regeneration_feedback tab if missing
    if "regeneration_feedback" not in tabs:
        print("➕ Creating 'regeneration_feedback' tab...")
        service.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": "regeneration_feedback"}}}]}
        ).execute()
        # Add headers
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range="regeneration_feedback!A1",
            valueInputOption="RAW",
            body={"values": [REGEN_HEADERS]}
        ).execute()
        print("✅ regeneration_feedback tab created with headers")
    else:
        print("✅ regeneration_feedback tab already exists")

    # 2. Add headers to video_submissions if row 1 is empty
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="video_submissions!A1:M1"
    ).execute()
    existing = result.get("values", [[]])
    if not existing or not existing[0] or existing[0][0] == "":
        print("➕ Adding headers to video_submissions...")
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range="video_submissions!A1",
            valueInputOption="RAW",
            body={"values": [VIDEO_HEADERS]}
        ).execute()
        print("✅ video_submissions headers added")
    else:
        print(f"✅ video_submissions already has headers: {existing[0][:5]}...")


def test_reference_read(service):
    """Test reading genres and genre data from the 122-column tabs."""
    print("\n--- TEST 1: Read Suggested Genres ---")
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="🎯 Suggested Genres!A1:D20"
    ).execute()
    rows = result.get("values", [])
    print(f"✅ Found {len(rows)} rows (including header)")
    if len(rows) > 1:
        print(f"   Header: {rows[0]}")
        print(f"   First genre: {rows[1]}")

    # Find genre tabs
    tabs = get_tab_names(service)
    genre_tabs = [t for t in tabs if t.startswith("Genre")]
    print(f"\n--- TEST 2: Read Genre Tabs ({len(genre_tabs)} found) ---")

    for tab in genre_tabs:
        # Read first 2 rows — header + sample data
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=SHEET_ID,
                range=f"'{tab}'!A1:J2"
            ).execute()
            vals = result.get("values", [])
            if vals:
                print(f"✅ {tab}: {len(vals[0])} columns in header row")
                if len(vals) > 1:
                    print(f"   Sample data row 1: {vals[1][:4]}...")
                else:
                    print(f"   ⚠️  No data rows yet (header only)")
            else:
                print(f"⚠️  {tab}: Empty")
        except Exception as e:
            print(f"❌ {tab}: {e}")

    return True


def test_submission_write(service):
    """Test appending a row to video_submissions."""
    print("\n--- TEST 3: Write to video_submissions ---")
    test_row = [
        "test_hash_setup", "scary_stories", "Test script", "question",
        "100", "45", "0", "0", "0", "horror_red",
        "en-US-Neural2-D", "dark_ambient", "2026-03-01T20:00:00"
    ]
    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range="video_submissions!A:A",
        valueInputOption="RAW",
        body={"values": [test_row]}
    ).execute()
    print("✅ Test row appended to video_submissions")
    print("   (You can delete this test row later)")
    return True


def main():
    print("=" * 60)
    print("  YT Shorts Auto — Sheet Setup & Connection Test")
    print("=" * 60)

    # Check keys
    for path, name in [(READER_KEY, "Reader"), (WRITER_KEY, "Writer")]:
        if not path.exists():
            print(f"❌ {name} key not found: {path}")
            return
        data = json.loads(path.read_text())
        print(f"✅ {name}: {data['client_email']}")

    # Step 1: Setup with writer account (needs edit access)
    print("\n" + "=" * 60)
    print("  STEP 1: Setup (using writer account)")
    print("=" * 60)
    writer_svc = get_service(WRITER_KEY, readonly=False)
    setup_submissions(writer_svc)

    # Step 2: Test reads with reader account
    print("\n" + "=" * 60)
    print("  STEP 2: Read Test (using reader account)")
    print("=" * 60)
    reader_svc = get_service(READER_KEY, readonly=True)
    read_ok = test_reference_read(reader_svc)

    # Step 3: Test write with writer account
    print("\n" + "=" * 60)
    print("  STEP 3: Write Test (using writer account)")
    print("=" * 60)
    write_ok = test_submission_write(writer_svc)

    # Final tabs
    final_tabs = get_tab_names(writer_svc)

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Sheet ID: {SHEET_ID}")
    print(f"  Tabs: {final_tabs}")
    print(f"  Reference Read:    {'✅ PASS' if read_ok else '❌ FAIL'}")
    print(f"  Submissions Write: {'✅ PASS' if write_ok else '❌ FAIL'}")

    if read_ok and write_ok:
        print("\n  🎉 Everything works! Sheet is ready for development.")
    print("=" * 60)


if __name__ == "__main__":
    main()
