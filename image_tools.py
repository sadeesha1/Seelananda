"""
image_tools.py — Replicate Flux Dev LoRA image generation for Aksha (Phase 2).

Tools:
  build_image_prompts(shots_json, lora_url)  → calls Claude to fill IMAGE_PROMPT_TEMPLATE
  generate_image(prompt, shot_number, frame_type, run_folder, lora_url) → local Path
  generate_all_images(image_prompts_json, run_folder, lora_url, progress_cb) → dict
"""

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


# ── Tool 4: build_image_prompts ────────────────────────────────────────────────

def build_image_prompts(shots_json: dict, lora_url: str = "", llm_id: str = None) -> dict:
    """
    Ask Claude to fill IMAGE_PROMPT_TEMPLATE for each shot (start + end frame).

    Args:
        shots_json: Output dict from plan_shots(), containing shots list.
        lora_url:   LoRA weights URL (informational — passed through to output).
        llm_id:     LLM model ID (e.g., "claude-sonnet-4-6"). Uses CLAUDE_MODEL if None.

    Returns:
        dict with:
          lora_url: str
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

    prompt = f"""You are a Flux image prompt engineer for Aksha, a Sri Lankan cooking influencer.

IMAGE PROMPT TEMPLATE (fill in the placeholders):
{IMAGE_PROMPT_TEMPLATE.replace("{shot_action}", "{{shot_action}}").replace("{camera_angle}", "{{camera_angle}}").replace("{lighting}", "{{lighting}}").replace("{outfit}", "{{outfit}}")}

For each shot below, generate TWO prompts:
1. start_frame_prompt — the beginning moment of the shot
2. end_frame_prompt — the ending moment of the shot (slightly different action/pose)

Both prompts must:
- Always start with "Aksha," (trigger word)
- Fill in shot_action: describe exactly what Aksha or the food looks like in that frame
- Fill in camera_angle: use the shot's angle verbatim
- Fill in lighting: always "warm pink neon accent lighting with natural window light"
- Fill in outfit: choose a fitting casual-chic cooking outfit (e.g. "sage linen apron over cream blouse", "dusty rose oversized shirt")
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
    Generate a single image via Replicate Flux Dev LoRA, save locally.

    Args:
        prompt:      Full Flux image prompt string.
        shot_number: Shot number (for file naming).
        frame_type:  "start" or "end".
        run_folder:  Root output folder for this run (images/ subfolder created inside).
        lora_url:    Replicate LoRA weights URL.

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

            # output is a list of FileOutput objects (or URLs)
            image_obj = output[0] if isinstance(output, list) else output

            # Handle both URL strings and FileOutput objects
            if hasattr(image_obj, "url"):
                image_url = image_obj.url
            elif hasattr(image_obj, "read"):
                # FileOutput — read bytes directly
                with open(out_path, "wb") as f:
                    f.write(image_obj.read())
                return out_path
            else:
                image_url = str(image_obj)

            # Download from URL
            urllib.request.urlretrieve(image_url, out_path)
            return out_path

        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)  # exponential back-off: 2s, 4s
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

    Args:
        image_prompts_json: Output of build_image_prompts().
        run_folder:         Root output folder (images/ created inside).
        lora_url:           Replicate LoRA weights URL.
        progress_cb:        Optional callable(completed: int, total: int, label: str)
                            called after each image finishes.

    Returns:
        dict: {
          "shots": [
            {
              "shot_number": int,
              "shot_name": str,
              "start_frame_prompt": str,
              "end_frame_prompt": str,
              "start_frame_path": str,   # local path or None on failure
              "end_frame_path": str,
              "start_frame_error": str,  # error message or None
              "end_frame_error": str,
            },
            ...
          ]
        }
    """
    prompts = image_prompts_json.get("prompts", [])

    # Build flat task list: (shot_num, shot_name, frame_type, prompt)
    tasks = []
    for p in prompts:
        tasks.append((p["shot_number"], p["shot_name"], "start", p["start_frame_prompt"]))
        tasks.append((p["shot_number"], p["shot_name"], "end",   p["end_frame_prompt"]))

    total = len(tasks)
    completed_count = 0

    # results keyed by (shot_number, frame_type)
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

    # Assemble ordered output
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
