import asyncio
from backend.services.gemini_service import GeminiService
from backend.core.config import config
from backend.agents.prompts import SCRIPT_SYSTEM_PROMPT, SCRIPT_USER_PROMPT

async def main():
    print("Initializing GeminiService...")
    gemini = GeminiService(api_key=config.gemini_api_key)
    
    sys_prompt = SCRIPT_SYSTEM_PROMPT.format(target_words=108)
    user_prompt = SCRIPT_USER_PROMPT.format(
        genre_name="Animal Facts",
        target_duration=45,
        target_words=108,
        mode="auto",
        custom_topic_line="Topic: Auto-generate",
        reference_scripts="(No reference scripts)",
        calibration_section=""
    )
    
    print("Calling Gemini...")
    try:
        response = await gemini.generate(sys_prompt, user_prompt)
        print("\n--- RAW GEMINI RESPONSE ---")
        print(response)
        print("---------------------------\n")
    except Exception as e:
        print(f"Error calling Gemini: {e}")

if __name__ == "__main__":
    asyncio.run(main())
