"""
video_tools.py — Replicate Kling / Minimax video generation + FFmpeg assembly (Phase 3).
"""

import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import replicate
from dotenv import load_dotenv

load_dotenv()

# ── Tool 6: generate_video_clip ──────────────────────────────────────────────────

def generate_video_clip(
    start_frame_path: str,
    end_frame_path: str,
    shot_description: str,
    shot_number: int,
    model_id: str,
    run_folder: Path,
) -> Path:
    """
    Generate a 5-second video clip using Replicate (Kling or Minimax).
    Polls until complete (timeout 10 mins).
    """
    clips_dir = run_folder / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    out_path = clips_dir / f"shot_{shot_number:02d}.mp4"

    # Adapt inputs based on model
    is_minimax = "minimax" in model_id.lower()
    
    # Need to keep file handles open until replicate.run or create submits
    first_file = None
    end_file = None
    
    try:
        inputs = {}
        # Minimax v01: prompt, first_frame_image
        # Kling v1.6: prompt, start_image, end_image, duration
        if start_frame_path and os.path.exists(start_frame_path):
            first_file = open(start_frame_path, "rb")
            if is_minimax:
                inputs["prompt"] = shot_description
                inputs["first_frame_image"] = first_file
            else:
                inputs["prompt"] = shot_description
                inputs["start_image"] = first_file
                inputs["duration"] = 5
        
        if not is_minimax and end_frame_path and os.path.exists(end_frame_path):
            end_file = open(end_frame_path, "rb")
            inputs["end_image"] = end_file

        # Replicate models require distinct polling if it's async
        # To avoid file handle issues, we use replicate.run which handles polling internally,
        # but the request asks to "Poll every 10 seconds, timeout 10 mins".
        prediction = replicate.predictions.create(
            model=model_id,
            input=inputs
        )
    finally:
        # We can close these after the API request is made
        if first_file: first_file.close()
        if end_file: end_file.close()

    # Poll manually every 10 seconds, timeout 10 mins (600s)
    start_time = time.time()
    timeout = 600

    while True:
        prediction.reload()
        if prediction.status in ["succeeded", "failed", "canceled"]:
            break
        if time.time() - start_time > timeout:
            prediction.cancel()
            raise TimeoutError(f"Video generation timed out after {timeout}s for shot {shot_number}")
        time.sleep(10)

    if prediction.status == "failed":
        raise RuntimeError(f"Video generation failed: {prediction.error}")
    if prediction.status == "canceled":
        raise RuntimeError(f"Video generation was canceled for shot {shot_number}")

    output_res = prediction.output
    if isinstance(output_res, list) and len(output_res) > 0:
        video_url = output_res[0]
    elif hasattr(output_res, "url"):
        video_url = output_res.url
    elif isinstance(output_res, str):
        video_url = output_res
    elif hasattr(output_res, "read"):
        with open(out_path, "wb") as f:
            f.write(output_res.read())
        return out_path
    else:
        raise ValueError(f"Unexpected output format from Replicate: {output_res}")

    # Replicate returns URL strings or URLs wrapped in objects
    if hasattr(video_url, "url"):
        video_url = video_url.url
    
    urllib.request.urlretrieve(str(video_url), out_path)
    return out_path


# ── Tool 7: assemble_video ───────────────────────────────────────────────────────

def check_ffmpeg_installed():
    """Verify FFmpeg is installed and accessible in PATH."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def assemble_video(clip_paths: list[str], run_folder: Path) -> Path:
    """
    Concatenate video clips using FFmpeg in shot order.
    """
    if not check_ffmpeg_installed():
        raise RuntimeError(
            "FFmpeg is not installed or not found in system PATH. "
            "Please install FFmpeg to assemble clips (e.g. `winget install ffmpeg` on Windows)."
        )

    final_dir = run_folder / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    out_path = final_dir / "aksha_final_video.mp4"

    # FFmpeg concat demuxer requires a text file with "file 'absolute_path'"
    list_path = final_dir / "concat_list.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for clip in clip_paths:
            # Escape paths for FFmpeg safely
            safe_clip = str(Path(clip).absolute()).replace("\\", "/")
            f.write(f"file '{safe_clip}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        str(out_path)
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg assembly failed:\\n{e.stderr}")

    return out_path
