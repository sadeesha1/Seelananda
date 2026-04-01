import re
import os

with open('app.py', 'r', encoding='utf-8') as f:
    app_text = f.read()

# 1. Imports
app_text = app_text.replace(
    "from video_tools import assemble_video, check_ffmpeg_installed, generate_video_clip",
    "from video_tools import assemble_video, check_ffmpeg_installed, generate_video_clip\nfrom caption_tools import write_captions"
)

# 2. Page Config
app_text = app_text.replace(
    'page_title="Aksha Content Agent",\n    page_icon="🍰"',
    'page_title="Aksha Studio",\n    page_icon="🍳"'
)

# 3. CSS Theme (Terracotta + Cream)
old_css = '''  /* Dark background */
  .stApp {
    background: linear-gradient(135deg, #0f0c1a 0%, #1a0f2e 50%, #0f1a2e 100%);
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
    background: linear-gradient(135deg, #ff6eb4, #ff9a6c, #ffd166);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    line-height: 1.2;
  }
  .hero-sub {
    color: #a78bca;
    font-size: 1rem;
    font-weight: 300;
    margin-top: 0.5rem;
    letter-spacing: 0.05em;
  }

  /* Input area */
  .stTextInput > div > div > input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,110,180,0.3) !important;
    border-radius: 12px !important;
    color: #f0e6ff !important;
    font-size: 1.05rem !important;
    padding: 0.85rem 1.2rem !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #ff6eb4 !important;
    box-shadow: 0 0 0 2px rgba(255,110,180,0.2) !important;
  }
  .stTextInput > div > div > input::placeholder {
    color: #6b5f8a !important;
  }

  /* Generate button */
  .stButton > button {
    background: linear-gradient(135deg, #ff6eb4, #d946a6) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.75rem 2.5rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 20px rgba(255,110,180,0.35) !important;
    width: 100% !important;
  }
  .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(255,110,180,0.5) !important;
  }

  /* Expander styling */
  .streamlit-expanderHeader {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,110,180,0.2) !important;
    border-radius: 10px !important;
    color: #f0e6ff !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
  }
  .streamlit-expanderContent {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,110,180,0.1) !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
  }'''

new_css = '''  /* Cream background */
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
  }'''
app_text = app_text.replace(old_css, new_css)

# Update other text colors in css
app_text = app_text.replace('color: #ff6eb4', 'color: #c75b42')
app_text = app_text.replace('color: #ffd166', 'color: #b57a40')
app_text = app_text.replace('color: #d4c5f0', 'color: #5c4f44')
app_text = app_text.replace('color: #ff9ad8', 'color: #c75b42')
app_text = app_text.replace('color: #7b6e9c', 'color: #8c7a6b')
app_text = app_text.replace('background: rgba(255,255,255,0.05)', 'background: #ffffff')
app_text = app_text.replace('background: rgba(255,255,255,0.04)', 'background: #ffffff')
app_text = app_text.replace('rgba(255,110,180', 'rgba(199,91,66')

# 4. Header & Stats Row
header_stats = '''
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
  <h1 class="hero-title">Aksha Studio</h1>
  <div class="hero-sub">AI Workflow Console</div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
col1.metric("Total Runs", tot_runs)
col2.metric("Total Videos", tot_vids)
col3.metric("Last Run", last_run)
st.divider()
'''

app_text = app_text.replace(
'''st.markdown("""
<div class="hero-header">
  <h1 class="hero-title">Aksha Content Agent</h1>
  <div class="hero-sub">Enter a one-line prompt. Let Claude do the rest.</div>
</div>
""", unsafe_allow_html=True)''', header_stats)

# 5. Sidebar Run History
sidebar_history = '''
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
                st.markdown(f"**{dname}**\\n*{fmt_rtime}*")
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
'''
app_text = app_text.replace(
    'st.caption("1080 × 1920 · 28 steps · LoRA scale 0.85")',
    'st.caption("1080 × 1920 · 28 steps · LoRA scale 0.85")' + sidebar_history
)

# 6. Session States for Captions
caption_state = '''
# Phase 4 captions state
if "captions" not in st.session_state:
    st.session_state.captions = None
if "cap_error_msg" not in st.session_state:
    st.session_state.cap_error_msg = None
'''
app_text = app_text.replace(
    'if "final_video_path" not in st.session_state:\n    st.session_state.final_video_path = None',
    'if "final_video_path" not in st.session_state:\n    st.session_state.final_video_path = None' + caption_state
)

# Also clear captions state on new gen
app_text = app_text.replace(
    'st.session_state.final_video_path = None\n            status_placeholder.empty()',
    'st.session_state.final_video_path = None\n            st.session_state.captions = None\n            st.session_state.cap_error_msg = None\n            status_placeholder.empty()'
)

# 7. Generate Everything logic
gen_everything = '''
col_prompt, col_btn1, col_btn2 = st.columns([5, 1, 2], vertical_alignment="bottom")

with col_prompt:
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

if generate_clicked or full_run_clicked:
'''
app_text = re.sub(r'col_prompt, col_btn = .*?if generate_clicked:', gen_everything, app_text, flags=re.DOTALL)

# Handle full_run_clicked injection
if_gen_logic = """
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

        except anthropic.APIStatusError as exc:
"""
after_gen_logic = """
            if full_run_clicked and not st.session_state.last_error_msg:
                # Automate phase 2
                active_lora = st.session_state.get("lora_url", "").strip()
                if active_lora:
                    status_placeholder.markdown('<div class="status-box">⏳ Generating Images...</div>', unsafe_allow_html=True)
                    try:
                        prompts = build_image_prompts(package["shots"], lora_url=active_lora)
                        st.session_state.image_prompts = prompts
                        st.session_state.image_results = generate_all_images(prompts, folder, active_lora)
                        package.update({"image_prompts": prompts, "image_results": st.session_state.image_results})
                        save_content_package(package, folder)
                    except Exception as e:
                        st.session_state.img_error_msg = str(e)

                # Automate phase 3
                if st.session_state.image_results and not st.session_state.img_error_msg:
                    status_placeholder.markdown('<div class="status-box">⏳ Generating Videos (This will take a while)...</div>', unsafe_allow_html=True)
                    try:
                        results_shots = st.session_state.image_results.get("shots", [])
                        clip_list = []
                        for s in results_shots:
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
                        caps = write_captions(package["recipe"], package.get("script", {}))
                        st.session_state.captions = caps
                        package["captions"] = caps
                        save_content_package(package, folder)
                    except Exception as e:
                        st.session_state.cap_error_msg = str(e)
                
                status_placeholder.empty()
                st.rerun()

        except anthropic.APIStatusError as exc:
"""
app_text = app_text.replace(if_gen_logic, if_gen_logic.replace("        except anthropic.APIStatusError as exc:", after_gen_logic))

# 8. Add Phase 4 Captions UI block at the end
captions_ui = '''
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
                    caps = write_captions(pkg["recipe"], pkg.get("script", {}))
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
'''
app_text = app_text + captions_ui

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_text)
