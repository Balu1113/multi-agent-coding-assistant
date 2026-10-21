from __future__ import annotations

import os
import logging
import json
import re
from pathlib import Path
from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

# Try loading .env file for API keys
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

_client: genai.Client | None = None
_client_api_key: str | None = None
_DEFAULT_MODEL = "gemini-3.1-flash-lite"
_CURRENT_MODEL = _DEFAULT_MODEL

# Import usage tracker once
from src.usage_tracker import track as _track_usage, update_rate_limit as _update_ratelimit

AVAILABLE_MODELS = [
    # Gemini free-tier models
    {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite", "group": "⚡ General", "daily_limit": 1500},
    {"id": "gemini-3-flash", "name": "Gemini 3 Flash", "group": "⚡ General", "daily_limit": 500},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "group": "⚡ General", "daily_limit": 1500},
    {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "group": "⚡ General", "daily_limit": 1500},
    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "group": "⚡ General", "daily_limit": 1500},
    {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite", "group": "⚡ General", "daily_limit": 1500},
    {"id": "gemini-2.5-flash-image", "name": "Gemini 2.5 Flash Image", "group": "🎨 Image", "daily_limit": 50},
    {"id": "gemini-3.1-flash-image", "name": "Gemini 3.1 Flash Image", "group": "🎨 Image", "daily_limit": 50},
    {"id": "imagen-4.0-generate-001", "name": "Imagen 4", "group": "🎨 Image (paid)", "daily_limit": 0},
    # Groq free-tier models
    {"id": "groq/meta-llama/llama-4-scout-17b-16e-instruct", "name": "Groq Llama 4 Scout 17B", "group": "💻 Coding", "daily_limit": 14400},
    {"id": "groq/llama-3.3-70b-versatile", "name": "Groq Llama 3.3 70B", "group": "⚡ General", "daily_limit": 14400},
    {"id": "groq/llama-3.1-8b-instant", "name": "Groq Llama 3.1 8B", "group": "⚡ General", "daily_limit": 14400},
    {"id": "groq/qwen/qwen3-32b", "name": "Groq Qwen3 32B", "group": "⚡ General", "daily_limit": 14400},
    {"id": "groq/openai/gpt-oss-120b", "name": "Groq GPT-OSS 120B", "group": "💻 Coding", "daily_limit": 14400},
    {"id": "groq/openai/gpt-oss-20b", "name": "Groq GPT-OSS 20B", "group": "💻 Coding", "daily_limit": 14400},
    # Hugging Face free-tier models
    {"id": "hf/meta-llama/Llama-3.1-8B-Instruct", "name": "HF Llama 3.1 8B", "group": "⚡ General", "daily_limit": 600},
    {"id": "hf/Qwen/Qwen2.5-7B-Instruct", "name": "HF Qwen 2.5 7B", "group": "⚡ General", "daily_limit": 600},
    {"id": "hf/Qwen/Qwen2.5-Coder-7B-Instruct", "name": "HF Qwen 2.5 Coder 7B", "group": "💻 Coding", "daily_limit": 600},
    {"id": "hf/google/gemma-2-9b-it", "name": "HF Gemma 2 9B", "group": "⚡ General", "daily_limit": 600},
    {"id": "hf/mistralai/Mistral-7B-Instruct-v0.3", "name": "HF Mistral 7B v0.3", "group": "⚡ General", "daily_limit": 600},
    {"id": "hf/microsoft/Phi-3.5-mini-instruct", "name": "HF Phi 3.5 Mini", "group": "⚡ General", "daily_limit": 600},
    {"id": "hf/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B", "name": "HF DeepSeek R1 Distill 7B", "group": "🧠 Reasoning", "daily_limit": 600},
    # Hugging Face image models (via Inference Providers)
    {"id": "hf/black-forest-labs/FLUX.1-schnell", "name": "HF FLUX.1 Schnell", "group": "🎨 Image", "daily_limit": 100},
    {"id": "hf/stabilityai/stable-diffusion-xl-base-1.0", "name": "HF SDXL 1.0", "group": "🎨 Image", "daily_limit": 100},
    {"id": "hf/stabilityai/stable-diffusion-3.5-large", "name": "HF SD 3.5 Large", "group": "🎨 Image", "daily_limit": 100},
]


def set_model(model_id: str) -> bool:
    global _CURRENT_MODEL
    if any(m["id"] == model_id for m in AVAILABLE_MODELS):
        _CURRENT_MODEL = model_id
        return True
    return False


def get_model() -> str:
    return _CURRENT_MODEL


def get_available_models() -> list[dict]:
    return AVAILABLE_MODELS.copy()


def _get_client() -> genai.Client:
    global _client, _client_api_key
    api_key = ""
    if env_path.exists():
        try:
            from dotenv import dotenv_values

            api_key = (dotenv_values(env_path).get("GEMINI_API_KEY") or "").strip().strip("\"'")
        except ImportError:
            pass
    if api_key:
        process_key = os.environ.get("GEMINI_API_KEY", "")
        if process_key and process_key != api_key:
            logger.warning("Using GEMINI_API_KEY from the project .env instead of a different inherited value")
    else:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in the project .env or process environment")
    if _client is None or _client_api_key != api_key:
        _client = genai.Client(api_key=api_key)
        _client_api_key = api_key
    return _client


def _get_groq_key() -> str:
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set in .env")
    return key


def _call_groq(prompt: str, system: str, **kwargs: object) -> str:
    """Call Groq via OpenAI-compatible API."""
    import requests
    api_key = _get_groq_key()
    model = kwargs.get("model", "groq/llama-3.1-8b-instant")
    if not isinstance(model, str):
        model = "groq/llama-3.1-8b-instant"
    # Strip groq/ prefix for the API call
    prefix = "groq/"
    api_model = model[len(prefix):] if model.startswith(prefix) else model
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": api_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 8192),
        },
        timeout=60,
    )
    # Capture real rate limit from response headers
    limit = resp.headers.get("x-ratelimit-limit-requests")
    remaining = resp.headers.get("x-ratelimit-remaining-requests")
    if limit and remaining:
        _update_ratelimit(model, int(limit), int(remaining))
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"] or ""


def _call_huggingface(prompt: str, system: str, **kwargs: object) -> str:
    """Call Hugging Face Inference Providers (OpenAI-compatible API)."""
    import requests
    api_key = os.environ.get("HF_API_KEY", "") or os.environ.get("HUGGINGFACE_API_KEY", "")
    model = kwargs.get("model", "hf/meta-llama/Llama-3.1-8B-Instruct")
    if not isinstance(model, str):
        model = "hf/meta-llama/Llama-3.1-8B-Instruct"
    prefix = "hf/"
    api_model = model[len(prefix):] if model.startswith(prefix) else model
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.post(
        "https://router.huggingface.co/v1/chat/completions",
        headers=headers,
        json={
            "model": api_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 4096),
        },
        timeout=120,
    )
    # Capture real rate limit from response headers
    limit = resp.headers.get("x-ratelimit-limit-requests")
    remaining = resp.headers.get("x-ratelimit-remaining-requests")
    if limit and remaining:
        _update_ratelimit(model, int(limit), int(remaining))
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"] or ""


def _call(prompt: str, system: str, **kwargs: object) -> str:
    model = kwargs.get("model", _CURRENT_MODEL)
    if isinstance(model, str) and model.startswith("groq/"):
        result = _call_groq(prompt, system, **kwargs)
        _track_usage(model)
        return result
    if isinstance(model, str) and model.startswith("hf/"):
        result = _call_huggingface(prompt, system, **kwargs)
        _track_usage(model)
        return result
    client = _get_client()
    if not isinstance(model, str):
        model = _CURRENT_MODEL
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=kwargs.get("temperature", 0.2),
            max_output_tokens=kwargs.get("max_tokens", 8192),
        ),
    )
    _track_usage(model)
    return response.text or ""


def _clean_code_block(text: str) -> str:
    lines = text.strip().split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def generate_code_with_llm(prompt: str, language: str = "python", model: str | None = None) -> str:
    system = (
        "You are an expert software engineer solving coding problems. "
        "Given a problem description, write clean, correct, and efficient code. "
        "Include time and space complexity as comments. "
        "Return ONLY the code block -- no preamble, no explanation."
    )
    user = f"Problem (language: {language}):\n\n{prompt}"
    code = _call(user, system, model=model)
    return _clean_code_block(code)


def review_code_with_llm(code: str, prompt: str, model: str | None = None) -> str:
    system = (
        "You are an expert code reviewer. Analyze the code for bugs, "
        "performance issues, style problems, and correctness. "
        "Be concise but thorough."
    )
    user = f"Problem: {prompt}\n\nCode:\n{code}"
    return _call(user, system, model=model)


def generate_tests_with_llm(code: str, prompt: str, model: str | None = None) -> str:
    system = (
        "You are an expert test engineer. Write comprehensive test cases "
        "for the given code. Include edge cases, normal cases, and corner cases. "
        "Use pytest style assertions with Python."
    )
    user = f"Problem: {prompt}\n\nCode:\n{code}"
    return _call(user, system, model=model)


def chat_with_llm(
    message: str,
    history: list | None = None,
    web_context: str = "",
    model: str | None = None,
    workspace_context: str = "",
) -> str:
    system = (
        "You are a helpful, knowledgeable assistant. Answer the user's question "
        "concisely and accurately using the provided web search results if available. "
        "If it's a coding question, provide code. "
        "If it's a general knowledge question, provide a clear, informative answer. "
        "Do not mention that you are a coding assistant unless the user asks about your capabilities."
    )
    ctx = ""
    if history:
        ctx = "Previous conversation:\n" + "\n".join(
            f"User: {h.get('prompt', '')}\nAssistant: {h.get('result', {}).get('message', '')}"
            for h in history[-6:]
        ) + "\n\n"
    workspace = (
        "Open workspace files (partial project context; use only files shown below):\n"
        f"{workspace_context}\n\n"
        if workspace_context else ""
    )
    user = f"{workspace}{ctx}User: {message}"
    if web_context:
        user = f"{web_context}\n\n{user}"
    return _call(user, system, model=model)


def _parse_workspace_response(raw: str) -> dict:
    decoder = json.JSONDecoder()
    for start, character in enumerate(raw):
        if character != "{":
            continue
        try:
            result, _end = decoder.raw_decode(raw[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(result, dict) and result.get("mode") in {"answer", "plan", "tool_call", "changes"}:
            return result
    raise ValueError("The agent returned an invalid workspace change response. Please retry.")


def generate_workspace_response(
    prompt: str,
    inventory: str,
    files: list[dict[str, str]],
    directories: list[str] | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    tool_results: list[dict[str, str]] | None = None,
    approved_requirement: str = "",
    approved_plan: str = "",
    model: str | None = None,
) -> dict:
    """Analyze a workspace request and return an answer, plan, or file changes."""
    system = (
        "You are an expert software engineer working inside an existing project. "
        "Analyze the project inventory and supplied file contents before deciding what to do. "
        "Use conversation_history to understand follow-up messages, references to prior files, and approved plans. "
        "Return exactly one JSON object, without markdown, using this schema: "
        '{"mode":"answer|plan|tool_call|changes","analysis":"...","message":"...",'
        '"requirement":"...","plan":"...","tool_call":{"tool":"search_workspace|read_file|list_directory","query":"...","path":"..."},'
        '"changes":[{"path":"relative/path","action":"write|delete|delete_directory","content":"complete file content or empty for delete"}]}. '
        "For every request that asks to implement a code change, first analyze the project and return mode=plan "
        "with a concise, ordered implementation plan and no file changes. Only include files that need to be "
        "created or fully rewritten in the later implementation; preserve existing project conventions. "
        "Use project_directories to determine which folders exist. If you need to inspect folder contents, return mode=tool_call "
        "with list_directory and its relative path (empty path lists the workspace root). If a file needs closer inspection, "
        "request search_workspace or read_file. Never guess unseen paths or contents. "
        "Use tool_results supplied on the next turn and continue analysis. You may request at most four inspections. "
        "For vague requests to improve or change the project without a concrete requirement, inspect the project, "
        "propose one specific, useful requirement, explain why it fits, include it in mode=plan, and do not include changes. "
        "Do not implement a plan until the user approves it. For questions or requests that do not ask for "
        "implementation, return mode=answer. Never invent file contents for files not supplied unless creating a new file. "
        "Never include paths outside the project, absolute paths, or paths containing '..'. "
        "For removals, return action=delete for the exact existing file path; do not return an empty write. "
        "For a folder removal, return action=delete_directory only for the exact existing directory, and include explicit delete actions for every child file and subdirectory first. "
        "Directory removal is non-recursive; never assume unlisted children can be removed. "
        "For other changes, return action=write with complete file contents, not diffs or snippets. Keep changes focused and do not modify secrets, "
        "generated files, dependency folders, or lockfiles."
    )
    if approved_plan.strip():
        system += (
            " The user explicitly approved this implementation plan: "
            f"{approved_plan.strip()}. Implement the approved plan now and return mode=changes with complete file contents; "
            "do not ask for further approval or return mode=plan."
        )
    context = {
        "user_request": prompt,
        "approved_requirement": approved_requirement,
        "approved_plan": approved_plan,
        "project_inventory": inventory,
        "project_directories": directories or [],
        "project_files": files,
        "conversation_history": (conversation_history or [])[-20:],
        "tool_results": (tool_results or [])[-4:],
    }
    raw = _call(
        json.dumps(context, ensure_ascii=False),
        system,
        model=model,
        temperature=0.2,
        max_tokens=8192,
    ).strip()
    try:
        result = _parse_workspace_response(raw)
    except ValueError:
        repair_context = {
            "original_user_request": prompt,
            "approved_requirement": approved_requirement,
            "approved_plan": approved_plan,
            "unparsed_model_response": raw[:12000],
        }
        repair_system = (
            system + " Return only one valid JSON object matching the required workspace response schema. "
            "Reformat the supplied model response without inventing new requirements or file contents. "
            "If it contains no actionable implementation plan, return mode=answer with a concise explanation."
        )
        try:
            repaired_raw = _call(
                json.dumps(repair_context, ensure_ascii=False),
                repair_system,
                model=model,
                temperature=0,
                max_tokens=8192,
            ).strip()
            result = _parse_workspace_response(repaired_raw)
        except Exception as repair_error:
            raise ValueError(
                "The agent could not return a valid structured response after one format retry. Please retry."
            ) from repair_error
    if not isinstance(result, dict) or result.get("mode") not in {"answer", "plan", "tool_call", "changes"}:
        raise ValueError("The agent response did not include a valid workspace action.")
    if result["mode"] == "tool_call":
        tool_call = result.get("tool_call")
        if not isinstance(tool_call, dict) or tool_call.get("tool") not in {"search_workspace", "read_file", "list_directory"}:
            raise ValueError("The agent requested an unsupported workspace tool.")
        if tool_call["tool"] == "search_workspace":
            query = tool_call.get("query", "")
            if not isinstance(query, str) or not query.strip() or len(query) > 200:
                raise ValueError("The workspace search request was invalid.")
            result["tool_call"] = {"tool": "search_workspace", "query": query.strip()}
        elif tool_call["tool"] == "list_directory":
            path = tool_call.get("path", "")
            if not isinstance(path, str) or len(path) > 500:
                raise ValueError("The workspace directory path was invalid.")
            normalized = path.replace("\\", "/").strip("/")
            parts = normalized.split("/") if normalized else []
            if ":" in normalized or any(part in {".", ".."} for part in parts):
                raise ValueError("The workspace directory path was invalid.")
            result["tool_call"] = {"tool": "list_directory", "path": normalized}
        else:
            path = tool_call.get("path", "")
            if not isinstance(path, str) or not path.strip() or len(path) > 500:
                raise ValueError("The workspace read request was invalid.")
            parts = path.replace("\\", "/").split("/")
            if path.startswith("/") or ":" in path or any(part in {"", ".", ".."} for part in parts):
                raise ValueError("The workspace read path was invalid.")
            result["tool_call"] = {"tool": "read_file", "path": "/".join(parts)}
        result["changes"] = []
        return result

    for key in ("analysis", "message", "requirement", "plan"):
        value = result.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"The agent response contains an invalid {key}.")
        result[key] = value
    changes = result.get("changes", [])
    if not isinstance(changes, list) or len(changes) > 20:
        raise ValueError("The agent returned too many workspace file changes.")
    discarded_unapproved_changes = result["mode"] != "changes" and bool(changes)
    if result["mode"] == "changes" and not approved_plan.strip():
        result["mode"] = "plan"
        discarded_unapproved_changes = bool(changes)
        if not result["plan"].strip():
            steps = [
                f"{index}. {'Remove' if isinstance(change, dict) and change.get('action') == 'delete' else 'Update'} {path}."
                for index, (change, path) in enumerate(
                    ((change, change.get("path")) for change in changes if isinstance(change, dict) and isinstance(change.get("path"), str)),
                    start=1,
                )
            ]
            result["plan"] = "\n".join(steps) or f"1. Analyze and implement: {result['requirement'] or prompt}."
        changes = []
    elif approved_plan.strip() and result["mode"] != "changes":
        raise ValueError("The agent did not implement the approved plan. Please retry.")
    if discarded_unapproved_changes:
        changes = []
    seen_paths: set[str] = set()
    total_chars = 0
    protected_files = {
        "bun.lock", "bun.lockb", "cargo.lock", "composer.lock", "gemfile.lock",
        "go.sum", "package-lock.json", "pipfile.lock", "poetry.lock", "pnpm-lock.yaml",
        "uv.lock", "yarn.lock",
    }
    protected_directories = {
        ".git", ".venv", "venv", "node_modules", "__pycache__", ".next", ".cache",
        ".ssh", ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage", "dist", "build", "target",
    }
    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get("path"), str):
            raise ValueError("The agent returned a malformed file change.")
        action = change.get("action", "write")
        content = change.get("content", "")
        if action not in {"write", "delete", "delete_directory"} or not isinstance(content, str):
            raise ValueError("The agent returned an invalid file action.")
        path = change["path"].replace("\\", "/")
        parts = path.split("/")
        name = parts[-1].lower() if parts else ""
        sensitive_name = (
            name.startswith(".env") or
            re.search(r"(^|[._-])(secret|credentials?|tokens?|private[_-]?key|id_rsa|id_ed25519)([._-]|$)", name, re.I) is not None or
            re.search(r"\.(key|pem|p12|pfx|jks)$", name, re.I) is not None
        )
        if (
            not path or path.startswith("/") or ":" in path or
            any(part in {"", ".", ".."} for part in parts) or
            any(part.lower() in protected_directories for part in parts) or
            name in protected_files or sensitive_name
        ):
            raise ValueError("The agent returned a file path outside the workspace.")
        if path in seen_paths:
            raise ValueError("The agent returned duplicate file changes.")
        seen_paths.add(path)
        change["path"] = path
        change["action"] = action
        change["content"] = content
        if action == "write":
            total_chars += len(content)
    if total_chars > 2_000_000:
        raise ValueError("The requested workspace changes exceed the 2 MB limit.")
    if result["mode"] == "plan" and not result["plan"].strip():
        raise ValueError("The agent returned an empty implementation plan. Please retry.")
    if result["mode"] == "changes" and not changes:
        raise ValueError("The agent did not return any file changes.")
    result["changes"] = changes
    result["discarded_unapproved_changes"] = discarded_unapproved_changes
    return result


def solve_error_with_llm(error_text: str, model: str | None = None) -> str:
    system = (
        "You are an expert debugging assistant. Given an error message and code, "
        "identify the root cause and provide a fix. Be specific and actionable."
    )
    user = f"Error:\n{error_text}"
    return _call(user, system, model=model)


def _generate_image_pollinations(prompt: str) -> dict:
    import requests, urllib.parse
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
        resp = requests.get(url, timeout=60, stream=True)
        if resp.status_code == 200:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            import base64
            b64 = base64.b64encode(resp.content).decode("utf-8")
            return {"success": True, "image_data": b64, "mime_type": content_type, "note": "Generated via Pollinations.ai"}
        return {"success": False, "error": f"Pollinations returned {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": f"Pollinations failed: {e}"}


def _generate_image_huggingface(prompt: str, model_id: str | None = None) -> dict:
    import io, base64
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        return {"success": False, "error": "huggingface_hub not installed"}
    api_key = os.environ.get("HF_API_KEY", "") or os.environ.get("HUGGINGFACE_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "No HF_API_KEY set"}
    client = InferenceClient(api_key=api_key)
    models_to_try = (
        [model_id] if model_id
        else ["black-forest-labs/FLUX.1-schnell", "stabilityai/stable-diffusion-xl-base-1.0", "stabilityai/stable-diffusion-3.5-large"]
    )
    for m in models_to_try:
        try:
            image = client.text_to_image(prompt, model=m)
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            _track_usage(f"hf/{m}")
            return {"success": True, "image_data": b64, "mime_type": "image/png", "note": f"Generated via HF ({m})"}
        except Exception as e:
            continue
    return {"success": False, "error": "All Hugging Face image models failed"}


def _generate_image_svg(prompt: str) -> dict:
    try:
        svg_prompt = (
            "Create a detailed, beautiful SVG illustration of: " + prompt + ". "
            "Requirements:\n"
            "- Use viewBox='0 0 800 600'\n"
            "- Include a rich gradient background (sky/environment)\n"
            "- Use multiple layered shapes with proper proportions\n"
            "- Add shadows, highlights, and gradients for depth\n"
            "- Use a rich, harmonious color palette\n"
            "- Make it detailed and visually impressive\n"
            "Return ONLY the raw <svg> tag with its contents. No markdown, no explanation."
        )
        svg_code = _call(svg_prompt, "You are an expert SVG designer. Return only valid SVG code.", temperature=0.4, max_tokens=4096)
        svg_code = svg_code.strip()
        if svg_code.startswith("```"):
            svg_code = svg_code.split("\n", 1)[-1]
            svg_code = svg_code.rsplit("```", 1)[0]
        svg_code = svg_code.strip()
        if "<svg" in svg_code:
            svg_code = svg_code[svg_code.index("<svg"):]
            if "</svg>" not in svg_code:
                svg_code += "</svg>"
            elif svg_code.rindex("</svg>") + 6 < len(svg_code):
                svg_code = svg_code[:svg_code.rindex("</svg>") + 6]
            import base64
            b64 = base64.b64encode(svg_code.encode("utf-8")).decode("utf-8")
            return {"success": True, "image_data": b64, "mime_type": "image/svg+xml", "note": "SVG vector illustration"}
        return {"success": False, "error": "SVG generation produced invalid output"}
    except Exception as e:
        return {"success": False, "error": f"SVG fallback failed: {e}"}


def generate_image_with_llm(prompt: str, model: str | None = None) -> dict:
    import base64

    # Strategy 1: Gemini Imagen (paid plan)
    if not model or "imagen" in model:
        try:
            client = _get_client()
            for img_model in ("imagen-4.0-generate-001", "imagen-4.0-fast-generate-001"):
                try:
                    response = client.models.generate_images(
                        model=img_model,
                        prompt=prompt,
                        config=genai_types.GenerateImagesConfig(number_of_images=1, aspect_ratio="1:1"),
                    )
                    if response.generated_images:
                        img = response.generated_images[0]
                        if img.image and img.image.image_bytes:
                            b64 = base64.b64encode(img.image.image_bytes).decode("utf-8")
                            _track_usage(img_model)
                            return {"success": True, "image_data": b64, "mime_type": "image/png"}
                except Exception:
                    continue
        except Exception:
            pass

    # Strategy 2: Gemini Image model via generate_content (free tier)
    if not model or model.startswith("gemini"):
        try:
            client = _get_client()
            gemini_image_models = ["gemini-2.5-flash-image", "gemini-3.1-flash-image", "gemini-3.1-flash-image-preview"]
            if model and model.startswith("gemini"):
                gemini_image_models.insert(0, model)
            for gm in gemini_image_models:
                try:
                    response = client.models.generate_content(
                        model=gm,
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(response_modalities=["Image"]),
                    )
                    for part in response.candidates[0].content.parts:
                        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                            _track_usage(gm)
                            b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                            return {"success": True, "image_data": b64, "mime_type": part.inline_data.mime_type}
                        if part.text and "<svg" in part.text:
                            _track_usage(gm)
                            svg_text = part.text
                            svg_text = svg_text[svg_text.index("<svg"):]
                            if "</svg>" in svg_text:
                                svg_text = svg_text[:svg_text.index("</svg>") + 6]
                            b64 = base64.b64encode(svg_text.encode("utf-8")).decode("utf-8")
                            return {"success": True, "image_data": b64, "mime_type": "image/svg+xml", "note": "Gemini returned SVG text"}
                except Exception:
                    continue
        except Exception:
            pass

    # Strategy 3: Hugging Face via Inference Providers (only if model is HF image)
    if model and model.startswith("hf/") and model.count("/") == 2:
        hf_model_id = model[len("hf/"):]
        result = _generate_image_huggingface(prompt, model_id=hf_model_id)
        if result["success"]:
            return result

    # Strategy 4: Pollinations.ai (free, no key)
    try:
        result = _generate_image_pollinations(prompt)
        if result["success"]:
            return result
    except Exception:
        pass

    # Strategy 5: Hugging Face (generic fallback)
    try:
        result = _generate_image_huggingface(prompt)
        if result["success"]:
            return result
    except Exception:
        pass

    # Strategy 6: SVG via text LLM
    try:
        result = _generate_image_svg(prompt)
        if result["success"]:
            return result
    except Exception:
        pass

    return {"success": False, "error": "All image generation methods failed. Try again later."}
