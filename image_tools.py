"""
image_tools.py — Replicate image generation for Aksha (Phase 2).

Tools:
  build_style_guide(clothing_images, background_images, kitchenware_images, llm_id)
      → Analyze reference images and return a locked style guide JSON

  build_image_prompts(shots_json, lora_url, llm_id, style_guide)
      → calls LLM to fill IMAGE_PROMPT_TEMPLATE, enforcing style_guide consistency

  generate_image(prompt, shot_number, frame_type, run_folder, lora_url, image_model_id)
      → local Path

  generate_all_images(image_prompts_json, run_folder, lora_url, image_model_id, progress_cb)
      → dict
"""

import base64
import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import replicate
import anthropic

# Ensure Replicate API key is set and create client
replicate_api_key = os.environ.get("REPLICATE_API_KEY")
if not replicate_api_key:
    raise RuntimeError(
        "REPLICATE_API_KEY not found in environment. "
        "Add it to your .env file: REPLICATE_API_KEY=your_key_here"
    )
replicate_client = replicate.Client(api_token=replicate_api_key)

from config import (
    AKSHA_SYSTEM_PROMPT,
    CLAUDE_MODEL,
    IMAGE_PROMPT_TEMPLATE,
    MAX_TOKENS,
)
from llm_adapter import get_llm_response

# ── Constants ──────────────────────────────────────────────────────────────────
FLUX_DEV_LORA_MODEL = "lucataco/flux-dev-lora:a22c463f11808b96047855b1e8d9ac0a" \
                      "13dc5eeb489c2b2507c5fca2c7b1c0d9"
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920
LORA_SCALE = 0.85
INFERENCE_STEPS = 28
GUIDANCE_SCALE = 3.5
MAX_RETRIES = 3
MAX_WORKERS = 4  # Parallel Replicate calls


# ── Style guide builder (vision) ───────────────────────────────────────────────

def build_style_guide(
    clothing_images: list,
    background_images: list,
    kitchenware_images: list,
    llm_id: str = None,
) -> dict:
    """
    Analyze reference images via LLM vision and return a locked style guide JSON.
    The style guide is then passed to build_image_prompts to enforce consistency
    across all generated frames.

    Args:
        clothing_images:    List of image bytes (up to 5) for outfit references.
        background_images:  List of image bytes (up to 5) for kitchen/background refs.
        kitchenware_images: List of image bytes (up to 5) for tool/kitchenware refs.
        llm_id:             LLM model ID. Uses CLAUDE_MODEL if None.

    Returns:
        dict with keys: clothing, background, kitchenware (only sections with images).
        Example:
        {
          "clothing": {
            "outfit_description": "sage linen apron over cream blouse",
            "colors": ["sage green", "cream"],
            "key_details": "apron strings tied at waist, loose relaxed fit"
          },
          "background": {
            "description": "modern kitchen with terracotta floor tiles",
            "key_elements": ["copper pots hanging", "pink neon strip light"],
            "lighting": "warm natural window light from left, pink neon accent"
          },
          "kitchenware": {
            "items": ["copper saucepan", "wooden cutting board"],
            "style": "artisanal handmade aesthetic",
            "key_details": "copper and wood dominant, aged patina finish"
          }
        }
    """
    if llm_id is None:
        llm_id = CLAUDE_MODEL

    def _to_b64(file_bytes: bytes) -> str:
        return base64.b64encode(file_bytes).decode("utf-8")

    def _img_media_type(file_bytes: bytes) -> str:
        """Detect image media type from magic bytes (Python 3.13 compatible)."""
        if file_bytes.startswith(b'\xff\xd8\xff'):
            return "image/jpeg"
        elif file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return "image/png"
        elif file_bytes.startswith(b'RIFF') and b'WEBP' in file_bytes[:20]:
            return "image/webp"
        elif file_bytes.startswith(b'GIF87a') or file_bytes.startswith(b'GIF89a'):
            return "image/gif"
        else:
            return "image/jpeg"  # default fallback

    sections = {}
    if clothing_images:
        sections["clothing"] = clothing_images[:5]
    if background_images:
        sections["background"] = background_images[:5]
    if kitchenware_images:
        sections["kitchenware"] = kitchenware_images[:5]

    if not sections:
        return {}

    system = (
        "You are a visual style analyst for Aksha, a Sri Lankan cooking influencer. "
        "Analyse the provided reference images and extract precise, detailed style "
        "descriptions that can lock visual consistency across AI-generated images."
    )

    section_labels = {
        "clothing": "CLOTHING / OUTFIT REFERENCES",
        "background": "KITCHEN / BACKGROUND REFERENCES",
        "kitchenware": "KITCHENWARE / TOOLS REFERENCES",
    }

    instructions = (
        "Analyse the reference images provided and return a JSON style guide.\n\n"
        "For each section, describe the visual elements with enough precision that an "
        "AI image model can reproduce them identically in every frame.\n\n"
        "Return ONLY valid JSON (no markdown):\n"
        "{\n"
        '  "clothing": {\n'
        '    "outfit_description": "<exact full outfit description>",\n'
        '    "colors": ["<color1>", "<color2>"],\n'
        '    "key_details": "<fabrics, fit, accessories, apron style, etc>"\n'
        "  },\n"
        '  "background": {\n'
        '    "description": "<full kitchen/background scene description>",\n'
        '    "key_elements": ["<element1>", "<element2>"],\n'
        '    "lighting": "<exact lighting setup — direction, color temperature, accent lights>"\n'
        "  },\n"
        '  "kitchenware": {\n'
        '    "items": ["<item1>", "<item2>"],\n'
        '    "style": "<overall aesthetic>",\n'
        '    "key_details": "<materials, colors, arrangement, patina, brand cues>"\n'
        "  }\n"
        "}\n\n"
        "Only include keys for sections that had reference images."
    )

    if llm_id.startswith("claude"):
        client = anthropic.Anthropic()
        content = [{"type": "text", "text": instructions}]
        for section_name, images in sections.items():
            content.append({"type": "text", "text": f"\n\n--- {section_labels[section_name]} ---"})
            for img_bytes in images:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": _img_media_type(img_bytes),
                        "data": _to_b64(img_bytes),
                    },
                })
        response = client.messages.create(
            model=llm_id,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        raw = response.content[0].text.strip()
    else:
        # OpenAI-compatible — SambaNova Llama-4 supports vision via data URLs
        try:
            from sambanova import SambaNova
        except ImportError:
            raise RuntimeError("sambanova package not installed. Run: pip install sambanova")
        client = SambaNova(api_key=os.environ.get("SAMBANOVA_API_KEY"))
        content = [{"type": "text", "text": instructions}]
        for section_name, images in sections.items():
            content.append({"type": "text", "text": f"\n\n--- {section_labels[section_name]} ---"})
            for img_bytes in images:
                media_type = _img_media_type(img_bytes)
                b64 = _to_b64(img_bytes)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{b64}"},
                })
        response = client.chat.completions.create(
            model=llm_id,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()

    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        return {}


# ── Tool 4: build_image_prompts ────────────────────────────────────────────────

def build_image_prompts(
    shots_json: dict,
    lora_url: str = "",
    llm_id: str = None,
    style_guide: dict = None,
) -> dict:
    """
    Ask the LLM to fill IMAGE_PROMPT_TEMPLATE for each shot (start + end frame).
    When style_guide is provided, the LLM is instructed to lock outfit, background,
    and kitchenware identically across all shots to maintain visual consistency.

    Args:
        shots_json:   Output dict from plan_shots(), containing shots list.
        lora_url:     LoRA weights URL (informational — passed through to output).
        llm_id:       LLM model ID (e.g., "claude-sonnet-4-6"). Uses CLAUDE_MODEL if None.
        style_guide:  Optional dict from build_style_guide(). When provided, all shots
                      will use the exact same outfit, background, and kitchenware.

    Returns:
        dict with:
          lora_url: str
          style_guide: dict (echoed back)
          prompts: list of {shot_number, shot_name, start_frame_prompt, end_frame_prompt}
    """
    if llm_id is None:
        llm_id = CLAUDE_MODEL
    shots = shots_json.get("shots", [])

    shot_descriptions = "\n".join(
        f"Shot {s['shot_number']} — {s['shot_name']}\n"
        f"  camera_angle: {s['camera_angle']}\n"
        f"  action: {s['action_description']}\n"
        f"  prop_focus: {s['prop_focus']}\n"
        f"  duration: {s['duration_seconds']}s"
        for s in shots
    )

    # Build style constraint block
    if style_guide:
        clothing = style_guide.get("clothing", {})
        background = style_guide.get("background", {})
        kitchenware = style_guide.get("kitchenware", {})

        style_block = "\n\nSTYLE GUIDE — LOCKED FOR ALL SHOTS (copy these exactly, do NOT vary between shots):\n"
        if clothing:
            style_block += (
                f"\nOUTFIT (use verbatim in every shot):\n"
                f"  outfit_description: {clothing.get('outfit_description', '')}\n"
                f"  colors: {', '.join(clothing.get('colors', []))}\n"
                f"  key_details: {clothing.get('key_details', '')}\n"
            )
        if background:
            style_block += (
                f"\nBACKGROUND (use verbatim in every shot):\n"
                f"  description: {background.get('description', '')}\n"
                f"  key_elements: {', '.join(background.get('key_elements', []))}\n"
                f"  lighting: {background.get('lighting', '')}\n"
            )
        if kitchenware:
            style_block += (
                f"\nKITCHENWARE (reference where visible):\n"
                f"  items: {', '.join(kitchenware.get('items', []))}\n"
                f"  style: {kitchenware.get('style', '')}\n"
                f"  key_details: {kitchenware.get('key_details', '')}\n"
            )

        outfit_instruction = (
            "- Fill in outfit: USE EXACTLY the outfit_description from the STYLE GUIDE above — "
            "identical across every single shot"
        )
        lighting_instruction = (
            "- Fill in lighting: USE EXACTLY the lighting from the STYLE GUIDE above — "
            "identical across every single shot"
        )
        background_instruction = (
            "- Background: include the background description from the STYLE GUIDE verbatim — "
            "same kitchen, same elements, same layout in every shot"
        )
    else:
        style_block = ""
        outfit_instruction = (
            '- Fill in outfit: choose ONE casual-chic cooking outfit and use it for ALL shots '
            '(e.g. "sage linen apron over cream blouse") — must be identical in every prompt'
        )
        lighting_instruction = (
            '- Fill in lighting: use "warm pink neon accent lighting with natural window light" '
            "for every shot — identical in all prompts"
        )
        background_instruction = (
            "- Background: always the same modern kitchen with terracotta tiles, copper pots, "
            "and pink neon accent lighting — consistent in every shot"
        )

    prompt = f"""You are a Flux image prompt engineer for Aksha, a Sri Lankan cooking influencer.
{style_block}
IMAGE PROMPT TEMPLATE (fill in the placeholders):
{IMAGE_PROMPT_TEMPLATE.replace("{shot_action}", "{{shot_action}}").replace("{camera_angle}", "{{camera_angle}}").replace("{lighting}", "{{lighting}}").replace("{outfit}", "{{outfit}}")}

For each shot below, generate TWO prompts:
1. start_frame_prompt — the beginning moment of the shot
2. end_frame_prompt — the ending moment of the shot (slightly different action/pose only)

CONSISTENCY RULES — every prompt in this batch must be identical for these elements:
{outfit_instruction}
{lighting_instruction}
{background_instruction}
- Only shot_action should vary between start and end frames — never outfit, background, or lighting

Both prompts must:
- Always start with "Aksha," (trigger word)
- Fill in shot_action: describe exactly what Aksha or the food looks like in that frame
- Fill in camera_angle: use the shot's angle verbatim
- Be vivid, specific, cinematic — describe textures, steam, drips, hands, expressions

SHOTS:
{shot_descriptions}

Return ONLY a valid JSON object (no markdown):
{{
  "prompts": [
    {{
      "shot_number": <int>,
      "shot_name": "<name>",
      "start_frame_prompt": "<full prompt string>",
      "end_frame_prompt": "<full prompt string>"
    }},
    ...
  ]
}}"""

    raw = get_llm_response(prompt, AKSHA_SYSTEM_PROMPT, MAX_TOKENS, llm_id).strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    result = json.loads(raw)
    result["lora_url"] = lora_url
    result["style_guide"] = style_guide or {}
    return result


# ── Tool 5: generate_image ─────────────────────────────────────────────────────

def generate_image(
    prompt: str,
    shot_number: int,
    frame_type: str,
    run_folder: Path,
    lora_url: str,
    image_model_id: str,
) -> Path:
    """
    Generate a single image via Replicate, save locally.

    Args:
        prompt:         Full image prompt string.
        shot_number:    Shot number (for file naming).
        frame_type:     "start" or "end".
        run_folder:     Root output folder for this run (images/ subfolder created inside).
        lora_url:       Optional Replicate LoRA weights URL (empty string to skip).
        image_model_id: Replicate model ID.

    Returns:
        Path to saved local PNG file.

    Raises:
        RuntimeError after MAX_RETRIES failures.
    """
    images_dir = run_folder / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    out_path = images_dir / f"shot_{shot_number:02d}_{frame_type}.png"

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            payload = {
                "prompt": prompt,
                "width": IMAGE_WIDTH,
                "height": IMAGE_HEIGHT,
                "output_format": "png",
            }
            if "flux" in image_model_id.lower():
                payload["num_inference_steps"] = INFERENCE_STEPS
                payload["guidance_scale"] = GUIDANCE_SCALE
                payload["output_quality"] = 100
                if lora_url and lora_url.strip():
                    payload["hf_lora"] = lora_url
                    payload["lora_scale"] = LORA_SCALE

            output = replicate_client.run(
                image_model_id,
                input=payload,
            )

            image_obj = output[0] if isinstance(output, list) else output

            if hasattr(image_obj, "url"):
                image_url = image_obj.url
            elif hasattr(image_obj, "read"):
                with open(out_path, "wb") as f:
                    f.write(image_obj.read())
                return out_path
            else:
                image_url = str(image_obj)

            urllib.request.urlretrieve(image_url, out_path)
            return out_path

        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
            continue

    raise RuntimeError(
        f"Failed to generate shot {shot_number} {frame_type} "
        f"after {MAX_RETRIES} attempts: {last_exc}"
    )


# ── Batch: generate all images in parallel ────────────────────────────────────

def generate_all_images(
    image_prompts_json: dict,
    run_folder: Path,
    lora_url: str,
    image_model_id: str,
    progress_cb=None,
) -> dict:
    """
    Generate all start + end frames for all shots in parallel.
    """
    prompts = image_prompts_json.get("prompts", [])

    tasks = []
    for p in prompts:
        tasks.append((p["shot_number"], p["shot_name"], "start", p["start_frame_prompt"]))
        tasks.append((p["shot_number"], p["shot_name"], "end",   p["end_frame_prompt"]))

    total = len(tasks)
    completed_count = 0
    results: dict[tuple, dict] = {}

    def _run_one(task):
        shot_num, shot_name, frame_type, prompt_str = task
        try:
            path = generate_image(
                prompt=prompt_str,
                shot_number=shot_num,
                frame_type=frame_type,
                run_folder=run_folder,
                lora_url=lora_url,
                image_model_id=image_model_id,
            )
            return (shot_num, shot_name, frame_type, str(path), None)
        except Exception as exc:
            return (shot_num, shot_name, frame_type, None, str(exc))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(_run_one, t): t for t in tasks}
        for future in as_completed(future_map):
            shot_num, shot_name, frame_type, path, err = future.result()
            results[(shot_num, frame_type)] = {
                "path": path,
                "error": err,
                "shot_name": shot_name,
            }
            completed_count += 1
            if progress_cb:
                label = f"Shot {shot_num} ({frame_type} frame)"
                progress_cb(completed_count, total, label)

    shot_outputs = []
    for p in prompts:
        sn = p["shot_number"]
        start_r = results.get((sn, "start"), {})
        end_r   = results.get((sn, "end"), {})
        shot_outputs.append({
            "shot_number":        sn,
            "shot_name":          p["shot_name"],
            "start_frame_prompt": p["start_frame_prompt"],
            "end_frame_prompt":   p["end_frame_prompt"],
            "start_frame_path":   start_r.get("path"),
            "end_frame_path":     end_r.get("path"),
            "start_frame_error":  start_r.get("error"),
            "end_frame_error":    end_r.get("error"),
        })

    return {"shots": shot_outputs}
