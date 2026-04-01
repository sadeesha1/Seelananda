"""
agent.py — Claude Sonnet master agent with three content-planning tools.

Tools (called in order by Claude via native function calling):
  1. plan_recipe   — Structured recipe from a dish name
  2. write_script  — Short-form video script from the recipe
  3. plan_shots    — Cinematography shot list from the script

Entry point:
  run_agent(user_prompt: str) -> dict  (full content_package)
"""

import json
import re
import anthropic
from llm_adapter import get_llm_response, run_openai_agent
from dotenv import load_dotenv

from config import AKSHA_SYSTEM_PROMPT, CLAUDE_MODEL, MAX_TOKENS

load_dotenv()

# ── Tool implementations ───────────────────────────────────────────────────────

def plan_recipe(dish_name: str, **kwargs) -> dict:
    """
    Generate a structured recipe in Aksha's voice.

    Args:
        dish_name: The name of the dish Aksha is making.

    Returns:
        dict with keys: dish_name, short_description, ingredients, steps,
        cultural_angle
    """
    prompt = f"""Create a detailed recipe JSON for: {dish_name}

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "dish_name": "{dish_name}",
  "short_description": "<2 sentences in Aksha's warm personal voice>",
  "ingredients": [
    {{"name": "<ingredient>", "quantity": <number>, "unit": "<unit or 'piece'>"}},
    ...
  ],
  "steps": [
    {{"step_number": 1, "instruction": "<clear home-cook-friendly instruction>", "duration_seconds": <int>}},
    ...
  ],
  "cultural_angle": "<one sentence connecting this dish to a broader food story>"
}}

Requirements:
- short_description: warm, personal, Aksha's excited voice
- ingredients: 6–12 items with precise quantities
- steps: 5–8 steps, every step has a realistic duration_seconds
- cultural_angle: meaningful connection to culture, memory, or food tradition
"""

    raw = get_llm_response(prompt, AKSHA_SYSTEM_PROMPT, MAX_TOKENS, llm_id=kwargs.get('llm_id', CLAUDE_MODEL)).strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def write_script(recipe_json: dict, **kwargs) -> dict:
    """
    Generate a short-form video script from a recipe JSON.

    Args:
        recipe_json: Output dict from plan_recipe().

    Returns:
        dict with keys: total_duration_seconds, sections, hook, cta
    """
    prompt = f"""Based on this recipe, write a short-form video script for Aksha.

RECIPE:
{json.dumps(recipe_json, indent=2)}

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "total_duration_seconds": <int, aim for 45–90 seconds>,
  "hook": "<attention-grabbing opening 5 seconds — one punchy sentence Aksha says to camera>",
  "sections": [
    {{
      "section_name": "<e.g. Hook, Intro, Ingredients, Step 1, Plating, CTA>",
      "voiceover_text": "<natural spoken words, Aksha's voice, conversational>",
      "on_screen_text": "<≤6 words, punchy caption text>",
      "start_time_seconds": <int>,
      "end_time_seconds": <int>
    }},
    ...
  ],
  "cta": "<closing call to action — friendly, not corporate>"
}}

Requirements:
- 5–8 sections covering: hook, ingredient intro, 2–3 key steps, reveal/plating, CTA
- voiceover_text: must sound natural spoken aloud, Aksha's warm personality
- on_screen_text: ≤6 words, big impact — complements but never repeats voiceover
- hook must be the most engaging moment — start with the result or a dramatic moment
- cta: warm, specific (e.g. "Save this for your next dinner party 🌙")
- total_duration_seconds must equal the last section's end_time_seconds
"""

    raw = get_llm_response(prompt, AKSHA_SYSTEM_PROMPT, MAX_TOKENS, llm_id=kwargs.get('llm_id', CLAUDE_MODEL)).strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def plan_shots(script_json: dict, **kwargs) -> dict:
    """
    Generate a cinematography shot list from a script JSON.

    Args:
        script_json: Output dict from write_script().

    Returns:
        dict with keys: shots (list of 8–10 shot objects)
    """
    prompt = f"""Based on this video script, create a detailed shot list for Aksha's video.

SCRIPT:
{json.dumps(script_json, indent=2)}

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "shots": [
    {{
      "shot_number": <int>,
      "shot_name": "<descriptive name e.g. 'Opening Reveal', 'Butter Melt Close-Up'>",
      "camera_angle": "<e.g. 'close-up overhead', 'medium wide', 'extreme close-up', 'eye level'>",
      "action_description": "<what Aksha is doing in this shot — specific and visual>",
      "prop_focus": "<which ingredient or tool is visually prominent>",
      "duration_seconds": <int>,
      "corresponding_script_section": "<name of the script section this shot serves>"
    }},
    ...
  ]
}}

Requirements:
- 8–10 shots total
- Mix of camera angles: overhead, close-up, medium, extreme close-up, tracking
- action_description: precise and cinematic — imagine a food film director writing this
- prop_focus: be specific (e.g. "chocolate ganache dripping off spatula" not just "chocolate")
- Every script section should have at least one corresponding shot
- Include at least 2 extreme close-up food money shots
- Include at least one shot of Aksha reacting to the food
"""

    raw = get_llm_response(prompt, AKSHA_SYSTEM_PROMPT, MAX_TOKENS, llm_id=kwargs.get('llm_id', CLAUDE_MODEL)).strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


# ── Tool definitions for Claude native tool use ───────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "plan_recipe",
        "description": (
            "Generate a structured recipe in Aksha's voice, including ingredients, "
            "step-by-step instructions, and a cultural food story angle. "
            "Always call this tool first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dish_name": {
                    "type": "string",
                    "description": "The name of the dish Aksha is making, extracted from the user prompt.",
                }
            },
            "required": ["dish_name"],
        },
    },
    {
        "name": "write_script",
        "description": (
            "Generate a short-form video script from a recipe JSON. "
            "Produces timed sections with voiceover text and on-screen captions. "
            "Call this after plan_recipe."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "recipe_json": {
                    "type": "object",
                    "description": "The full recipe dict returned by plan_recipe.",
                }
            },
            "required": ["recipe_json"],
        },
    },
    {
        "name": "plan_shots",
        "description": (
            "Generate a detailed cinematography shot list from a script JSON. "
            "Produces 8–10 shots with camera angles, action descriptions, and prop focus. "
            "Call this after write_script."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "script_json": {
                    "type": "object",
                    "description": "The full script dict returned by write_script.",
                }
            },
            "required": ["script_json"],
        },
    },
]

# ── Tool dispatcher ────────────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "plan_recipe": plan_recipe,
    "write_script": write_script,
    "plan_shots": plan_shots,
}


# ── Master agent loop ──────────────────────────────────────────────────────────

def run_agent(user_prompt: str, status_callback=None, llm_id: str = None) -> dict:
    if llm_id is None: llm_id = CLAUDE_MODEL
    if not llm_id.startswith("claude"):
        return run_openai_agent(user_prompt, llm_id, AKSHA_SYSTEM_PROMPT, TOOL_DEFINITIONS, MAX_TOKENS, status_callback, TOOL_REGISTRY)
    """
    Orchestrate the three content tools via Claude native function calling.

    Args:
        user_prompt: One-line description of what Aksha is cooking.
        status_callback: Optional callable(str) for streaming status messages
                         to the UI (e.g. a Streamlit status placeholder).

    Returns:
        content_package dict with keys: recipe, script, shots, user_prompt
    """
    client = anthropic.Anthropic()

    def _status(msg: str):
        if status_callback:
            status_callback(msg)

    messages = [
        {
            "role": "user",
            "content": (
                f"{user_prompt}\n\n"
                "Please create a complete content package for Aksha by calling "
                "plan_recipe, then write_script, then plan_shots — in that order."
            ),
        }
    ]

    collected = {"recipe": None, "script": None, "shots": None}

    # Agentic loop — keep going until Claude stops calling tools
    while True:
        response = client.messages.create(
            model=llm_id,
            max_tokens=MAX_TOKENS,
            system=AKSHA_SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        # If no tool calls, we're done
        if response.stop_reason == "end_turn":
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input

            # Status feedback to UI
            status_map = {
                "plan_recipe": "🥘 Planning recipe...",
                "write_script": "📝 Writing video script...",
                "plan_shots": "🎬 Planning shot list...",
            }
            _status(status_map.get(tool_name, f"Running {tool_name}..."))

            # Execute
            fn = TOOL_REGISTRY[tool_name]
            result = fn(**tool_input, llm_id=llm_id)

            # Store
            if tool_name == "plan_recipe":
                collected["recipe"] = result
            elif tool_name == "write_script":
                collected["script"] = result
            elif tool_name == "plan_shots":
                collected["shots"] = result

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        # Send tool results back to Claude
        messages.append({"role": "user", "content": tool_results})

    _status("✅ Content package complete!")

    return {
        "user_prompt": user_prompt,
        "recipe": collected["recipe"],
        "script": collected["script"],
        "shots": collected["shots"],
    }
