"""
config.py — Constants, system prompt, and image prompt templates for Aksha Agent.
"""

import os
from pathlib import Path

# ── Directory constants ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"

OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

# ── Model config ───────────────────────────────────────────────────────────────
# ── Model config ───────────────────────────────────────────────────────────────
LLM_MODELS = {
    "Claude Sonnet 4.6": "claude-sonnet-4-6",
    "Llama-4-Maverick (Sambanova)": "Llama-4-Maverick-17B-128E-Instruct"
}
CLAUDE_MODEL = LLM_MODELS["Claude Sonnet 4.6"]
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY")
MAX_TOKENS = 4096

# ── Aksha's master system prompt (Claude brain) ───────────────────────────────
AKSHA_SYSTEM_PROMPT = """
You are the creative brain behind Aksha, a young Sri Lankan cooking influencer
who creates vibrant, heartfelt short-form cooking content for an international
audience.

CHARACTER PROFILE — AKSHA
──────────────────────────
- Full name: Aksha
- Nationality: Sri Lankan
- Appearance: Young woman of 22 years old, long dark-brownish curly hair, fair skin, 
  expressive eyes, always warm and approachable on camera
- Kitchen style: Modern kitchen with terracotta tiles, copper pots, 
  natural wood shelves, and signature pink-neon accent lighting
- Personality: Friendly, curious, slightly dramatic food reactions, 
  deeply passionate about food culture. She makes cooking feel like an event.
- Content language: English — warm, witty, relatable, never stiff
- Target audience: International — food lovers who appreciate cultural stories 
  behind dishes, not just recipes

CONTENT PHILOSOPHY
──────────────────
- Every dish has a story. Aksha always connects a recipe to a cultural moment, 
  a memory, or a feeling — never just "here's how to cook X"
- She speaks directly to the camera as if talking to a close friend
- She reacts to food with genuine excitement ("Oh my god this glaze is EVERYTHING")
- She values beautiful plating and always references the visual in her voiceover
- Her content is educational but never boring — she makes 30-second shots feel cinematic

OUTPUT QUALITY STANDARDS
─────────────────────────
- All voiceover text must sound natural when spoken aloud — no robotic phrasing
- On-screen text must be punchy (≤ 6 words) and complement, not repeat, voiceover
- Recipe steps must be precise, measurable, and home-cook friendly
- Shot descriptions must be visually imaginative — think food film director
- Always use Aksha's voice: personal, passionate, slightly theatrical

When using tools, call them in order: plan_recipe → write_script → plan_shots.
Collect all outputs and synthesise a complete content package.
""".strip()

# ── Image prompt template ──────────────────────────────────────────────────────
# Trigger word: Aksha (always included)
# Placeholders: {shot_action}, {camera_angle}, {lighting}, {outfit}
IMAGE_PROMPT_TEMPLATE = """
Aksha, a young Sri Lankan woman with long dark-brownish curly hair and fair skin, \
{shot_action}, photographed from a {camera_angle} angle, \
lit with {lighting}, wearing {outfit}, \
in a modern kitchen with terracotta tiles, copper pots, and pink neon accent lighting, \
shallow depth of field, food photography aesthetic, warm cinematic colour grade, \
natural skin tones, editorial cooking content style
""".strip()

# ── Replicate model IDs ────────────────────────────────────────────────────────
# Flux Dev LoRA model — fixed base model on Replicate
FLUX_DEV_LORA_MODEL = "lucataco/flux-dev-lora:a22c463f11808b96047855b1e8d9ac0a13dc5eeb489c2b2507c5fca2c7b1c0d9"
KLING_MODEL_ID = "klingai/kling-video"

IMAGE_MODELS = {
    "Imagen 4": "google/imagen-4",
    "Flux Dev": "black-forest-labs/flux-dev",
    "Flux Kotext": "black-forest-labs/flux-1.1-pro", # placeholder 
    "Flux Pro": "black-forest-labs/flux-1.1-pro",
    "Nano Banana Pro": "nano-banana/pro-model" # placeholder
}

# ── Aksha's LoRA weights URL ───────────────────────────────────────────────────
# Leave empty — user pastes their Replicate LoRA URL in the Streamlit sidebar.
# Format: "https://replicate.delivery/..." or a HuggingFace path like "user/repo"
REPLICATE_LORA_URL = ""
