# GCP & Google Sheets Setup Guide

> Follow these steps to set up the Google Cloud infrastructure needed for the app.

---

## Step 1: Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a Project** → **New Project**
3. Name: `ytshortsauto` (or whatever you prefer)
4. Click **Create**
5. Make sure this project is selected in the top bar

---

## Step 2: Enable Required APIs

Go to **APIs & Services → Library** and enable these:

| API | Search For | Why |
|---|---|---|
| Google Sheets API | `Google Sheets API` | Read genres + scripts, write submissions |
| Google Drive API | `Google Drive API` | Required by Sheets API for sharing |

> Note: The user-facing APIs (Gemini, TTS, YouTube, etc.) will use the USER's own GCP project, not ours. We only need Sheets API on our project.

---

## Step 3: Create Service Account A (Reference Reader)

1. Go to **IAM & Admin → Service Accounts**
2. Click **+ Create Service Account**
3. Name: `reference-reader`
4. Description: `Reads genre list and curated scripts from Reference Sheet`
5. Click **Create and Continue**
6. Skip the role assignment (no GCP roles needed — it only accesses Sheets)
7. Click **Done**
8. Click on the service account you just created
9. Go to **Keys** tab → **Add Key → Create new key → JSON**
10. Download the JSON key file → save as `reference-reader-key.json`
11. **Note the email** (looks like `reference-reader@ytshortsauto.iam.gserviceaccount.com`)

---

## Step 4: Create Service Account B (Data Writer)

1. Same steps as above
2. Name: `data-writer`
3. Description: `Writes anonymized user performance data to Submissions Sheet`
4. Download JSON key → save as `data-writer-key.json`
5. **Note the email** (looks like `data-writer@ytshortsauto.iam.gserviceaccount.com`)

---

## Step 5: Create the Reference Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) (from YOUR personal Google account)
2. Create a new spreadsheet
3. Name it: **YTShortsAuto - Reference Data**
4. Create these tabs (rename "Sheet1" and add new tabs):

### Tab: `genres`
| genre_id | display_name | icon | difficulty | is_active |
|---|---|---|---|---|
| scary_stories | Scary Stories & Mysteries | 👻 | Easy | TRUE |
| psychology | Psychology Facts | 🧠 | Medium | TRUE |
| history | History Facts | 🏛️ | Medium | TRUE |
| motivation | Motivation & Mindset | 💪 | Easy | TRUE |
| tech_ai | Tech & AI News | 🤖 | Medium | TRUE |

### Tab: `scary_stories` (one tab per genre with scripts)
| script_text | hook_pattern | quality_score | word_count |
|---|---|---|---|
| (we'll populate this with test data — see `test_reference_data.json`) | | | |

### Tab: `genre_config`
| genre_id | tts_voice | tts_rate | tts_pitch | layout | caption_preset | music_mood |
|---|---|---|---|---|---|---|
| scary_stories | en-US-Neural2-D | 0.88 | -2.0 | split_screen | horror_red | dark_ambient |
| psychology | en-US-Neural2-F | 0.95 | 0.0 | full_image | clean_pro | neutral |
| history | en-US-Neural2-D | 0.92 | -0.5 | full_image | classic_white | cinematic |
| motivation | en-US-Neural2-A | 1.02 | 0.5 | full_image | bold_pop | uplifting |
| tech_ai | en-US-Neural2-J | 0.97 | 0.0 | full_image | neon_glow | electronic |

5. **Share the sheet** with the reference-reader service account:
   - Click **Share** button
   - Paste: `reference-reader@ytshortsauto.iam.gserviceaccount.com`
   - Set to **Viewer** (read-only)
   - Uncheck "Notify people"
   - Click **Share**

6. **Copy the Sheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXX/edit
                                          ^^^^^^^^^^^^^^^^^ THIS PART
   ```

---

## Step 6: Create the Submissions Google Sheet

1. Create another new spreadsheet
2. Name it: **YTShortsAuto - User Submissions**
3. Create these tabs:

### Tab: `video_submissions`
| user_hash | genre | script_text | hook_pattern | word_count | duration | views_14d | retention_avg | likes | caption_style | voice_id | music_mood | timestamp |

### Tab: `regeneration_feedback`
| user_hash | genre | complaint_type | notes | timestamp |

4. **Share** with the data-writer service account:
   - Paste: `data-writer@ytshortsauto.iam.gserviceaccount.com`
   - Set to **Editor** (needs write access)
   - Click **Share**

5. Copy the Sheet ID (same as above method)

---

## Step 7: Save Your Config

Create a file (you'll encrypt this later) with your IDs:

```json
{
  "reference_sheet_id": "YOUR_REFERENCE_SHEET_ID_HERE",
  "submissions_sheet_id": "YOUR_SUBMISSIONS_SHEET_ID_HERE"
}
```

Store the two JSON key files (`reference-reader-key.json` and `data-writer-key.json`) securely. These will be encrypted into the app binary during build.

---

## Step 8: Test It Works

Run this Python script to verify everything is connected:

```python
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Test Reference Sheet (read)
creds = Credentials.from_service_account_file(
    'reference-reader-key.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
service = build('sheets', 'v4', credentials=creds)
result = service.spreadsheets().values().get(
    spreadsheetId='YOUR_REFERENCE_SHEET_ID',
    range='genres!A1:E10'
).execute()
print("✅ Reference Sheet connected!")
print(f"   Found {len(result.get('values', []))} rows in genres tab")

# Test Submissions Sheet (write)
creds2 = Credentials.from_service_account_file(
    'data-writer-key.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
service2 = build('sheets', 'v4', credentials=creds2)
service2.spreadsheets().values().append(
    spreadsheetId='YOUR_SUBMISSIONS_SHEET_ID',
    range='video_submissions!A:A',
    valueInputOption='RAW',
    body={'values': [['test_hash', 'scary_stories', 'test script', 'question',
                      '120', '45', '0', '0', '0', 'horror_red', 'Neural2-D',
                      'dark_ambient', '2026-03-01T00:00:00']]}
).execute()
print("✅ Submissions Sheet connected! (test row written)")
```

Install the dependency first:
```
pip install google-api-python-client google-auth
```

---

## Checklist

- [ ] GCP project created
- [ ] Google Sheets API enabled
- [ ] Google Drive API enabled
- [ ] Service Account A created (reference-reader) + JSON key downloaded
- [ ] Service Account B created (data-writer) + JSON key downloaded
- [ ] Reference Sheet created with `genres`, `scary_stories`, `genre_config` tabs
- [ ] Reference Sheet shared with Service Account A (Viewer)
- [ ] Submissions Sheet created with `video_submissions`, `regeneration_feedback` tabs
- [ ] Submissions Sheet shared with Service Account B (Editor)
- [ ] Both Sheet IDs saved
- [ ] Test script passes ✅
