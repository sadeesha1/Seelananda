"""
app.py — Streamlit UI for Aksha AI Content Agent (Phase 1: Text Pipeline)
"""

import json
import os
import traceback
from datetime import datetime
from pathlib import Path

import anthropic
import streamlit as st
from dotenv import load_dotenv

from agent import run_agent
from config import OUTPUT_DIR, REPLICATE_LORA_URL, IMAGE_MODELS, LLM_MODELS
from image_tools import build_image_prompts, build_style_guide, generate_all_images, generate_image
from video_tools import assemble_video, generate_video_clip
from caption_tools import write_captions

load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Aksha Studio",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,700;1,700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
  }

  /* Cream background */
  .stApp {
    background: #fcf9f2;
    color: #4a3f35;
    min-height: 100vh;
  }

  /* Hero header */
  .hero-header {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
  }
  .hero-title {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    font-style: italic;
    color: #c75b42; /* Terracotta */
    margin: 0;
    line-height: 1.2;
  }
  .hero-sub {
    color: #8c7a6b;
    font-size: 1rem;
    font-weight: 300;
    margin-top: 0.5rem;
    letter-spacing: 0.05em;
  }

  /* Input area */
  .stTextInput > div > div > input {
    background: #ffffff !important;
    border: 1px solid rgba(199,91,66,0.3) !important;
    border-radius: 12px !important;
    color: #4a3f35 !important;
    font-size: 1.05rem !important;
    padding: 0.85rem 1.2rem !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #c75b42 !important;
    box-shadow: 0 0 0 2px rgba(199,91,66,0.2) !important;
  }
  .stTextInput > div > div > input::placeholder {
    color: #baa89b !important;
  }

  /* Generate button */
  .stButton > button {
    background: #c75b42 !important;
    color: #fcf9f2 !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.75rem 2.5rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(199,91,66,0.3) !important;
    width: 100% !important;
  }
  .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(199,91,66,0.4) !important;
    background: #a94b34 !important;
  }

  /* Expander styling */
  .streamlit-expanderHeader {
    background: #ffffff !important;
    border: 1px solid rgba(199,91,66,0.15) !important;
    border-radius: 10px !important;
    color: #4a3f35 !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
  }
  .streamlit-expanderContent {
    background: #faf7f0 !important;
    border: 1px solid rgba(199,91,66,0.1) !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
    color: #4a3f35 !important;
  }
  
  /* Badges */
  .shot-badge {
    color: #c75b42 !important;
    background: rgba(199,91,66,0.1) !important;
  }
  
  .hashtag-badge {
    background: rgba(199,91,66,0.1);
    color: #c75b42;
    padding: 0.3rem 0.6rem;
    border-radius: 5px;
    font-size: 0.85rem;
    font-weight: 500;
    margin: 0.2rem;
    display: inline-block;
  }
  .hashtag-badge.broad {
    background: rgba(140,122,107,0.1);
    color: #8c7a6b;
  }
  .hashtag-badge.lifestyle {
    background: rgba(216,162,109,0.15);
    color: #b57a40;
  }

  /* Cards inside expanders */
  .script-card {
    background: #ffffff;
    border: 1px solid rgba(199,91,66,0.15);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
  }
  .script-card .label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #c75b42;
    margin-bottom: 0.3rem;
  }
  .script-card .section-name {
    font-size: 1rem;
    font-weight: 700;
    color: #b57a40;
    margin-bottom: 0.6rem;
  }
  .script-card .voiceover {
    color: #5c4f44;
    font-size: 0.95rem;
    line-height: 1.6;
    margin-bottom: 0.5rem;
  }
  .script-card .onscreen {
    background: rgba(199,91,66,0.12);
    color: #c75b42;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.3rem 0.7rem;
    border-radius: 6px;
    display: inline-block;
  }
  .script-card .timing {
    color: #8c7a6b;
    font-size: 0.8rem;
    margin-top: 0.5rem;
  }

  /* Shot cards */
  .shot-card {
    background: #ffffff;
    border-left: 3px solid #ff6eb4;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
  }
  .shot-card .shot-num {
    font-size: 0.7rem;
    font-weight: 700;
    color: #c75b42;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .shot-card .shot-name {
    font-size: 0.95rem;
    font-weight: 700;
    color: #f0e6ff;
    margin: 0.15rem 0;
  }
  .shot-card .shot-detail {
    color: #a090c0;
    font-size: 0.85rem;
    line-height: 1.5;
  }
  .shot-card .shot-badge {
    display: inline-block;
    background: rgba(199,91,66,0.15);
    color: #c75b42;
    font-size: 0.75rem;
    padding: 0.15rem 0.6rem;
    border-radius: 20px;
    margin-right: 0.4rem;
    margin-top: 0.35rem;
  }

  /* Status / info messages */
  .status-box {
    background: rgba(199,91,66,0.08);
    border: 1px solid rgba(199,91,66,0.25);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    color: #d4b8f0;
    font-size: 0.95rem;
    margin: 1rem 0;
  }

  /* Save path pill */
  .save-pill {
    display: inline-block;
    background: rgba(100,255,180,0.1);
    border: 1px solid rgba(100,255,180,0.25);
    color: #64ffb4;
    font-size: 0.8rem;
    padding: 0.3rem 0.9rem;
    border-radius: 20px;
    margin-top: 0.5rem;
    font-family: monospace;
  }

  /* Divider */
  hr { border-color: rgba(199,91,66,0.15) !important; }

  /* Streamlit default text overrides */
  p, li, span { color: #c8b8e8; }
  h1, h2, h3, h4 { color: #f0e6ff; }
  th { color: #c75b42 !important; }
  td { color: #5c4f44 !important; }
</style>
""", unsafe_allow_html=True)



# ── Header & Stats ─────────────────────────────────────────────────────────────
def get_run_stats():
    runs = []
    total_vids = 0
    last_date = "Never"
    if OUTPUT_DIR.exists():
        for item in OUTPUT_DIR.iterdir():
            if item.is_dir() and (item / "content_package.json").exists():
                runs.append(item)
                if (item / "final" / "aksha_final_video.mp4").exists():
                    total_vids += 1
    runs.sort(key=lambda x: x.name, reverse=True)
    if runs:
        try:
            date_str = runs[0].name.split("_", 1)[0]
            last_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            last_date = "Recently"
    return len(runs), total_vids, last_date, runs

tot_runs, tot_vids, last_run, all_runs = get_run_stats()

st.markdown("""
<div class="hero-header">
  <p class="hero-title">Aksha Studio</p>
  <p class="hero-sub">AI Workflow Console</p>
</div>
""", unsafe_allow_html=True)

colH1, colH2, colH3 = st.columns(3)
colH1.metric("Total Runs", tot_runs)
colH2.metric("Total Videos", tot_vids)
colH3.metric("Last Run", last_run)
st.divider()



# ── Input section ──────────────────────────────────────────────────────────────
col_input, col_btn1, col_btn2 = st.columns([5, 1, 2], vertical_alignment="bottom")

with col_input:
    user_prompt = st.text_input(
        label="What is Aksha cooking today?",
        placeholder="Describe what Aksha is cooking today...",
        label_visibility="collapsed",
        key="user_prompt_input",
    )

with col_btn1:
    generate_clicked = st.button("🍰 Generate", use_container_width=True)

with col_btn2:
    full_run_clicked = st.button("🚀 Generate Everything", use_container_width=True)


# ── Session state initialization ────────────────────────────────────────────────
if "content_package" not in st.session_state:
    st.session_state.content_package = None
if "last_error_msg" not in st.session_state:
    st.session_state.last_error_msg = None
if "last_error_trace" not in st.session_state:
    st.session_state.last_error_trace = None
if "save_path" not in st.session_state:
    st.session_state.save_path = None
if "run_folder" not in st.session_state:
    st.session_state.run_folder = None
# Style guide state
if "style_guide" not in st.session_state:
    st.session_state.style_guide = {}
if "style_guide_error" not in st.session_state:
    st.session_state.style_guide_error = None
# Phase 2 image state
if "image_prompts" not in st.session_state:
    st.session_state.image_prompts = None
if "image_results" not in st.session_state:
    st.session_state.image_results = None
if "img_error_msg" not in st.session_state:
    st.session_state.img_error_msg = None
# Phase 3 video state
if "video_clips" not in st.session_state:
    st.session_state.video_clips = {}
if "video_error_msg" not in st.session_state:
    st.session_state.video_error_msg = None
if "final_video_path" not in st.session_state:
    st.session_state.final_video_path = None
# Phase 4 captions state
if "captions" not in st.session_state:
    st.session_state.captions = None
if "cap_error_msg" not in st.session_state:
    st.session_state.cap_error_msg = None

# ── Sidebar — LoRA config ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧠 Master AI Agent")
    llm_choice_key = st.selectbox(
        "LLM Model",
        options=list(LLM_MODELS.keys()),
        index=0,
        help="Select the LLM brain to power the agent."
    )
    llm_id = LLM_MODELS[llm_choice_key]
    st.divider()
    st.markdown("## 🎨 Image Settings")
    image_model_choice = st.selectbox(
        "Image Model",
        options=list(IMAGE_MODELS.keys()),
        index=1,
        help="Select the AI image model to use for generation."
    )
    
    st.markdown("Paste your Replicate LoRA URL below if using a Flux model.")
    lora_url_input = st.text_input(
        label="LoRA Weights URL",
        value=REPLICATE_LORA_URL,
        placeholder="https://replicate.delivery/your-lora-url or HF path",
        help="Your trained Flux LoRA for Aksha. Paste the Replicate delivery URL or HuggingFace path.",
        key="lora_url",
    )
    st.caption("Trigger word: **Aksha** (always included in prompts)")
    st.divider()
    
    st.markdown("## 🎬 Video Settings")
    video_model_choice = st.selectbox(
        "Video Model",
        options=["Kling v1.6", "Minimax video-01"],
        help="Select the AI video model to use for clip generation."
    )
    if video_model_choice == "Kling v1.6":
        video_model_id = "klingai/kling-video"
    else:
        video_model_id = "minimax/video-01"
        
    st.divider()
    st.markdown("**Image settings**")
    st.caption("1080 × 1920 · 28 steps · LoRA scale 0.85")
    st.divider()
    st.markdown("## 📸 Style References")
    st.caption("Upload reference images to lock consistent outfit, background, and kitchenware across all generated frames.")

    with st.expander("👗 Clothing References (up to 5)"):
        clothing_uploads = st.file_uploader(
            "Outfit / clothing references",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="clothing_refs",
            label_visibility="collapsed",
        )
        if clothing_uploads:
            st.caption(f"{min(len(clothing_uploads), 5)} image(s) uploaded")

    with st.expander("🏠 Background References (up to 5)"):
        background_uploads = st.file_uploader(
            "Kitchen / background references",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="background_refs",
            label_visibility="collapsed",
        )
        if background_uploads:
            st.caption(f"{min(len(background_uploads), 5)} image(s) uploaded")

    with st.expander("🍳 Kitchenware References (up to 5)"):
        kitchenware_uploads = st.file_uploader(
            "Kitchenware / tools references",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="kitchenware_refs",
            label_visibility="collapsed",
        )
        if kitchenware_uploads:
            st.caption(f"{min(len(kitchenware_uploads), 5)} image(s) uploaded")

    any_refs = any([clothing_uploads, background_uploads, kitchenware_uploads])
    analyze_clicked = st.button(
        "🔍 Analyse References",
        key="analyze_refs_btn",
        disabled=not any_refs,
        use_container_width=True,
    )

    if analyze_clicked and any_refs:
        st.session_state.style_guide_error = None
        with st.spinner("Analysing reference images..."):
            try:
                st.session_state.style_guide = build_style_guide(
                    clothing_images=[f.read() for f in (clothing_uploads or [])[:5]],
                    background_images=[f.read() for f in (background_uploads or [])[:5]],
                    kitchenware_images=[f.read() for f in (kitchenware_uploads or [])[:5]],
                    llm_id=llm_id,
                )
            except Exception as e:
                st.session_state.style_guide_error = str(e)

    if st.session_state.style_guide_error:
        st.error(f"Style analysis failed: {st.session_state.style_guide_error}")

    if st.session_state.style_guide:
        st.success("✅ Style guide active — consistency locked")
        with st.expander("📋 View Style Guide JSON"):
            st.json(st.session_state.style_guide)
        if st.button("🗑 Clear Style Guide", key="clear_style_btn"):
            st.session_state.style_guide = {}
            st.rerun()

    st.divider()
    st.markdown("## 🗂 Run History")
    for run_dir in all_runs[:10]: # show last 10
        try:
            pkg_path = run_dir / "content_package.json"
            with open(pkg_path, "r", encoding="utf-8") as f:
                rpkg = json.load(f)
            dname = rpkg.get("recipe", {}).get("dish_name", "Unknown Dish")
            rtime = run_dir.name.split("_", 1)[0]
            fmt_rtime = f"{rtime[:4]}-{rtime[4:6]}-{rtime[6:8]}"
            
            with st.container():
                st.markdown(f"**{dname}**\n*{fmt_rtime}*")
                # Thumbnail
                imgs = rpkg.get("image_results", {}).get("shots", [])
                if imgs and imgs[0].get("start_frame_path"):
                    if Path(imgs[0]["start_frame_path"]).exists():
                        st.image(imgs[0]["start_frame_path"])
                if st.button(f"Load '{dname}'", key=f"load_{run_dir.name}"):
                    st.session_state.content_package = rpkg
                    st.session_state.run_folder = str(run_dir)
                    st.session_state.save_path = str(pkg_path)
                    
                    st.session_state.image_prompts = rpkg.get("image_prompts", None)
                    st.session_state.image_results = rpkg.get("image_results", None)
                    st.session_state.video_clips = rpkg.get("video_results", {})
                    st.session_state.final_video_path = rpkg.get("final_video", None)
                    st.rerun()
                st.markdown("<hr style='margin:0.5rem 0'>", unsafe_allow_html=True)
        except Exception:
            pass


# ── Helpers ───────────────────────────────────────────────────────────────────
def _make_run_folder(package: dict) -> Path:
    """Create a timestamped output folder for this run (idempotent if already created)."""
    dish_name = (package.get("recipe", {}) or {}).get("dish_name", "content")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in dish_name).lower()
    if st.session_state.run_folder:
        return Path(st.session_state.run_folder)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = OUTPUT_DIR / f"{timestamp}_{safe_name}"
    folder.mkdir(parents=True, exist_ok=True)
    st.session_state.run_folder = str(folder)
    return folder


def save_content_package(package: dict, folder: Path | None = None) -> Path:
    """Save the content package JSON to output/ subfolder."""
    if folder is None:
        folder = _make_run_folder(package)
    out_file = folder / "content_package.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2, ensure_ascii=False)
    return out_file


if generate_clicked or full_run_clicked:
    if not user_prompt.strip():
        st.warning("Please describe what Aksha is cooking today! 🍴")
    elif llm_id.startswith("claude") and (not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_anthropic_api_key_here"):
        st.error("⚠️ ANTHROPIC_API_KEY is not set. Please add it to your `.env` file.")
    elif not llm_id.startswith("claude") and (not os.getenv("SAMBANOVA_API_KEY") or os.getenv("SAMBANOVA_API_KEY") == "your_sambanova_api_key_here"):
        st.error("⚠️ SAMBANOVA_API_KEY is not set. Please add it to your `.env` file.")
    else:
        st.session_state.content_package = None
        st.session_state.last_error_msg = None
        st.session_state.last_error_trace = None
        st.session_state.save_path = None

        status_placeholder = st.empty()

        def update_status(msg: str):
            status_placeholder.markdown(
                f'<div class="status-box">⏳ {msg}</div>', unsafe_allow_html=True
            )

        try:
            with st.spinner("Aksha's agent is working its magic..."):
                package = run_agent(user_prompt.strip(), status_callback=update_status, llm_id=llm_id)

            folder = _make_run_folder(package)
            save_path = save_content_package(package, folder)
            st.session_state.content_package = package
            st.session_state.save_path = save_path
            # Reset any stale image/video state from a previous run
            st.session_state.image_prompts = None
            st.session_state.image_results = None
            st.session_state.img_error_msg = None
            st.session_state.video_clips = {}
            st.session_state.video_error_msg = None
            st.session_state.final_video_path = None
            st.session_state.captions = None
            st.session_state.cap_error_msg = None
            status_placeholder.empty()


            if full_run_clicked and not st.session_state.last_error_msg:
                # Automate phase 2
                active_lora = st.session_state.get("lora_url", "").strip()
                status_placeholder.markdown('<div class="status-box">⏳ Generating Images...</div>', unsafe_allow_html=True)
                try:
                    prompts = build_image_prompts(package["shots"], lora_url=active_lora, llm_id=llm_id, style_guide=st.session_state.style_guide or None)
                    st.session_state.image_prompts = prompts
                    st.session_state.image_results = generate_all_images(prompts, folder, active_lora, IMAGE_MODELS[image_model_choice])
                    package.update({"image_prompts": prompts, "image_results": st.session_state.image_results})
                    save_content_package(package, folder)
                except Exception as e:
                    st.session_state.img_error_msg = str(e)

                # Automate phase 3
                if st.session_state.image_results and not st.session_state.img_error_msg:
                    try:
                        results_shots = st.session_state.image_results.get("shots", [])
                        clip_list = []
                        tot = len(results_shots)
                        for idx, s in enumerate(results_shots):
                            status_placeholder.markdown(
                                f'<div class="status-box">⏳ Generating Video Clip {idx + 1} of {tot} (Shot {s["shot_number"]})...</div>',
                                unsafe_allow_html=True
                            )
                            c = generate_video_clip(s.get("start_frame_path"), s.get("end_frame_path"), s["shot_name"], s["shot_number"], video_model_id, folder)
                            st.session_state.video_clips[s["shot_number"]] = str(c)
                            package.setdefault("video_results", {})[s["shot_number"]] = str(c)
                            clip_list.append(str(c))
                        save_content_package(package, folder)
                        
                        status_placeholder.markdown('<div class="status-box">⏳ Assembling final video...</div>', unsafe_allow_html=True)
                        fin = assemble_video(clip_list, folder)
                        st.session_state.final_video_path = str(fin)
                        package["final_video"] = str(fin)
                        save_content_package(package, folder)
                    except Exception as e:
                        st.session_state.video_error_msg = str(e)

                
                # Automate phase 4
                if st.session_state.final_video_path:
                    status_placeholder.markdown('<div class="status-box">⏳ Writing captions...</div>', unsafe_allow_html=True)
                    try:
                        caps = write_captions(package["recipe"], package.get("script", {}), llm_id)
                        st.session_state.captions = caps
                        package["captions"] = caps
                        save_content_package(package, folder)
                    except Exception as e:
                        st.session_state.cap_error_msg = str(e)
                
                status_placeholder.empty()
                st.rerun()

        except anthropic.AuthenticationError as exc:
            st.session_state.last_error_msg = (
                "Anthropic API key is invalid or has no credits. "
                "Check your ANTHROPIC_API_KEY in .env and verify billing at console.anthropic.com."
            )
            st.session_state.last_error_trace = traceback.format_exc()
            status_placeholder.empty()
        except anthropic.PermissionDeniedError as exc:
            st.session_state.last_error_msg = (
                "Anthropic API access denied — account may be suspended or key has no credits. "
                "Check console.anthropic.com."
            )
            st.session_state.last_error_trace = traceback.format_exc()
            status_placeholder.empty()
        except anthropic.APIStatusError as exc:
            # Catch API billing, rate limit, or server errors directly from Anthropic
            st.session_state.last_error_msg = f"Anthropic API Error ({exc.status_code}): {exc.message}"
            st.session_state.last_error_trace = traceback.format_exc()
            status_placeholder.empty()
        except RuntimeError as exc:
            msg = str(exc)
            st.session_state.last_error_msg = msg
            st.session_state.last_error_trace = traceback.format_exc()
            status_placeholder.empty()
        except Exception as exc:
            st.session_state.last_error_msg = str(exc)
            st.session_state.last_error_trace = traceback.format_exc()
            status_placeholder.empty()


# ── Error display with retry ── ────────────────────────────────────────────────
if st.session_state.last_error_msg:
    st.error(f"Something went wrong: {st.session_state.last_error_msg}")
    with st.expander("🔍 Detailed trace"):
        st.code(st.session_state.last_error_trace, language="text")
    if st.button("🔄 Retry", key="retry_btn"):
        st.session_state.last_error_msg = None
        st.session_state.last_error_trace = None
        st.rerun()


# ── Results display ────────────────────────────────────────────────────────────
if st.session_state.content_package:
    pkg = st.session_state.content_package
    recipe = pkg.get("recipe") or {}
    script = pkg.get("script") or {}
    shots_data = pkg.get("shots") or {}

    # Save status
    if st.session_state.save_path:
        st.markdown(
            f'<span class="save-pill">💾 Saved → {st.session_state.save_path}</span>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Recipe Card ───────────────────────────────────────────────────────────
    with st.expander("🥘 Recipe Card", expanded=True):
        st.markdown(f"### {recipe.get('dish_name', 'Dish')}")
        st.markdown(f"*{recipe.get('short_description', '')}*")

        cultural = recipe.get("cultural_angle")
        if cultural:
            st.info(f"🌍 {cultural}")

        st.markdown("**Ingredients**")
        ingredients = recipe.get("ingredients", [])
        if ingredients:
            import pandas as pd
            df = pd.DataFrame(ingredients)
            # Rename columns nicely
            col_map = {"name": "Ingredient", "quantity": "Qty", "unit": "Unit"}
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            st.dataframe(df, hide_index=True, use_container_width=True)

        st.markdown("**Steps**")
        for step in recipe.get("steps", []):
            num = step.get("step_number", "")
            instruction = step.get("instruction", "")
            dur = step.get("duration_seconds", 0)
            mins, secs = divmod(dur, 60)
            time_str = f"{mins}m {secs}s" if mins else f"{secs}s"
            st.markdown(f"**{num}.** {instruction} ⏱ *{time_str}*")

    # ── Script ────────────────────────────────────────────────────────────────
    with st.expander("📝 Video Script", expanded=True):
        hook = script.get("hook", "")
        cta = script.get("cta", "")
        total_dur = script.get("total_duration_seconds", 0)

        col1, col2 = st.columns(2)
        col1.metric("Total Duration", f"{total_dur}s")
        col2.metric("Sections", len(script.get("sections", [])))

        if hook:
            st.markdown(f"**🎣 Hook:** *{hook}*")

        st.markdown("<br>", unsafe_allow_html=True)

        for section in script.get("sections", []):
            name = section.get("section_name", "")
            vo = section.get("voiceover_text", "")
            ons = section.get("on_screen_text", "")
            t_start = section.get("start_time_seconds", 0)
            t_end = section.get("end_time_seconds", 0)

            st.markdown(f"""
<div class="script-card">
  <div class="label">Section</div>
  <div class="section-name">{name}</div>
  <div class="voiceover">🎙 {vo}</div>
  <span class="onscreen">📺 {ons}</span>
  <div class="timing">⏱ {t_start}s – {t_end}s</div>
</div>
""", unsafe_allow_html=True)

        if cta:
            st.markdown(f"**📣 CTA:** {cta}")

    # ── Shot List ─────────────────────────────────────────────────────────────
    with st.expander("🎬 Shot List", expanded=True):
        shots = shots_data.get("shots", [])
        st.markdown(f"**{len(shots)} shots planned**")
        st.markdown("<br>", unsafe_allow_html=True)

        for shot in shots:
            num = shot.get("shot_number", "")
            name = shot.get("shot_name", "")
            angle = shot.get("camera_angle", "")
            action = shot.get("action_description", "")
            prop = shot.get("prop_focus", "")
            dur = shot.get("duration_seconds", 0)
            section = shot.get("corresponding_script_section", "")

            st.markdown(f"""
<div class="shot-card">
  <div class="shot-num">Shot {num}</div>
  <div class="shot-name">{name}</div>
  <div class="shot-detail">{action}</div>
  <span class="shot-badge">📷 {angle}</span>
  <span class="shot-badge">🔍 {prop}</span>
  <span class="shot-badge">⏱ {dur}s</span>
  <span class="shot-badge">📄 {section}</span>
</div>
""", unsafe_allow_html=True)

    # ── Raw JSON ──────────────────────────────────────────────────────────────
    with st.expander("🗂 Raw JSON (content_package)"):
        st.json(pkg)

    # ═══════════════════════════════════════════════════════════════════════════
    # ── Phase 2: IMAGE GENERATION ─────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.markdown("## 🖼 Phase 2 — Generate Images")

    # LoRA URL (optional)
    active_lora = st.session_state.get("lora_url", "").strip()
    if active_lora:
        st.markdown(
            f'<span class="save-pill">🎨 LoRA: {active_lora[:60]}{'...' if len(active_lora) > 60 else ''}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("💡 Tip: Paste a Replicate LoRA URL in the sidebar to use custom weights (optional)")

    # ── Generate Images button ────────────────────────────────────────────────
    gen_images_clicked = st.button(
        "🖼 Generate All Images",
        key="gen_images_btn",
        use_container_width=False,
    )

    if gen_images_clicked:
        st.session_state.img_error_msg = None
        shots_for_images = (pkg.get("shots") or {}).get("shots", [])
        total_images = len(shots_for_images) * 2

        img_progress_bar = st.progress(0, text="Building image prompts with Claude...")
        img_status = st.empty()

        try:
            # Step 1 — Claude builds all prompts
            img_status.markdown(
                '<div class="status-box">🎨 Claude is writing cinematic image prompts...</div>',
                unsafe_allow_html=True,
            )
            image_prompts = build_image_prompts(pkg["shots"], lora_url=active_lora, llm_id=llm_id, style_guide=st.session_state.style_guide or None)
            st.session_state.image_prompts = image_prompts

            # Step 2 — Replicate generates all images in parallel
            run_folder = Path(st.session_state.run_folder) if st.session_state.run_folder else _make_run_folder(pkg)

            def _progress(done, total, label):
                pct = done / total
                img_progress_bar.progress(pct, text=f"Generating image {done} of {total} — {label}")
                img_status.markdown(
                    f'<div class="status-box">🔄 {label}...</div>',
                    unsafe_allow_html=True,
                )

            image_results = generate_all_images(
                image_prompts_json=image_prompts,
                run_folder=run_folder,
                lora_url=active_lora,
                image_model_id=IMAGE_MODELS[image_model_choice],
                progress_cb=_progress,
            )
            st.session_state.image_results = image_results

            # Save updated package with image paths
            pkg["image_prompts"] = image_prompts
            pkg["image_results"] = image_results
            st.session_state.content_package = pkg
            save_content_package(pkg, run_folder)

            img_progress_bar.progress(1.0, text="✅ All images generated!")
            img_status.empty()

        except anthropic.APIStatusError as exc:
            st.session_state.img_error_msg = f"Claude API error: {exc.message}"
            img_progress_bar.empty()
            img_status.empty()
        except Exception as exc:
            st.session_state.img_error_msg = str(exc)
            img_progress_bar.empty()
            img_status.empty()

    # ── Image error banner ────────────────────────────────────────────────────
    if st.session_state.img_error_msg:
        st.error(f"Image generation failed: {st.session_state.img_error_msg}")
        if st.button("🔄 Retry Images", key="retry_img_btn"):
            st.session_state.img_error_msg = None
            st.rerun()

    # ── Image grid display ────────────────────────────────────────────────────
    if st.session_state.image_results:
        results_shots = st.session_state.image_results.get("shots", [])

        for shot_result in results_shots:
            sn = shot_result["shot_number"]
            sname = shot_result["shot_name"]
            start_path = shot_result.get("start_frame_path")
            end_path   = shot_result.get("end_frame_path")
            start_err  = shot_result.get("start_frame_error")
            end_err    = shot_result.get("end_frame_error")

            st.markdown(f"""
<div class="shot-card" style="margin-bottom:0.4rem">
  <div class="shot-num">Shot {sn}</div>
  <div class="shot-name">{sname}</div>
</div>""", unsafe_allow_html=True)

            col_start, col_end = st.columns(2, gap="small")

            with col_start:
                st.caption("▶ Start Frame")
                if start_path and Path(start_path).exists():
                    st.image(start_path, use_container_width=True)
                elif start_err:
                    st.error(f"Failed: {start_err}")
                else:
                    st.info("Not generated")

            with col_end:
                st.caption("⏹ End Frame")
                if end_path and Path(end_path).exists():
                    st.image(end_path, use_container_width=True)
                elif end_err:
                    st.error(f"Failed: {end_err}")
                else:
                    st.info("Not generated")

            # Per-shot regenerate button
            if st.button(
                f"🔁 Regenerate Shot {sn}",
                key=f"regen_shot_{sn}",
            ):
                active_lora_regen = st.session_state.get("lora_url", "").strip()
                regen_prompts = st.session_state.image_prompts
                matching = [
                    p for p in (regen_prompts or {}).get("prompts", [])
                    if p["shot_number"] == sn
                ]
                if matching:
                    p = matching[0]
                    run_folder_r = Path(st.session_state.run_folder)
                    with st.spinner(f"Regenerating Shot {sn}..."):
                        try:
                            new_start = generate_image(
                                prompt=p["start_frame_prompt"],
                                shot_number=sn,
                                frame_type="start",
                                run_folder=run_folder_r,
                                lora_url=active_lora_regen,
                                image_model_id=IMAGE_MODELS[image_model_choice],
                            )
                            new_end = generate_image(
                                prompt=p["end_frame_prompt"],
                                shot_number=sn,
                                frame_type="end",
                                run_folder=run_folder_r,
                                lora_url=active_lora_regen,
                                image_model_id=IMAGE_MODELS[image_model_choice],
                            )
                            # Update session state
                            for s in st.session_state.image_results["shots"]:
                                if s["shot_number"] == sn:
                                    s["start_frame_path"] = str(new_start)
                                    s["end_frame_path"]   = str(new_end)
                                    s["start_frame_error"] = None
                                    s["end_frame_error"]   = None
                            # Re-save package
                            pkg["image_results"] = st.session_state.image_results
                            st.session_state.content_package = pkg
                            save_content_package(pkg, run_folder_r)
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Regen failed: {exc}")

            st.markdown("<hr style='border-color:rgba(199,91,66,0.1)'>")

    # ═══════════════════════════════════════════════════════════════════════════
    # ── Phase 3: VIDEO GENERATION ─────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════
    if st.session_state.image_results and not st.session_state.img_error_msg:
        st.divider()
        st.markdown(f"## 🎬 Phase 3 — Generate Video Clips")
        st.caption(f"Using model: **{video_model_choice}**")

        results_shots = st.session_state.image_results.get("shots", [])
        total_clips = len(results_shots)

        gen_videos_clicked = st.button(
            "🎬 Generate Video Clips sequentially",
            key="gen_videos_btn",
            use_container_width=False,
        )

        if gen_videos_clicked:
            st.session_state.video_error_msg = None
            st.session_state.final_video_path = None
            run_folder = Path(st.session_state.run_folder)

            video_progress_bar = st.progress(0, text="Starting video generation...")
            video_status = st.empty()

            for idx, shot_result in enumerate(results_shots):
                sn = shot_result["shot_number"]
                sname = shot_result["shot_name"]
                start_path = shot_result.get("start_frame_path")
                end_path = shot_result.get("end_frame_path")
                
                # Fetch original script/shot data for the motion prompt
                original_shot = next((s for s in pkg.get("shots", {}).get("shots", []) if s["shot_number"] == sn), {})
                prompt = original_shot.get("action_description", sname)

                label = f"Clip {idx + 1} of {total_clips} — Shot {sn} ({sname})"
                video_progress_bar.progress(idx / total_clips, text=label)
                video_status.info(f"⏳ Generating: {label}\\n(Takes ~3-5 mins per clip)")

                if not start_path or not Path(start_path).exists():
                    st.session_state.video_error_msg = f"Missing start frame for Shot {sn}. Cannot generate video."
                    break

                try:
                    import time
                    t0 = time.time()
                    clip_path = generate_video_clip(
                        start_frame_path=start_path,
                        end_frame_path=end_path,
                        shot_description=prompt,
                        shot_number=sn,
                        model_id=video_model_id,
                        run_folder=run_folder
                    )
                    t_elapsed = time.time() - t0

                    # Save to state
                    st.session_state.video_clips[sn] = str(clip_path)

                    # Update context json
                    pkg.setdefault("video_results", {})[sn] = str(clip_path)
                    st.session_state.content_package = pkg
                    save_content_package(pkg, run_folder)

                    st.success(f"✅ Finished Shot {sn} in {t_elapsed/60:.1f}m")

                except Exception as exc:
                    st.session_state.video_error_msg = f"Shot {sn} failed: {exc}"
                    break
            
            video_status.empty()
            if not st.session_state.video_error_msg:
                video_progress_bar.progress(1.0, text="✅ All video clips generated!")
            else:
                video_progress_bar.empty()

        if st.session_state.video_error_msg:
            st.error(f"Video Generation Error: {st.session_state.video_error_msg}")
            if st.button("🔄 Resume Videos", key="retry_vid_btn"):
                st.session_state.video_error_msg = None
                st.rerun()

        # Display completed clips
        if st.session_state.video_clips:
            st.markdown("### 🎞 Completed Clips")
            for shot_result in results_shots:
                sn = shot_result["shot_number"]
                if sn in st.session_state.video_clips:
                    clip_path = st.session_state.video_clips[sn]
                    st.markdown(f"**Shot {sn}: {shot_result['shot_name']}**")
                    if Path(clip_path).exists():
                        st.video(clip_path)

            st.divider()
            
            if len(st.session_state.video_clips) == total_clips:
                # Assemble
                st.markdown("### 🎬 Final Assembly")
                assemble_clicked = st.button("Assemble Final Video", key="assemble_btn")
                
                if assemble_clicked:
                    run_folder = Path(st.session_state.run_folder)
                    clip_list = [st.session_state.video_clips[s["shot_number"]] for s in results_shots]
                    try:
                        with st.spinner("Assembling video with FFmpeg..."):
                            final_v = assemble_video(clip_list, run_folder)
                            st.session_state.final_video_path = str(final_v)
                            
                            pkg["final_video"] = str(final_v)
                            st.session_state.content_package = pkg
                            save_content_package(pkg, run_folder)
                    except Exception as exc:
                        st.error(str(exc))

                if st.session_state.final_video_path and Path(st.session_state.final_video_path).exists():
                    st.success("✅ Assembly complete!")
                    final_path = st.session_state.final_video_path
                    st.video(final_path)
                    
                    with open(final_path, "rb") as f:
                        st.download_button(
                            "📥 Download Final Video",
                            data=f,
                            file_name=f"aksha_final_{datetime.now().strftime('%Y%m%d')}.mp4",
                            mime="video/mp4"
                        )


    # ═══════════════════════════════════════════════════════════════════════════
    # ── Phase 4: CAPTIONS & COPY ──────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════════
    if st.session_state.final_video_path and not st.session_state.video_error_msg:
        st.divider()
        st.markdown("## 📝 Phase 4 — Social Media Copy")
        
        gen_caps_clicked = st.button(
            "📝 Generate Captions",
            key="gen_caps_btn",
            disabled=(st.session_state.captions is not None)
        )
        
        rewrite_caps_clicked = st.button("🔄 Rewrite Captions", key="rewrite_caps_btn")
        
        if gen_caps_clicked or rewrite_caps_clicked:
            st.session_state.cap_error_msg = None
            with st.spinner("Claude is writing social copy..."):
                try:
                    caps = write_captions(pkg["recipe"], pkg.get("script", {}), llm_id)
                    st.session_state.captions = caps
                    pkg["captions"] = caps
                    save_content_package(pkg, Path(st.session_state.run_folder))
                except Exception as exc:
                    st.session_state.cap_error_msg = str(exc)
        
        if st.session_state.cap_error_msg:
            st.error(st.session_state.cap_error_msg)
            
        if st.session_state.captions:
            caps = st.session_state.captions
            ig = caps.get("instagram_caption", {})
            fb = caps.get("facebook_post", {})
            tags = caps.get("hashtags", {})
            
            col_ig, col_fb = st.columns(2)
            
            with col_ig:
                st.markdown("### 📸 Instagram")
                st.text_area("Caption Header", value=ig.get("full_caption", ""), height=200, key="ig_box")
                st.code(ig.get("full_caption", ""), language="text")
                
                st.markdown("**Hashtags**")
                niche_html = "".join([f"<span class='hashtag-badge'>{t}</span>" for t in tags.get("niche", [])])
                broad_html = "".join([f"<span class='hashtag-badge broad'>{t}</span>" for t in tags.get("broad", [])])
                life_html = "".join([f"<span class='hashtag-badge lifestyle'>{t}</span>" for t in tags.get("lifestyle", [])])
                st.markdown(f"<div>{niche_html}</div><div style='margin-top:0.3rem'>{broad_html}</div><div style='margin-top:0.3rem'>{life_html}</div>", unsafe_allow_html=True)
                st.code(tags.get("full_hashtag_string", ""), language="text")
                
            with col_fb:
                st.markdown("### 📘 Facebook")
                st.text_area("FB Text", value=fb.get("text", ""), height=200, key="fb_box")
                st.code(fb.get("text", ""), language="text")
