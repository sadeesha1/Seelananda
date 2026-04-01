import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

try:
    from sambanova import SambaNova
    SAMBANOVA_AVAILABLE = True
except ImportError:
    SAMBANOVA_AVAILABLE = False

try:
    from openai import PermissionDeniedError as _OAIPermissionDeniedError
    from openai import AuthenticationError as _OAIAuthenticationError
except ImportError:
    _OAIPermissionDeniedError = None
    _OAIAuthenticationError = None

def get_llm_response(prompt: str, system_prompt: str, max_tokens: int, llm_id: str) -> str:
    """Wrapper to call either Anthropic or SambaNova for text generation."""
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
        if not SAMBANOVA_AVAILABLE:
            raise ImportError("sambanova package not found. Run 'pip install sambanova'.")
        
        client = SambaNova(
            api_key=os.environ.get("SAMBANOVA_API_KEY"),
            # base_url="https://api.sambanova.ai/v1" # SDK handles this usually or defaults to it
        )
        resp = client.chat.completions.create(
            model=llm_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.1,
            top_p=0.1
        )
        return resp.choices[0].message.content

def run_openai_agent(user_prompt: str, llm_id: str, system_prompt: str, tools: list, max_tokens: int, status_callback, registry: dict) -> dict:
    """Agentic loop using SambaNova SDK."""
    if not SAMBANOVA_AVAILABLE:
        raise ImportError("sambanova package not found. Run 'pip install sambanova'.")

    client = SambaNova(
        api_key=os.environ.get("SAMBANOVA_API_KEY"),
    )

    def _status(msg: str):
        if status_callback:
            status_callback(msg)

    # Convert Anthropic tools format to OpenAI-style expected by SambaNova
    # Note: official SDK might actually expect the tool definitions in a specific way.
    # Typically tool_calling is same as OpenAI format.
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
        {"role": "user", "content": f"{user_prompt}\n\nPlease create a complete content package for Aksha by calling plan_recipe, then write_script, then plan_shots — in that order."}
    ]

    collected = {"recipe": None, "script": None, "shots": None}

    while True:
        try:
            response = client.chat.completions.create(
                model=llm_id,
                messages=messages,
                tools=openai_tools,
                max_tokens=max_tokens,
                temperature=0.1 # recommended by user
            )
        except Exception as e:
            if _OAIPermissionDeniedError and isinstance(e, _OAIPermissionDeniedError):
                raise RuntimeError(
                    "SambaNova account suspended or deactivated. "
                    "Contact help@sambanovasystems.com to restore access, "
                    "or switch to Claude in the sidebar."
                )
            if _OAIAuthenticationError and isinstance(e, _OAIAuthenticationError):
                raise RuntimeError(
                    "SambaNova API key is invalid or expired. "
                    "Check your SAMBANOVA_API_KEY in .env."
                )
            raise RuntimeError(f"SambaNova API Error: {str(e)}")

        msg = response.choices[0].message
        
        # We need to append the message to the history.
        # But for OpenAI/SambaNova we append the Assistant object or dict.
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
