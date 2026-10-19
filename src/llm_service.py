from __future__ import annotations

import os
import logging
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
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=api_key)
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


def chat_with_llm(message: str, history: list | None = None, web_context: str = "", model: str | None = None) -> str:
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
    user = f"{ctx}User: {message}"
    if web_context:
        user = f"{web_context}\n\n{user}"
    return _call(user, system, model=model)


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
