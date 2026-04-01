import re

# 1. Patch agent.py
with open("agent.py", "r", encoding="utf-8") as f:
    at = f.read()

# Replace imports
at = at.replace("import anthropic", "import anthropic\nfrom llm_adapter import get_llm_response, run_openai_agent")

# Replace individual tools logic
at = re.sub(
    r"""    client = anthropic.Anthropic\(\)\n\n    prompt = f\"\"\"Create a detailed recipe JSON(.*?)    message = client\.messages\.create\(.*?\)\n\n    raw = message\.content\[0\]\.text\.strip\(\)""",
    r"""    prompt = f\"\"\"Create a detailed recipe JSON\1    raw = get_llm_response(prompt, AKSHA_SYSTEM_PROMPT, MAX_TOKENS, llm_id=kwargs.get('llm_id', CLAUDE_MODEL)).strip()""",
    at, flags=re.DOTALL
)

at = re.sub(
    r"""    client = anthropic.Anthropic\(\)\n\n    prompt = f\"\"\"Based on this recipe, write(.*?)    message = client\.messages\.create\(.*?\)\n\n    raw = message\.content\[0\]\.text\.strip\(\)""",
    r"""    prompt = f\"\"\"Based on this recipe, write\1    raw = get_llm_response(prompt, AKSHA_SYSTEM_PROMPT, MAX_TOKENS, llm_id=kwargs.get('llm_id', CLAUDE_MODEL)).strip()""",
    at, flags=re.DOTALL
)

at = re.sub(
    r"""    client = anthropic.Anthropic\(\)\n\n    prompt = f\"\"\"Based on this video script, create(.*?)    message = client\.messages\.create\(.*?\)\n\n    raw = message\.content\[0\]\.text\.strip\(\)""",
    r"""    prompt = f\"\"\"Based on this video script, create\1    raw = get_llm_response(prompt, AKSHA_SYSTEM_PROMPT, MAX_TOKENS, llm_id=kwargs.get('llm_id', CLAUDE_MODEL)).strip()""",
    at, flags=re.DOTALL
)

# Replace signatures
at = at.replace("def plan_recipe(dish_name: str) -> dict:", "def plan_recipe(dish_name: str, **kwargs) -> dict:")
at = at.replace("def write_script(recipe_json: dict) -> dict:", "def write_script(recipe_json: dict, **kwargs) -> dict:")
at = at.replace("def plan_shots(script_json: dict) -> dict:", "def plan_shots(script_json: dict, **kwargs) -> dict:")

# Replace master loop
runagent_old = """def run_agent(user_prompt: str, status_callback=None) -> dict:"""
runagent_new = """def run_agent(user_prompt: str, status_callback=None, llm_id: str = None) -> dict:\n    if llm_id is None: llm_id = CLAUDE_MODEL\n    if not llm_id.startswith("claude"):\n        return run_openai_agent(user_prompt, llm_id, AKSHA_SYSTEM_PROMPT, TOOL_DEFINITIONS, MAX_TOKENS, status_callback, TOOL_REGISTRY)"""
at = at.replace(runagent_old, runagent_new)

# Update registry calls within Anthropic master loop to pass llm_id
at = at.replace("""result = fn(**tool_input)""", """result = fn(**tool_input, llm_id=llm_id)""")

with open("agent.py", "w", encoding="utf-8") as f:
    f.write(at)

# 2. Patch caption_tools.py
with open("caption_tools.py", "r", encoding="utf-8") as f:
    ct = f.read()

ct = ct.replace("import anthropic", "import anthropic\nfrom llm_adapter import get_llm_response")
ct = ct.replace("def write_captions(recipe_json: dict, script_json: dict) -> dict:", "def write_captions(recipe_json: dict, script_json: dict, llm_id: str) -> dict:")

ct_call_old = """    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=AKSHA_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()"""
ct_call_new = """    raw = get_llm_response(prompt, AKSHA_SYSTEM_PROMPT, MAX_TOKENS, llm_id).strip()"""
ct = ct.replace(ct_call_old, ct_call_new)
ct = ct.replace("    client = anthropic.Anthropic()\n", "")

with open("caption_tools.py", "w", encoding="utf-8") as f:
    f.write(ct)

# 3. Patch app.py (adding UI and plumbing llm_id)
with open("app.py", "r", encoding="utf-8") as f:
    ap = f.read()

ap = ap.replace("from config import OUTPUT_DIR, REPLICATE_LORA_URL, IMAGE_MODELS", "from config import OUTPUT_DIR, REPLICATE_LORA_URL, IMAGE_MODELS, LLM_MODELS")
ap = ap.replace(
'''# ── Sidebar — LoRA config ─────────────────────────────────────────────────────
with st.sidebar:''', 
'''# ── Sidebar — LoRA config ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧠 Master AI Agent")
    llm_choice_key = st.selectbox(
        "LLM Model",
        options=list(LLM_MODELS.keys()),
        index=0,
        help="Select the LLM brain to power the agent."
    )
    llm_id = LLM_MODELS[llm_choice_key]
    st.divider()'''
)

ap = ap.replace(
'''    elif not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_anthropic_api_key_here":
        st.error("⚠️ ANTHROPIC_API_KEY is not set. Please add it to your `.env` file.")''',
'''    elif llm_id.startswith("claude") and (not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_anthropic_api_key_here"):
        st.error("⚠️ ANTHROPIC_API_KEY is not set. Please add it to your `.env` file.")
    elif not llm_id.startswith("claude") and (not os.getenv("SAMBANOVA_API_KEY") or os.getenv("SAMBANOVA_API_KEY") == "your_sambanova_api_key_here"):
        st.error("⚠️ SAMBANOVA_API_KEY is not set. Please add it to your `.env` file.")'''
)

# Find where run_agent is called
ap = ap.replace('package = run_agent(user_prompt.strip(), status_callback=update_status)', 'package = run_agent(user_prompt.strip(), status_callback=update_status, llm_id=llm_id)')

# Phase 4 automation
ap = ap.replace('caps = write_captions(package["recipe"], package.get("script", {}))', 'caps = write_captions(package["recipe"], package.get("script", {}), llm_id)')

# Phase 4 manual button
ap = ap.replace('caps = write_captions(pkg["recipe"], pkg.get("script", {}))', 'caps = write_captions(pkg["recipe"], pkg.get("script", {}), llm_id)')

with open("app.py", "w", encoding="utf-8") as f:
    f.write(ap)

print("Patching complete.")
