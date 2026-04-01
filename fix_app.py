import re

with open('app.py', 'r', encoding='utf-8') as f:
    app_text = f.read()

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
  <p class="hero-title">Aksha Studio</p>
  <p class="hero-sub">AI Workflow Console</p>
</div>
""", unsafe_allow_html=True)

colH1, colH2, colH3 = st.columns(3)
colH1.metric("Total Runs", tot_runs)
colH2.metric("Total Videos", tot_vids)
colH3.metric("Last Run", last_run)
st.divider()
'''

# Replace the wrong header with the new one we tried to inject
wrong_header = '''# ── Hero header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
  <p class="hero-title">✨ Aksha Content Agent</p>
  <p class="hero-sub">One sentence in → full content package out</p>
</div>
""", unsafe_allow_html=True)

st.divider()'''

app_text = app_text.replace(wrong_header, header_stats)

# And now it's defined BEFORE line 318 where `all_runs` is used, because hero header is line 262 and sidebar is line 288.

# Wait, `get_run_stats` uses OUTPUT_DIR. Is `OUTPUT_DIR` imported? Yes at line 16.
# Let's save.

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_text)
