import os

adapter_code = '''import os
import json
import anthropic

try:
    import openai
except ImportError:
    pass

from config import CLAUDE_MODEL

def get_llm_response(prompt: str, system_prompt: str, max_tokens: int, llm_id: str) -> str:
    """Wrapper to call either Anthropic or OpenAI-style (Sambanova) for text generation."""
    if llm_id.startswith("claude"):
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=llm_id,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            system=system_prompt
        )
        return resp.content[0].text
    else:
        client = openai.OpenAI(
            api_key=os.environ.get("SAMBANOVA_API_KEY"),
            base_url="https://api.sambanova.ai/v1"
        )
        resp = client.chat.completions.create(
            model=llm_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content

def run_openai_agent(user_prompt: str, llm_id: str, system_prompt: str, tools: list, max_tokens: int, status_callback, registry: dict) -> dict:
    import json
    client = openai.OpenAI(
        api_key=os.environ.get("SAMBANOVA_API_KEY"),
        base_url="https://api.sambanova.ai/v1"
    )

    def _status(msg: str):
        if status_callback:
            status_callback(msg)

    # Convert Anthropic tools back to OpenAI
    openai_tools = []
    for t in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"]
            }
        })
        
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{user_prompt}\\n\\nPlease create a complete content package for Aksha by calling plan_recipe, then write_script, then plan_shots — in that order."}
    ]

    collected = {"recipe": None, "script": None, "shots": None}

    while True:
        try:
            response = client.chat.completions.create(
                model=llm_id,
                messages=messages,
                tools=openai_tools,
                max_tokens=max_tokens
            )
        except Exception as e:
            raise RuntimeError(f"Sambanova API Error: {str(e)}")

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            break

        for tcall in msg.tool_calls:
            try:
                args = json.loads(tcall.function.arguments)
            except:
                args = {}
            name = tcall.function.name
            
            status_map = {
                "plan_recipe": "🥘 Planning recipe...",
                "write_script": "📝 Writing video script...",
                "plan_shots": "🎬 Planning shot list...",
            }
            _status(status_map.get(name, f"Running {name}..."))

            # Execute
            fn = registry.get(name)
            if fn:
                # pass llm_id to tools so they use the correct model
                result = fn(**args, llm_id=llm_id)
            else:
                result = {"error": f"Unknown tool {name}"}

            if name == "plan_recipe":
                collected["recipe"] = result
            elif name == "write_script":
                collected["script"] = result
            elif name == "plan_shots":
                collected["shots"] = result

            messages.append({
                "role": "tool",
                "tool_call_id": tcall.id,
                "name": name,
                "content": json.dumps(result)
            })

    _status("✅ Content package complete!")
    return {
        "user_prompt": user_prompt,
        "recipe": collected["recipe"],
        "script": collected["script"],
        "shots": collected["shots"],
    }
'''

with open("llm_adapter.py", "w", encoding="utf-8") as f:
    f.write(adapter_code)
