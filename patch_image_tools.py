import re

with open('image_tools.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update generate_all_images signature
text = text.replace(
"""def generate_all_images(
    image_prompts_json: dict,
    run_folder: Path,
    lora_url: str,
    progress_cb=None,
) -> dict""",
"""def generate_all_images(
    image_prompts_json: dict,
    run_folder: Path,
    lora_url: str,
    image_model_id: str,
    progress_cb=None,
) -> dict"""
)

# update call to generate_image inside generate_all_images
text = text.replace(
"""            path = generate_image(
                prompt=prompt_str,
                shot_number=shot_num,
                frame_type=frame_type,
                run_folder=run_folder,
                lora_url=lora_url,
            )""",
"""            path = generate_image(
                prompt=prompt_str,
                shot_number=shot_num,
                frame_type=frame_type,
                run_folder=run_folder,
                lora_url=lora_url,
                image_model_id=image_model_id,
            )"""
)

# 2. Update generate_image signature
text = text.replace(
"""def generate_image(
    prompt: str,
    shot_number: int,
    frame_type: str,
    run_folder: Path,
    lora_url: str,
) -> Path""",
"""def generate_image(
    prompt: str,
    shot_number: int,
    frame_type: str,
    run_folder: Path,
    lora_url: str,
    image_model_id: str,
) -> Path"""
)

# 3. Update the execution logic in generate_image
old_run_block = """            output = replicate.run(
                FLUX_DEV_LORA_MODEL,
                input={
                    "prompt": prompt,
                    "hf_lora": lora_url,
                    "lora_scale": LORA_SCALE,
                    "width": IMAGE_WIDTH,
                    "height": IMAGE_HEIGHT,
                    "num_inference_steps": INFERENCE_STEPS,
                    "guidance_scale": GUIDANCE_SCALE,
                    "output_format": "png",
                    "output_quality": 100,
                },
            )"""

new_run_block = """            payload = {
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
            
            output = replicate.run(
                image_model_id,
                input=payload,
            )"""

text = text.replace(old_run_block, new_run_block)

with open('image_tools.py', 'w', encoding='utf-8') as f:
    f.write(text)
