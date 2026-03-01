"""
Genre Research Excel Sheet Generator
Creates a comprehensive, formatted spreadsheet for analyzing YouTube Shorts.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

wb = openpyxl.Workbook()

# ── STYLE DEFINITIONS ──
HEADER_FILL = PatternFill(start_color="1a1a2e", end_color="1a1a2e", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
SECTION_FILL = PatternFill(start_color="16213e", end_color="16213e", fill_type="solid")
SECTION_FONT = Font(name="Calibri", size=11, bold=True, color="e94560")
DATA_FONT = Font(name="Calibri", size=10, color="333333")
EXAMPLE_FONT = Font(name="Calibri", size=10, color="666666", italic=True)
FORMULA_FILL = PatternFill(start_color="e8f5e9", end_color="e8f5e9", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style='thin', color='CCCCCC'),
    right=Side(style='thin', color='CCCCCC'),
    top=Side(style='thin', color='CCCCCC'),
    bottom=Side(style='thin', color='CCCCCC'),
)
WRAP_ALIGN = Alignment(wrap_text=True, vertical='top')
CENTER_ALIGN = Alignment(horizontal='center', vertical='top')

# ── ALL COLUMNS (in order) ──
# Each tuple: (Column Header, Width, Section Name, Example Value, Data Validation options or None)
COLUMNS = [
    # ─── SECTION: VIDEO INFO ───
    ("Video URL", 35, "📌 VIDEO INFO", "youtube.com/shorts/xYz123abc", None),
    ("Channel Name", 22, "", "@DarkFactsDaily", None),
    ("Channel Subscribers", 18, "", "850K", None),
    ("Views", 14, "", "14200000", None),
    ("Likes", 12, "", "620000", None),
    ("Comments", 12, "", "8400", None),
    ("Upload Date", 14, "", "2024-11-15", None),
    ("Duration (sec)", 14, "", "52", None),
    ("Day of Week", 14, "", "Friday", ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]),
    ("Post Time", 12, "", "21:30", None),
    
    # ─── SECTION: FULL SCRIPT ───
    ("Full Script / Transcript", 70, "📝 SCRIPT (MOST IMPORTANT)", 
     "Did you know that in 1973, a family in Connecticut bought their dream home, only to discover that the previous owner had sealed an entire room behind a brick wall? When construction workers finally broke through, they found a child's bedroom that hadn't been touched in 40 years. The bed was still made. Toys were still on the floor. And on the wall, someone had scratched the words 'she can hear you' over and over again. The family moved out three days later. To this day, no one knows who the room belonged to. And the house? It's still for sale.", None),
    ("Word Count", 12, "", "108", None),
    ("Sentence Count", 14, "", "7", None),
    ("Words Per Second", 16, "", "=L2/H2", None),  # Formula
    
    # ─── SECTION: SCRIPT STRUCTURE ───
    ("Hook (First Sentence)", 50, "🪝 HOOK & STRUCTURE",
     "Did you know that in 1973, a family in Connecticut bought their dream home?", None),
    ("Hook Type", 22, "", "question + time_reference", 
     ["question", "shocking_fact", "what_if", "challenge", "story_opener", "stat_number", "mystery", "impossibility", "time_reference"]),
    ("Hook Emotional Trigger", 22, "", "curiosity", 
     ["curiosity", "fear", "shock", "disbelief", "humor", "fomo", "awe", "anger", "sadness"]),
    ("Hook Speed (sec)", 16, "", "4.5", None),
    ("Opening Words (first 5)", 30, "", "Did you know that in", None),
    ("Body Sentence Count", 18, "", "4", None),
    ("Has Twist/Reveal?", 16, "", "yes", ["yes", "no"]),
    ("Twist Line", 40, "", "she can hear you", None),
    ("Ending Type", 18, "", "open_ended", 
     ["cliffhanger", "call_to_curiosity", "question", "punchline", "open_ended", "call_to_action", "loop_back"]),
    ("Last Sentence", 50, "", "And the house? It's still for sale.", None),
    
    # ─── SECTION: SCRIPT QUALITY ───
    ("Tense Used", 14, "📊 SCRIPT ANALYSIS", "past", ["present", "past", "mixed"]),
    ("POV / Person", 16, "", "narrator", ["you_2nd_person", "they_3rd", "narrator", "I_1st", "mixed"]),
    ("Rhetorical Questions Count", 22, "", "0", None),
    ("Power Words", 50, "", "dream, discover, sealed, scratched, hear, moved out", None),
    ("Emphasis Words", 50, "", "sealed, 40 years, she can hear you, still for sale", None),
    ("Narrative Technique", 22, "", "escalating_reveal", 
     ["escalating_reveal", "mystery_solve", "list_format", "story_arc", "comparison", "countdown", "before_after", "question_answer"]),
    ("Emotional Arc", 30, "", "curiosity → unease → dread → shock → lingering fear", None),
    ("Has Numbers/Stats?", 16, "", "yes (1973, 40 years)", None),
    ("Has Direct Address?", 16, "", "no", ["yes", "no"]),
    ("Banned Phrases Found", 30, "", "none", None),
    
    # ─── SECTION: SCRIPT PACING (NEW) ───
    ("Avg Sentence Length (words)", 24, "⏱️ SCRIPT PACING", "15.4", None),
    ("Shortest Sentence", 40, "", "The bed was still made. (5 words)", None),
    ("Longest Sentence", 50, "", "Did you know that in 1973, a family in Connecticut... (24 words)", None),
    ("Short:Long Sentence Ratio", 24, "", "3:4 (3 short, 4 long)", None),
    ("Sentence Length Pattern", 22, "", "long_then_short_punch", 
     ["long_then_short_punch", "consistent_medium", "building_longer", "alternating", "all_short_punchy", "mixed"]),
    ("Info Density (facts per sentence)", 26, "", "1.0 (7 facts in 7 sentences)", None),
    ("Surprise/Twist Count", 20, "", "2 (sealed room + scratched words)", None),
    ("Has CTA?", 12, "", "no", ["yes_subscribe", "yes_comment", "yes_follow", "yes_like", "implicit", "no"]),
    ("CTA Placement", 14, "", "N/A", ["start", "middle", "end", "N/A"]),
    ("Repetition/Callback?", 22, "", "yes — 'still' repeated: still made, still on floor, still for sale", None),
    ("Sensory Language Used", 30, "", "visual: bed, toys, scratched | auditory: hear", None),
    
    # ─── SECTION: VOICE & PACING ─── 
    ("Voice Gender", 14, "🎙️ VOICE & PACING", "male", ["male", "female", "ai_neutral"]),
    ("Voice Tone", 22, "", "deep_authoritative", 
     ["deep_authoritative", "casual_friendly", "whispery_dramatic", "energetic_fast", "warm_storyteller", "robotic_factual"]),
    ("Speaking Speed", 16, "", "slow", ["slow_under_2.5", "medium_2.5_3.5", "fast_over_3.5"]),
    ("Pause After Hook (ms)", 20, "", "600", None),
    ("Pause Before Reveal (ms)", 22, "", "800", None),
    ("Other Notable Pauses", 40, "", "After '40 years' ~400ms, After 'hear you' ~700ms", None),
    ("Words Spoken Louder/Slower", 40, "", "sealed, 40 years, scratched, she can hear you, still for sale", None),
    
    # ─── SECTION: VISUALS ───
    ("Layout Type", 18, "🖼️ VISUALS", "split_screen", 
     ["full_images", "split_screen", "full_gameplay", "talking_head", "screen_recording", "mixed"]),
    ("Face Visible?", 14, "", "no", ["yes_talking_head", "yes_but_not_main", "no"]),
    ("Image Count", 12, "", "5", None),
    ("Image Change Timing", 20, "", "every 8-12 sec (synced to sentences)", None),
    ("Transition Type", 16, "", "dissolve", 
     ["cut", "dissolve", "fade", "slide", "zoom", "wipe", "mixed"]),
    ("Image Style", 18, "", "dark_moody", 
     ["dark_moody", "bright_colorful", "minimalist", "stock_photos", "ai_generated", "screenshots", "mixed"]),
    ("Ken Burns Effect?", 16, "", "yes", ["yes", "no"]),
    ("Images Match Words?", 18, "", "perfectly_synced", 
     ["perfectly_synced", "loosely_related", "random", "mostly_synced"]),
    ("Image Descriptions", 60, "", 
     "1. Old house exterior (hook) | 2. Brick wall close-up (sealed room) | 3. Abandoned bedroom (child's room) | 4. Scratched wall texture (she can hear you) | 5. For Sale sign (ending)", None),
    ("Gameplay Type", 18, "", "minecraft_parkour", 
     ["minecraft_parkour", "subway_surfers", "satisfying_videos", "temple_run", "gta", "other", "none"]),
    ("Gameplay Position", 16, "", "bottom_half", 
     ["full_screen", "bottom_half", "top_half", "background", "none"]),
    ("Color Grading / Filter", 20, "", "cold_desaturated", 
     ["cold_desaturated", "warm", "high_contrast", "vintage", "neon_bright", "natural", "none"]),
    ("Text Overlays (besides captions)?", 30, "", "none", 
     ["title_card", "fact_labels", "arrows_circles", "counter_number", "none"]),

    # ─── SECTION: CAPTIONS ───
    ("Caption Style", 18, "📝 CAPTIONS", "word_at_a_time", 
     ["word_at_a_time", "sentence_highlight", "karaoke_wipe", "emphasis_only", "bounce_pop", "typewriter", "none"]),
    ("Caption Font", 20, "", "Montserrat Black", None),
    ("Caption Primary Color", 20, "", "white", None),
    ("Caption Highlight Color", 22, "", "red", None),
    ("Caption Position", 16, "", "center", ["top", "center", "bottom"]),
    ("Caption Border/Glow?", 18, "", "yes — black 3px, red glow on emphasis", None),
    ("Words Per Caption Pop", 20, "", "2-3", None),

    # ─── SECTION: AUDIO ───
    ("Has Background Music?", 18, "🎵 AUDIO", "yes", ["yes", "no"]),
    ("Music Mood", 16, "", "eerie", 
     ["eerie", "upbeat", "dramatic", "chill", "tense", "epic", "sad", "energetic", "ambient", "none"]),
    ("Music Volume Level", 18, "", "barely_audible", 
     ["barely_audible", "noticeable", "loud"]),
    ("Music Fades?", 14, "", "yes", ["yes", "no"]),
    ("Music Changes Mid-Video?", 22, "", "no — builds slightly but same track", None),
    ("Has Sound Effects?", 16, "", "yes", ["yes", "no"]),
    ("SFX at Hook", 30, "", "subtle low bass hit", None),
    ("SFX at Reveal/Twist", 30, "", "sharp horror stinger", None),
    ("SFX at Ending", 30, "", "deep drone/rumble", None),
    ("Other SFX Notes", 40, "", "Faint scratching sound during 'scratched the words'", None),
    ("Audio Clarity", 14, "", "crystal_clear", ["crystal_clear", "good", "slightly_noisy", "poor"]),
    
    # ─── SECTION: UPLOAD METADATA ───
    ("Video Title", 50, "📤 UPLOAD METADATA", "This Family Found A Sealed Room In Their Home 😨", None),
    ("Title Length (chars)", 18, "", "52", None),
    ("Title Has Emoji?", 16, "", "yes: 😨", None),
    ("Title Has Hashtags?", 16, "", "no", ["yes", "no"]),
    ("Title Pattern Type", 20, "", "statement_shock", 
     ["question", "statement_shock", "number_list", "how_to", "this_that", "challenge", "story_title"]),
    ("Description First Line", 40, "", "Would you stay? 😱", None),
    ("Hashtags Used", 50, "", "#shorts #scary #creepy #horror #haunted #truestory #mystery", None),
    ("Category", 20, "", "People & Blogs", None),
    
    # ─── SECTION: VIRALITY SIGNALS (NEW) ───
    ("Like-to-View Ratio (%)", 20, "🔥 VIRALITY SIGNALS", "=E2/D2*100", None),  # Formula
    ("Comment-to-View Ratio (%)", 22, "", "=F2/D2*100", None),  # Formula
    ("Estimated Save/Share Level", 22, "", "high", 
     ["very_high", "high", "medium", "low"]),
    ("Why Would Someone Share This?", 40, "", "The twist 'she can hear you' — people tag friends to scare them", None),
    ("Re-Watch Value", 18, "", "medium", 
     ["high_catches_new_details", "medium_good_but_once", "low_no_reason_to_rewatch"]),
    ("Controversy/Debate Potential", 24, "", "low — factual storytelling, not polarizing", None),
    ("Trend Alignment", 20, "", "none_evergreen", 
     ["riding_current_trend", "trending_format", "seasonal", "none_evergreen"]),
    ("First Frame: Scroll-Stop?", 24, "", "yes — dark house image with bold white caption", None),
    ("First Frame: Motion?", 18, "", "yes_ken_burns_zoom", 
     ["yes_ken_burns_zoom", "yes_gameplay_motion", "yes_animation", "no_static"]),
    ("Would YOU Stop Scrolling?", 22, "", "yes — the caption 'Did you know' + eerie image", None),

    # ─── SECTION: ENGAGEMENT DEEP-DIVE ───
    ("Top Comment Theme", 40, "💬 ENGAGEMENT", "People sharing similar real stories", None),
    ("Comment Sentiment", 18, "", "engaged_scared", 
     ["engaged_positive", "engaged_scared", "engaged_debate", "asking_for_more", "skeptical", "mixed"]),
    ("Do Comments Add Stories?", 22, "", "yes — people share their own creepy house stories", None),
    ("Creator Replies in Comments?", 24, "", "yes_pinned_comment", 
     ["yes_pinned_comment", "yes_replies_some", "no_replies"]),
    ("Likely Share Trigger", 30, "", "The 'she can hear you' twist — people tag friends", None),
    ("Retention Hook", 30, "", "Escalating mystery — each sentence more disturbing", None),
    ("Where Would You Stop Watching?", 30, "", "Nowhere — every sentence reveals more, no boring moment", None),

    # ─── SECTION: THUMBNAIL ───
    ("Thumbnail Style", 22, "🖼️ THUMBNAIL", "dark_atmospheric", 
     ["text_overlay", "person_reacting", "dark_atmospheric", "bright_colorful", "screenshot", "split_image", "no_custom"]),
    ("Thumbnail Text", 30, "", "SEALED ROOM", None),
    ("Thumbnail Colors", 20, "", "dark blue + red text", None),
    
    # ─── SECTION: SCORES & NOTES ───
    ("Score: Hook (1-10)", 16, "⭐ SCORES", "9", None),
    ("Score: Script (1-10)", 16, "", "9", None),
    ("Score: Pacing (1-10)", 16, "", "9", None),
    ("Score: Visual (1-10)", 16, "", "8", None),
    ("Score: Audio (1-10)", 16, "", "8", None),
    ("Score: Shareability (1-10)", 20, "", "9", None),
    ("Score: Overall (1-10)", 16, "", "9", None),
    ("Why It Worked", 60, "", "Escalating reveals, open ending makes you want to comment, slow pacing builds dread, images perfectly synced, 'she can hear you' is directed at YOU", None),
    ("What To Improve", 60, "", "Gameplay bottom half slightly distracting, could start faster, add one more detail about the previous owner", None),
    ("Usable as Few-Shot Example?", 22, "", "yes", ["yes", "no", "maybe"]),
    ("Additional Notes", 50, "", "Good template for 'discovery' type horror. Short punchy sentences after setup = effective pacing pattern to replicate.", None),
]


def create_genre_sheet(ws, sheet_name, include_example=True):
    """Create a formatted genre research sheet with headers and optional example."""
    
    ws.title = sheet_name
    ws.sheet_properties.tabColor = "1a1a2e"
    
    # Freeze top row
    ws.freeze_panes = 'A2'
    
    current_section = ""
    col = 1
    
    for header, width, section, example, validation in COLUMNS:
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        cell.border = THIN_BORDER
        
        # Set column width
        ws.column_dimensions[get_column_letter(col)].width = width
        
        # Add example in row 2
        if include_example and example:
            ex_cell = ws.cell(row=2, column=col)
            # Check if it's a formula
            if str(example).startswith("="):
                ex_cell.value = example
                ex_cell.fill = FORMULA_FILL
            else:
                ex_cell.value = example
            ex_cell.font = EXAMPLE_FONT
            ex_cell.alignment = WRAP_ALIGN
            ex_cell.border = THIN_BORDER
        
        # Add data validation (dropdowns) for rows 2-100
        if validation and isinstance(validation, list):
            dv = DataValidation(
                type="list",
                formula1=f'"{",".join(validation)}"',
                allow_blank=True,
                showErrorMessage=True
            )
            dv.error = f'Please select from: {", ".join(validation)}'
            dv.errorTitle = 'Invalid Entry'
            # Apply to rows 3-100 (row 2 is example)
            start_row = 3 if include_example else 2
            dv.add(f'{get_column_letter(col)}{start_row}:{get_column_letter(col)}100')
            ws.add_data_validation(dv)
        
        col += 1
    
    # Set row height for header
    ws.row_dimensions[1].height = 35
    if include_example:
        ws.row_dimensions[2].height = 80  # Taller for example row with long script
    
    # Add section color bars in a helper row (row 1 section markers)
    # We'll color-code sections by changing header backgrounds
    section_colors = {
        "📌 VIDEO INFO": "0d47a1",
        "📝 SCRIPT (MOST IMPORTANT)": "b71c1c",
        "🪝 HOOK & STRUCTURE": "e65100",
        "📊 SCRIPT ANALYSIS": "4a148c",
        "⏱️ SCRIPT PACING": "311b92",
        "🎙️ VOICE & PACING": "1b5e20",
        "🖼️ VISUALS": "006064",
        "📝 CAPTIONS": "f57f17",
        "🎵 AUDIO": "880e4f",
        "📤 UPLOAD METADATA": "1a237e",
        "🔥 VIRALITY SIGNALS": "bf360c",
        "💬 ENGAGEMENT": "33691e",
        "🖼️ THUMBNAIL": "3e2723",
        "⭐ SCORES": "ff6f00",
    }
    
    col = 1
    current_color = "1a1a2e"
    for header, width, section, example, validation in COLUMNS:
        if section and section in section_colors:
            current_color = section_colors[section]
        cell = ws.cell(row=1, column=col)
        cell.fill = PatternFill(start_color=current_color, end_color=current_color, fill_type="solid")
        col += 1


def create_instructions_sheet(ws):
    """Create the instructions/guide sheet."""
    ws.title = "📖 Instructions"
    ws.sheet_properties.tabColor = "4caf50"
    
    instructions = [
        ("Genre Research Sheet — How To Use", "", ""),
        ("", "", ""),
        ("STEP", "WHAT TO DO", "TIME"),
        ("1", "Open a YouTube Short and watch it once normally (just experience it)", "1 min"),
        ("2", "Watch again — this time copy the FULL SCRIPT word for word into column K", "3 min"),
        ("3", "Fill columns A-J (Video Info): URL, channel, views, etc.", "2 min"),
        ("4", "Fill columns L-N (Word count, sentence count — count from the script)", "1 min"),
        ("5", "Fill columns O-X (Hook & Structure): Write the first sentence, classify hook type", "3 min"),
        ("6", "Fill columns Y-AH (Script Analysis): Power words, emphasis words, narrative technique", "3 min"),
        ("7", "Watch a THIRD time — focus on audio. Fill Voice & Pacing columns", "3 min"),
        ("8", "Fill Visuals, Captions, Audio columns — describe what you see/hear", "3 min"),
        ("9", "Copy the title, description line, hashtags into Upload Metadata", "1 min"),
        ("10", "Read 5-10 comments. Note the theme and what makes people engage", "2 min"),
        ("11", "Score the video 1-10 on each dimension + write WHY it worked", "2 min"),
        ("", "", ""),
        ("TOTAL TIME PER VIDEO: ~20 minutes", "", ""),
        ("", "", ""),
        ("IMPORTANT NOTES:", "", ""),
        ("• The FULL SCRIPT column is the MOST important — we use it as few-shot examples for the AI", "", ""),
        ("• Power words = emotionally charged words (terrifying, destroyed, secret, ancient...)", "", ""),
        ("• Emphasis words = words the narrator speaks louder/slower — these become caption highlights", "", ""),
        ("• Row 2 has a filled example in every genre sheet — use it as reference", "", ""),
        ("• Dropdown menus on some columns — click the cell to see options", "", ""),  
        ("• Aim for 15 TOP VIDEOS per genre + 5 low-performing ones to compare", "", ""),
        ("• If a column doesn't apply (e.g., no gameplay), write 'none' or 'N/A'", "", ""),
    ]
    
    ws.column_dimensions['A'].width = 55
    ws.column_dimensions['B'].width = 75
    ws.column_dimensions['C'].width = 15
    
    for i, (a, b, c) in enumerate(instructions, 1):
        ws.cell(row=i, column=1, value=a).font = Font(name="Calibri", size=12 if i <= 2 else 10, bold=i <= 1 or i == 3 or "IMPORTANT" in str(a) or "TOTAL" in str(a))
        ws.cell(row=i, column=2, value=b).font = Font(name="Calibri", size=10)
        ws.cell(row=i, column=3, value=c).font = Font(name="Calibri", size=10)
        if i == 1:
            ws.cell(row=i, column=1).font = Font(name="Calibri", size=16, bold=True, color="1a1a2e")
        if i == 3:
            for col_idx in range(1, 4):
                ws.cell(row=i, column=col_idx).fill = PatternFill(start_color="e0e0e0", end_color="e0e0e0", fill_type="solid")


def create_genre_suggestions_sheet(ws):
    """Create a sheet with suggested genres."""
    ws.title = "🎯 Suggested Genres"
    ws.sheet_properties.tabColor = "ff9800"
    
    headers = ["Genre ID", "Display Name", "Icon", "Why It Works", "Competition Level", "Audience Size", "Content Difficulty", "Recommended?"]
    widths = [22, 25, 8, 55, 18, 16, 18, 15]
    
    for i, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=1, column=i, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.column_dimensions[get_column_letter(i)].width = w
    
    genres = [
        ("scary_stories", "Scary Stories", "👻", "Massive audience, high shares (people tag friends), easy to write, works with stock images + gameplay", "Medium", "Huge", "Easy", "★★★★★"),
        ("motivation", "Motivation / Mindset", "💪", "Evergreen content, high save rate, quote-based = easy scripts, inspirational images", "High", "Huge", "Easy", "★★★★☆"),
        ("psychology_facts", "Psychology Facts", "🧠", "Mind-blowing content = high shares, educational feel = credibility, unique niche", "Low-Medium", "Large", "Medium", "★★★★★"),
        ("tech_ai", "Tech & AI News", "🤖", "Trending topic, tech-savvy audience engages heavily, always fresh content", "Medium", "Large", "Medium", "★★★★☆"),
        ("history_facts", "History Facts", "📜", "Unique stories = low competition, educational credibility, great for images", "Low", "Large", "Medium", "★★★★★"),
        ("space_universe", "Space & Universe", "🌌", "Awe-inspiring content, stunning visuals available free (NASA), universal appeal", "Low-Medium", "Large", "Medium", "★★★★☆"),
        ("reddit_stories", "Reddit Stories", "📱", "Endless content supply, high engagement (people relate), proven format", "High", "Huge", "Easy", "★★★☆☆"),
        ("animal_facts", "Animal Facts", "🐾", "Universal appeal, heartwarming + amazing content, great stock footage", "Medium", "Huge", "Easy", "★★★★☆"),
        ("conspiracy_lite", "Mind-Blowing Theories", "🔍", "High curiosity factor, debate in comments = algorithm boost, careful: avoid harmful content", "Medium", "Large", "Hard", "★★★☆☆"),
        ("gaming_facts", "Gaming History & Facts", "🎮", "Built-in gameplay footage, nostalgic audience, Easter eggs = high engagement", "Medium", "Large", "Easy", "★★★★☆"),
        ("crime_mystery", "True Crime Mini", "🔎", "Huge audience on all platforms, binge-worthy format, serious tone works well", "High", "Huge", "Medium", "★★★☆☆"),
        ("money_finance", "Money & Finance Tips", "💰", "High-value audience (advertisers love it), actionable content = saves, credibility building", "High", "Large", "Medium", "★★★☆☆"),
        ("relationship_tips", "Relationship & Social", "❤️", "Relatable content = comments, debate-style hooks work great, wide audience", "High", "Huge", "Easy", "★★★☆☆"),
        ("science_facts", "Science Explained", "🔬", "Educational credibility, visual experiments available, mind-blowing reveals", "Low-Medium", "Large", "Medium", "★★★★☆"),
        ("mythology", "Mythology & Legends", "⚔️", "Unique niche, rich stories, stunning AI/stock art, low competition", "Low", "Medium", "Medium", "★★★★★"),
    ]
    
    for row_idx, genre in enumerate(genres, 2):
        for col_idx, val in enumerate(genre, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = DATA_FONT
            cell.alignment = WRAP_ALIGN
            cell.border = THIN_BORDER
    
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = 'A2'


# ── BUILD THE WORKBOOK ──

# Sheet 1: Instructions
create_instructions_sheet(wb.active)

# Sheet 2: Suggested Genres  
create_genre_suggestions_sheet(wb.create_sheet())

# Sheet 3-7: Genre template sheets (5 blank genre sheets ready to fill)
# Creating generic named sheets — user renames to their genres
genre_sheets = ["Genre 1", "Genre 2", "Genre 3", "Genre 4", "Genre 5"]
for name in genre_sheets:
    ws = wb.create_sheet()
    create_genre_sheet(ws, name, include_example=True)

# Save
output_path = r"C:\Users\vgaur\Desktop\YTSHORTSAUTOMATION\Genre_Research_Sheet.xlsx"
wb.save(output_path)
print(f"✅ Created: {output_path}")
print(f"   Sheets: {[s.title for s in wb.worksheets]}")
print(f"   Columns per genre sheet: {len(COLUMNS)}")
print(f"   Sections: 12")
