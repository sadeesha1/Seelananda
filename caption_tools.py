"""
caption_tools.py — Aksha AI copywriter for social media captions (Phase 4).
"""

import json
import re

import anthropic
from llm_adapter import get_llm_response
from dotenv import load_dotenv

from config import AKSHA_SYSTEM_PROMPT, CLAUDE_MODEL, MAX_TOKENS

load_dotenv()

# ── Tool 8: write_captions ──────────────────────────────────────────────────────

def write_captions(recipe_json: dict, script_json: dict, llm_id: str) -> dict:
    """
    Generate platform-specific copy (Instagram & Facebook) and hashtags.
    Uses Claude to write in Aksha's signature storytelling voice.
    """

    dish_name = recipe_json.get("dish_name", "a delicious dish")
    short_desc = recipe_json.get("short_description", "")
    cultural_angle = recipe_json.get("cultural_angle", "")

    # Extract some hook/cta context from script if available
    script_hook = script_json.get("hook", "")
    script_cta = script_json.get("cta", "")
    
    prompt = f"""You are the copywriter for Aksha's social media. 

Write captions for the following content:
Dish: {dish_name}
Vibe/Description: {short_desc}
Cultural Story: {cultural_angle}
Video Hook: {script_hook}
Video CTA: {script_cta}

REQUIREMENTS:
1. instagram_caption:
   - hook: The first line (must stop the scroll, be punchy/dramatic).
   - body: 3-4 sentences total. Use warm storytelling and Aksha's voice. Weave in the cultural angle.
   - cta: Call to action, asking a question or telling them to save the recipe.
   - full_caption: hook + body + cta combined with appropriate line breaks.
2. hashtags:
   - niche: 10 specific cooking/food niche tags.
   - broad: 10 general food/cooking tags.
   - lifestyle: 5 lifestyle/culture tags.
   - full_hashtag_string: all 25 combined with spaces.
3. facebook_post:
   - text: Slightly longer, more conversational than Instagram. Should feel like a mini blog post update to family/friends.

Return ONLY a valid JSON object matching this structure exactly (no markdown formatting):
{{
  "instagram_caption": {{
    "hook": "<string>",
    "body": "<string>",
    "cta": "<string>",
    "full_caption": "<string>"
  }},
  "hashtags": {{
    "niche": ["<tag1>", "<tag2>"],
    "broad": ["<tag1>", "<tag2>"],
    "lifestyle": ["<tag1>", "<tag2>"],
    "full_hashtag_string": "<string>"
  }},
  "facebook_post": {{
    "text": "<string>"
  }}
}}"""

    raw = get_llm_response(prompt, AKSHA_SYSTEM_PROMPT, MAX_TOKENS, llm_id).strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    
    try:
        result = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"Failed to parse Claude JSON response for captions: {e}\\nRaw: {raw}")
        
    return result
