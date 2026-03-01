# Google Deep Research Prompt — YouTube Shorts Automation Product

> **Instructions:** Copy everything below the line into Google Deep Research. Attach the `MASTER_BLUEPRINT.md` file alongside this prompt so it has full context of what you're building.

---

I'm attaching my complete product blueprint (MASTER_BLUEPRINT.md) for a desktop application that automates YouTube Shorts creation using AI. I need you to read it thoroughly and then conduct a comprehensive market analysis.

## About my product (summary — see the attached blueprint for full details):
- **Desktop app** (Tauri + Python backend) that generates complete YouTube Shorts autonomously: scripts, TTS narration with SSML, images, captions with 6 animation styles, background video/gameplay, SFX, music — then uploads to YouTube
- **$100 one-time purchase** — no subscription. Competitors charge $15-150/MONTH
- **BYOK model** (Bring Your Own Key) — users provide their own API keys for Gemini, Google Cloud TTS, Groq, YouTube, Pexels, Pixabay, Freesound. Our cost per user = $0
- **Self-improving system** — learns from video performance data via analytics feedback loop, adjusts scripts/hooks/timing over time
- **Cross-model validation** — Gemini generates scripts, Groq (Llama 3.3 70B) validates quality (5-layer validation pipeline)
- **10+ genre templates** with per-genre voice profiles, caption styles, image strategies, music moods
- **Preview before upload** with 1 regeneration per video — user feedback drives smart partial re-generation
- **Shadow ban detection** using 5 statistical signals
- **Anti-piracy** via Ed25519 license keys + HWID machine binding + PyArmor + encrypted prompts

Please analyze the following 10 areas in depth:

---

## 1. Market Size & Demand
- Current and projected market size for: YouTube automation tools, AI video generation tools, short-form video creation tools (2024-2027)
- How many YouTube channels actively post Shorts? What percentage would realistically pay for an automation tool?
- Is this market growing, plateauing, or already saturated?
- Break down by geography — where is demand strongest? (US, India, Southeast Asia, Europe, LATAM)

## 2. Competitive Landscape (Deep Dive)
- List EVERY direct competitor in AI-powered YouTube Shorts automation. For each one provide:
  - Exact pricing model (subscription tiers, one-time, freemium)
  - Key features and critical limitations
  - Real user reviews — what do people actually say? (search Reddit, Trustpilot, G2, ProductHunt)
  - Number of users/customers if known
  - What AI models/TTS engines they use
  - Do they support BYOK? If not, do they eat the API costs?
- Include at minimum: ShortX, AutoShorts.ai, InVideo AI, Opus Clip, Fliki, Pictory, Crayo AI, Klap, Shorts Generator, Vidnoz, Visla, Lumen5, Renderforest
- Which have raised VC funding? How much? Are any profitable?
- Are there any open-source alternatives gaining traction?

## 3. Feature Gap Analysis
Based on what my blueprint describes vs what competitors offer, identify:
- Which of my features are truly unique (not offered by ANY competitor)?
- Which features do users MOST request that current tools lack?
- Specifically check if ANY competitor offers:
  - Self-improving AI that learns from video performance data
  - Cross-model validation (using a second LLM to quality-check scripts)
  - Per-genre customization (different prompts, voices, visuals per niche)
  - BYOK (users bring their own API keys)
  - Real caption animation (word-level karaoke, bounce, emphasis highlighting)
  - Background gameplay integration (Minecraft/Subway Surfers split-screen)
  - Shadow ban detection with auto-recovery
  - Preview + regeneration before upload
  - Frequency-aware audio ducking (not just flat volume reduction)
- Search Reddit subs: r/youtubeautomation, r/NewTubers, r/ChatGPT, r/SideProject, r/Entrepreneur
- Search Twitter/X for complaints about specific tools
- Top 10 complaints about existing YouTube Shorts automation tools

## 4. Pricing Validation
- What are users currently paying for similar tools? Build a pricing comparison table
- Is $100 one-time realistic for a BYOK tool? Or is it too high / too low?
- How does BYOK change the value proposition? Users save on subscription but pay for their own API usage — what's the actual monthly API cost for a user making 3-6 videos/day on free tiers?
- Are there successful examples of one-time purchase AI tools in this space?
- Search AppSumo, ProductHunt, and indie hacker communities for lifetime deal data on video tools
- What would the optimal price be to maximize both adoption and revenue?

## 5. YouTube Policy & Risk Assessment (Critical)
- What is YouTube's CURRENT official stance on AI-generated content as of 2025/2026?
- Are AI-generated Shorts being actively suppressed, shadow-banned, or penalized?
- What are the exact disclosure requirements? Does the "made with AI" label hurt performance?
- Have any YouTube automation tool users reported channel terminations? Document specific cases
- Is there a risk YouTube will crack down on automation tools specifically?
- Any recent YouTube policy changes (last 6 months) that affect this space?
- Are Shorts still being pushed by YouTube's algorithm or is the honeymoon period over?

## 6. Technical Feasibility Validation
Based on my blueprint's architecture, validate:
- Are these free tier limits actually sufficient for real daily usage?
  - Gemini 2.5 Flash: ~15 RPM, is this enough for 3-6 videos/day?
  - Google Cloud TTS: 1M chars/month free — how many videos is that?
  - Groq: 500K tokens/day — sufficient for validation of 6 scripts/day?
  - YouTube Data API: 10K units/day — what's the actual cost per upload?
  - Pexels/Pixabay/Freesound: any gotchas with their free tiers?
- What are the REAL hidden costs a user will hit?
- Is the FFmpeg-based rendering approach (no MoviePy) standard and reliable?
- Any concerns about Tauri v2 for a production desktop app?

## 7. Distribution & Go-to-Market Strategy
- How do successful indie desktop apps acquire their first 100, 1000, 10000 users?
- What marketing channels specifically work for YouTube automation tools?
- Map the communities, forums, influencers, and content creators in this niche
- Would a ProductHunt launch make sense? What about AppSumo?
- How important is a free trial vs paid-only? Is 3 free videos enough?
- What's the typical virality coefficient for tools like this?
- Should we sell on our own site or through marketplaces (Gumroad, LemonSqueezy)?

## 8. Moat & Defensibility
- If a well-funded competitor sees my feature set and tries to copy it, what takes the longest to replicate?
- Is the self-improving feedback loop (analytics → pattern engine → script adjustment) a real competitive moat or is it easy to copy?
- Could Google, YouTube, Canva, Adobe, or CapCut enter this space and make indie tools obsolete?
- What's the realistic window of opportunity before big players dominate?
- Is BYOK a sustainable advantage or will competitors just eat the API costs to simplify UX?

## 9. Revenue Projections
- At $100 one-time purchase:
  - What conversion rate should I expect from free trial → paid?
  - How many units needed for $5K/month, $10K/month, $50K/month revenue?
  - What's a realistic customer acquisition cost (CAC) for this niche?
  - What would month 1, month 6, month 12, year 2 look like realistically?
- Compare with actual indie tool revenue numbers from similar products (cite examples)
- Should I consider a hybrid model (one-time + optional premium features)?

## 10. Red Flags & Existential Risks
- What are the top 5 things that could kill this product entirely?
- Regulatory risk: any upcoming legislation affecting AI content generation?
- Could YouTube restrict API access for automation tools?
- What happens if Google puts Gemini free tier behind a paywall?
- Legal exposure: copyright, defamation, misinformation liability for AI-generated content?
- What if YouTube Shorts as a format loses momentum?
- Is there a risk of market saturation — too many automation tools, not enough buyers?

---

**Requirements for your response:**
- Cite specific sources for ALL data points (links to articles, Reddit threads, documentation, reports)
- Include actual numbers wherever possible, not just qualitative assessments
- Prioritize very recent data (2024-2026)
- Be brutally honest about risks — I need reality, not optimism
- If data doesn't exist for something, say so explicitly rather than speculating
- Compare my specific features (from the attached blueprint) against each competitor
