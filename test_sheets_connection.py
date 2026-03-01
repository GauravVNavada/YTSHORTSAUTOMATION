"""
Google Sheets Connection Test & Setup Script
=============================================
Run this to verify your GCP setup works correctly.

Usage:
    pip install google-api-python-client google-auth
    python test_sheets_connection.py
"""

import json
import sys
from pathlib import Path

# --- CONFIGURATION ---
# Single sheet with everything: genres (122 cols), Suggested Genres, video_submissions
REFERENCE_SHEET_ID = "1w4teWGFkdX1VsMIdt3orIRkZ30-fHkfZOhW7w3Ck-QE"
# Same sheet — submissions tab is inside the same spreadsheet
SUBMISSIONS_SHEET_ID = "1w4teWGFkdX1VsMIdt3orIRkZ30-fHkfZOhW7w3Ck-QE"

READER_KEY_PATH = Path("reference-reader-key.json")
WRITER_KEY_PATH = Path("data-writer-key.json")


def check_dependencies():
    """Check if required packages are installed."""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        print("✅ Dependencies installed")
        return True
    except ImportError:
        print("❌ Missing dependencies. Run:")
        print("   pip install google-api-python-client google-auth")
        return False


def check_key_files():
    """Verify service account key files exist and are valid JSON."""
    ok = True
    for path, name in [(READER_KEY_PATH, "Reference Reader"), (WRITER_KEY_PATH, "Data Writer")]:
        if not path.exists():
            print(f"❌ {name} key not found: {path}")
            ok = False
        else:
            try:
                data = json.loads(path.read_text())
                email = data.get("client_email", "???")
                print(f"✅ {name} key valid — {email}")
            except json.JSONDecodeError:
                print(f"❌ {name} key is not valid JSON")
                ok = False
    return ok


def test_reference_read():
    """Test reading from the Reference (Research) Sheet."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    print("\n--- Testing Reference Sheet (READ) ---")
    try:
        creds = Credentials.from_service_account_file(
            str(READER_KEY_PATH),
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)

        # Test 1: Read Suggested Genres tab
        result = service.spreadsheets().values().get(
            spreadsheetId=REFERENCE_SHEET_ID,
            range="🎯 Suggested Genres!A1:D20"
        ).execute()
        rows = result.get("values", [])
        print(f"✅ Suggested Genres tab: {len(rows)} rows found")
        if len(rows) > 1:
            print(f"   First genre: {rows[1]}")

        # Test 2: Read sheet metadata (tab names)
        meta = service.spreadsheets().get(
            spreadsheetId=REFERENCE_SHEET_ID
        ).execute()
        tabs = [s["properties"]["title"] for s in meta["sheets"]]
        print(f"✅ Sheet tabs: {tabs}")

        # Test 3: Read Genre 1 headers
        result2 = service.spreadsheets().values().get(
            spreadsheetId=REFERENCE_SHEET_ID,
            range="Genre 1!A1:Z1"
        ).execute()
        headers = result2.get("values", [[]])[0]
        print(f"✅ Genre 1 headers: {len(headers)} columns found")
        print(f"   First 5: {headers[:5]}")

        print("\n✅ REFERENCE SHEET CONNECTION SUCCESSFUL!")
        return True

    except Exception as e:
        print(f"\n❌ REFERENCE SHEET FAILED: {e}")
        if "403" in str(e) or "PERMISSION_DENIED" in str(e):
            print("\n   FIX: Share the sheet with your reader service account:")
            reader_email = json.loads(READER_KEY_PATH.read_text()).get("client_email")
            print(f"   Email: {reader_email}")
            print("   Access: Viewer (read-only)")
        elif "404" in str(e):
            print(f"\n   FIX: Sheet ID may be wrong. Current: {REFERENCE_SHEET_ID}")
        return False


def test_submissions_write():
    """Test writing to the Submissions Sheet."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    print("\n--- Testing Submissions Sheet (WRITE) ---")

    if not SUBMISSIONS_SHEET_ID:
        print("⚠️  SUBMISSIONS_SHEET_ID is empty.")
        print("   You need to create a separate Google Sheet for user submissions.")
        print("   Steps:")
        print("   1. Go to sheets.google.com → Create new spreadsheet")
        print("   2. Name it: 'YTShortsAuto - User Submissions'")
        print("   3. Create tab: 'video_submissions' with headers:")
        print("      user_hash | genre | script_text | hook_pattern | word_count |")
        print("      duration | views_14d | retention_avg | likes | caption_style |")
        print("      voice_id | music_mood | timestamp")
        print("   4. Create tab: 'regeneration_feedback' with headers:")
        print("      user_hash | genre | complaint_type | notes | timestamp")
        writer_email = json.loads(WRITER_KEY_PATH.read_text()).get("client_email")
        print(f"   5. Share with: {writer_email} (Editor access)")
        print("   6. Copy the Sheet ID from the URL and paste it in this script")
        return False

    try:
        creds = Credentials.from_service_account_file(
            str(WRITER_KEY_PATH),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build("sheets", "v4", credentials=creds)

        # Test: Append a test row
        test_row = [
            "test_hash_12345",        # user_hash
            "scary_stories",          # genre
            "Test script text",       # script_text
            "question",               # hook_pattern
            "100",                    # word_count
            "45",                     # duration
            "0",                      # views_14d
            "0",                      # retention_avg
            "0",                      # likes
            "horror_red",             # caption_style
            "en-US-Neural2-D",        # voice_id
            "dark_ambient",           # music_mood
            "2026-03-01T00:00:00"     # timestamp
        ]

        service.spreadsheets().values().append(
            spreadsheetId=SUBMISSIONS_SHEET_ID,
            range="video_submissions!A:A",
            valueInputOption="RAW",
            body={"values": [test_row]}
        ).execute()
        print("✅ Test row written to video_submissions tab!")
        print("   (You can delete this test row from the sheet)")

        print("\n✅ SUBMISSIONS SHEET CONNECTION SUCCESSFUL!")
        return True

    except Exception as e:
        print(f"\n❌ SUBMISSIONS SHEET FAILED: {e}")
        if "403" in str(e) or "PERMISSION_DENIED" in str(e):
            writer_email = json.loads(WRITER_KEY_PATH.read_text()).get("client_email")
            print(f"\n   FIX: Share the submissions sheet with: {writer_email}")
            print("   Access: Editor (needs write)")
        return False


def main():
    print("=" * 60)
    print("  YT Shorts Auto — Google Sheets Connection Test")
    print("=" * 60)

    # Step 1: Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Step 2: Check key files
    print()
    if not check_key_files():
        sys.exit(1)

    # Step 3: Test reference sheet read
    ref_ok = test_reference_read()

    # Step 4: Test submissions sheet write
    sub_ok = test_submissions_write()

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Reference Sheet (read):    {'✅ PASS' if ref_ok else '❌ FAIL'}")
    print(f"  Submissions Sheet (write): {'✅ PASS' if sub_ok else '❌ FAIL / NOT SET UP'}")

    if ref_ok and not sub_ok and not SUBMISSIONS_SHEET_ID:
        print("\n  NEXT STEP: Create the Submissions Sheet (see instructions above)")
    elif ref_ok and sub_ok:
        print("\n  🎉 All set! Both sheets connected. Ready to build.")

    print("=" * 60)


if __name__ == "__main__":
    main()
