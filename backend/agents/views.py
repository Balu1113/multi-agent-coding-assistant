import os
import re
import sys
import time
import logging
import asyncio
import threading
from pathlib import Path

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.serializers import (
    WorkflowInputSerializer,
    ChatInputSerializer,
    DebugInputSerializer,
    LanguagesOutputSerializer,
    FileUploadSerializer,
    ImageInputSerializer,
)

logger = logging.getLogger(__name__)

# --- Global orchestrator with background event loop ---
_orchestrator = None
_loop = None
_loop_thread = None


def _start_loop():
    """Run the asyncio event loop forever in a daemon thread."""
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


def _ensure_orchestrator():
    global _orchestrator, _loop, _loop_thread

    if _orchestrator is not None:
        return _orchestrator

    from src.communication.message_queue import MessageQueue
    from src.agents.orchestrator import AgentOrchestrator

    # Start background event loop thread
    if _loop_thread is None or not _loop_thread.is_alive():
        _loop_thread = threading.Thread(target=_start_loop, daemon=True)
        _loop_thread.start()
        # Wait for loop to be set
        while _loop is None:
            time.sleep(0.01)

    mq = MessageQueue()
    future = asyncio.run_coroutine_threadsafe(
        AgentOrchestrator(mq).__aenter__(), _loop
    )
    _orchestrator = future.result(timeout=10)
    logger.info("Orchestrator initialized with %d agents", len(_orchestrator.agents))
    return _orchestrator


class LanguagesView(APIView):
    def get(self, request: Request):
        data = {
            "languages": [
                {"name": "python", "aliases": ["python", "py", "python3"]},
                {"name": "javascript", "aliases": ["javascript", "js", "node", "nodejs"]},
                {"name": "typescript", "aliases": ["typescript", "ts"]},
                {"name": "java", "aliases": ["java"]},
                {"name": "cpp", "aliases": ["cpp", "c++", "c"]},
                {"name": "go", "aliases": ["go", "golang"]},
                {"name": "rust", "aliases": ["rust", "rs"]},
                {"name": "ruby", "aliases": ["ruby", "rb"]},
                {"name": "php", "aliases": ["php"]},
                {"name": "swift", "aliases": ["swift"]},
                {"name": "kotlin", "aliases": ["kotlin", "kt"]},
                {"name": "scala", "aliases": ["scala"]},
                {"name": "r", "aliases": ["r"]},
                {"name": "sql", "aliases": ["sql"]},
            ]
        }
        serializer = LanguagesOutputSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(data)


class ModelsView(APIView):
    def get(self, request: Request):
        from src.llm_service import get_available_models, get_model

        return Response({
            "models": get_available_models(),
            "current": get_model(),
        })


class HealthView(APIView):
    def get(self, request: Request):
        try:
            orch = _ensure_orchestrator()
            count = len(orch.agents) if orch.agents else 0
        except Exception as exc:
            count = 0
            logger.warning("Health check: orchestrator not available: %s", exc)

        return Response({
            "status": "ok",
            "agents_running": count,
        })


class WorkflowView(APIView):
    def post(self, request: Request):
        serializer = WorkflowInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        prompt = serializer.validated_data["prompt"]
        history = serializer.validated_data.get("history", [])
        model = serializer.validated_data.get("model", "")
        agents = serializer.validated_data.get("agents", [])
        service = serializer.validated_data.get("service", "")
        plan = serializer.validated_data.get("plan", "")
        execute_plan = serializer.validated_data.get("execute_plan", False)
        plan_approved = serializer.validated_data.get("plan_approved", False)
        research_mode = serializer.validated_data.get("research_mode", False)
        start = time.perf_counter()

        if model:
            from src.llm_service import set_model

            set_model(model)

        try:
            orch = _ensure_orchestrator()
            future = asyncio.run_coroutine_threadsafe(
                orch.process_request(
                    prompt,
                    history,
                    agents=agents,
                    service=service,
                    plan=plan,
                    execute_plan=execute_plan,
                    plan_approved=plan_approved,
                    research_mode=research_mode,
                ),
                _loop,
            )
            result = future.result(timeout=120)
            duration = time.perf_counter() - start

            if "error" in result:
                return Response({
                    "success": False,
                    "error": result["error"],
                    "duration": duration,
                })

            return Response({
                "success": True,
                "type": result.get("type", "code"),
                "code": result.get("code", ""),
                "review": result.get("review", ""),
                "tests": result.get("tests", ""),
                "research": result.get("research", ""),
                "plan": result.get("plan", ""),
                "requires_approval": result.get("requires_approval", False),
                "duration": duration,
            })

        except Exception as exc:
            logger.exception("Workflow failed")
            duration = time.perf_counter() - start
            return Response({
                "success": False,
                "error": str(exc),
                "duration": duration,
            }, status=500)


def _chat_reply(message: str) -> str | None:
    """Return a canned reply if pattern matches, else None (caller should use LLM)."""
    msg = message.lower().strip()
    if msg in ("hello", "hi", "hey", "heya", "howdy", "sup", "yo"):
        return "Hello! I'm the multi-agent coding assistant. I can write, review, and test code for you. What would you like me to help with?"
    if msg in ("bye", "goodbye", "cya", "see you", "see ya", "later"):
        return "Goodbye! Come back anytime you need help with code."
    if msg in ("thanks", "thank you", "ty", "thx"):
        return "You're welcome! Happy to help. Let me know if you need anything else."
    if any(msg.startswith(w) for w in ("who", "what are you", "tell me about yourself")):
        return (
            "I'm a multi-agent coding assistant with a **Coder** agent that writes, reviews, and tests code.\n\n"
            "I can handle algorithms, data structures, and general programming tasks. Just ask!"
        )
    if any(w in msg for w in ("what can you do", "help", "capabilities", "features")):
        return (
            "I can help with:\n\n"
            "- 💻 **Code generation** — \"write a function to find the longest palindrome\"\n"
            "- 🔍 **Code review** — I'll review generated code for bugs and style\n"
            "- 🧪 **Tests** — I'll generate test cases for the code\n\n"
            "My Coder agent does all three — write, review, and test — in sequence. Just ask!"
        )
    if any(w in msg for w in ("how are you", "how's it going", "how do you feel")):
        return "I'm running smoothly! All agents are online and ready. How can I assist you with coding today?"
    if any(w in msg for w in ("python", "javascript", "typescript", "rust", "go", "java", "c++", "c#")):
        return (
            f"I see you're interested in **{message.strip()}**! "
            "My Coder agent can write code, review it, and generate tests in that language. What would you like me to create?"
        )
    return None  # use LLM


class ChatView(APIView):
    def post(self, request: Request):
        serializer = ChatInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        message = serializer.validated_data["message"]
        history = serializer.validated_data.get("history", [])
        model = serializer.validated_data.get("model", "")
        web_search = serializer.validated_data.get("web_search", True)
        reply = _chat_reply(message)

        if reply is not None:
            return Response({
                "type": "chat",
                "message": reply,
            })

        try:
            from src.llm_service import chat_with_llm, set_model
            from src.web_search import search_web, format_search_results

            if model:
                set_model(model)

            web_context = ""
            if web_search:
                results = search_web(message, max_results=5)
                web_context = format_search_results(results)

            llm_reply = chat_with_llm(message, history, web_context=web_context, model=model or None)
            return Response({
                "type": "chat",
                "message": llm_reply,
            })

        except Exception as exc:
            logger.warning("LLM chat failed, falling back: %s", exc)
            try:
                from src.web_search import search_web, format_search_results

                results = search_web(message, max_results=5)
                if results:
                    fallback = "I couldn't generate a full response, but here's what I found from the web:\n\n"
                    fallback += format_search_results(results)
                    return Response({
                        "type": "chat",
                        "message": fallback,
                    })
            except Exception:
                pass

            return Response({
                "type": "chat",
                "message": (
                    f"I understand you said: \"{message.strip()}\". "
                    "I'm a coding assistant — I can write, review, and test code for you. "
                    "Try something like \"write a function to reverse a linked list\" or \"create a sorting algorithm\"."
                ),
            })


_ERROR_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"SyntaxError", re.I), "SyntaxError"),
    (re.compile(r"IndentationError", re.I), "IndentationError"),
    (re.compile(r"TabError", re.I), "TabError"),
    (re.compile(r"TypeError", re.I), "TypeError"),
    (re.compile(r"ValueError", re.I), "ValueError"),
    (re.compile(r"NameError", re.I), "NameError"),
    (re.compile(r"IndexError", re.I), "IndexError"),
    (re.compile(r"KeyError", re.I), "KeyError"),
    (re.compile(r"AttributeError", re.I), "AttributeError"),
    (re.compile(r"ImportError|ModuleNotFoundError", re.I), "ImportError"),
    (re.compile(r"FileNotFoundError", re.I), "FileNotFoundError"),
    (re.compile(r"ZeroDivisionError", re.I), "ZeroDivisionError"),
    (re.compile(r"StopIteration", re.I), "StopIteration"),
    (re.compile(r"RuntimeError", re.I), "RuntimeError"),
    (re.compile(r"RecursionError", re.I), "RecursionError"),
    (re.compile(r"PermissionError", re.I), "PermissionError"),
    (re.compile(r"ConnectionError|ConnectionRefused|ConnectionReset", re.I), "ConnectionError"),
    (re.compile(r"TimeoutError", re.I), "TimeoutError"),
    (re.compile(r"AssertionError", re.I), "AssertionError"),
    (re.compile(r"OverflowError", re.I), "OverflowError"),
    (re.compile(r"MemoryError", re.I), "MemoryError"),
    (re.compile(r"EOFError", re.I), "EOFError"),
    (re.compile(r"OSError|IOError", re.I), "OSError"),
    (re.compile(r"looks like you didn't match", re.I), "RegexMatchError"),
    (re.compile(r"(undefined|is not defined)", re.I), "NameError"),
    (re.compile(r"(out of range|cannot access local)", re.I), "IndexError"),
    (re.compile(r"(expected|unexpected token|missing\))", re.I), "SyntaxError"),
]


def _solve_error(error_text: str) -> dict:
    error_text_stripped = error_text.strip()
    error_type = "UnknownError"

    for pattern, etype in _ERROR_PATTERNS:
        if pattern.search(error_text_stripped):
            error_type = etype
            break

    lower = error_text_stripped.lower()

    from src.code_gen import generate_code

    known_problems = {
        "two sum": "two sum",
        "threesum": "three sum",
        "4sum": "four sum",
        "foursum": "four sum",
        "max profit": "stock max profit",
        "stock max profit": "stock max profit",
        "fibonacci": "fibonacci",
        "binary search": "binary search",
        "quick sort": "quicksort",
        "quicksort": "quicksort",
        "merge sort": "mergesort",
        "fizzbuzz": "fizzbuzz",
        "palindrome": "palindrome",
        "reverse linked": "reverse linked list",
        "tree traversal": "tree traversal",
        "binary tree": "tree traversal",
        "factorial": "factorial",
        "prime": "prime",
        "container with most water": "container with most water",
    }
    related_problem = None
    for keyword, problem in known_problems.items():
        if keyword in lower:
            related_problem = problem
            break

    solutions: dict[str, dict] = {
        "SyntaxError": {
            "analysis": (
                "A SyntaxError means Python couldn't understand your code due to "
                "invalid syntax. Common causes: missing colons, unmatched parentheses, "
                "quotes, or brackets; using invalid characters or keywords incorrectly."
            ),
            "fix": (
                "1. Check for missing colons (`:`) after `if`, `elif`, `else`, `for`, `while`, `def`, `class`, `try`, `except`, `finally`.\n"
                "2. Ensure parentheses `()`, brackets `[]`, and braces `{}` are properly balanced.\n"
                "3. Check string quotes — they must match (single/double).\n"
                "4. Look for misplaced keywords or operators.\n"
                "5. The error often points to the exact line where parsing fails."
            ),
        },
        "IndentationError": {
            "analysis": (
                "An IndentationError means your code has inconsistent or incorrect indentation. "
                "Python relies on indentation to define code blocks."
            ),
            "fix": (
                "1. Use 4 spaces per indentation level (PEP 8 standard).\n"
                "2. Do NOT mix tabs and spaces — configure your editor to convert tabs to spaces.\n"
                "3. Ensure all lines in a block have the same indentation.\n"
                "4. Check that `if`, `for`, `while`, `def`, `class`, etc. are followed by indented blocks."
            ),
        },
        "TypeError": {
            "analysis": (
                "A TypeError occurs when an operation is applied to an object of inappropriate type. "
                "For example, adding a string and an integer, or calling a non-callable object."
            ),
            "fix": (
                "1. Check the types of your variables with `type()`.\n"
                "2. Use `str()`, `int()`, `float()`, `list()` for explicit type conversion.\n"
                "3. Ensure function arguments match expected types.\n"
                "4. Use type hints and a type checker like mypy to catch mismatches early.\n"
                "5. Common fixes: `str(123)` instead of `'hello' + 123`; `int('5')` instead of `'5' + 3`."
            ),
        },
        "NameError": {
            "analysis": (
                "A NameError means you're trying to use a variable, function, or module that "
                "hasn't been defined or isn't in scope."
            ),
            "fix": (
                "1. Check spelling — Python names are case-sensitive (`myVar` vs `myvar`).\n"
                "2. Ensure the variable/function is defined before use.\n"
                "3. Check scope — variables defined inside a function aren't accessible outside.\n"
                "4. For modules: verify you installed the package (`pip install <name>`).\n"
                "5. For imports: check the module path and file location."
            ),
        },
        "IndexError": {
            "analysis": (
                "An IndexError happens when you try to access a list/tuple index that doesn't exist. "
                "Python uses 0-based indexing, so a list of length N has indices 0 through N-1."
            ),
            "fix": (
                "1. Check the list length with `len()` before accessing an index.\n"
                "2. Remember: last valid index is `len(lst) - 1`, not `len(lst)`.\n"
                "3. Use `lst[-1]` to safely access the last element.\n"
                "4. For loops: prefer `for item in lst:` over index-based access.\n"
                "5. Use slicing `lst[start:end]` which gracefully handles out-of-range."
            ),
        },
        "KeyError": {
            "analysis": (
                "A KeyError occurs when you try to access a dictionary key that doesn't exist."
            ),
            "fix": (
                "1. Use `dict.get(key, default)` instead of `dict[key]` to safely access keys.\n"
                "2. Check if key exists first: `if key in my_dict:`.\n"
                "3. Use `collections.defaultdict` for dictionaries with default values.\n"
                "4. Verify the key spelling and case."
            ),
        },
        "AttributeError": {
            "analysis": (
                "An AttributeError means you're trying to access an attribute or method "
                "that doesn't exist on the object."
            ),
            "fix": (
                "1. Check the object type with `type(obj)` — you may have the wrong type.\n"
                "2. Verify the attribute/method name spelling and case.\n"
                "3. Check if None — calling `.method()` on None is a common cause.\n"
                "4. For modules: `module.method()` vs `module.ModuleClass.method()`.\n"
                "5. Check your imports — you may have imported the wrong class."
            ),
        },
        "ImportError": {
            "analysis": (
                "An ImportError or ModuleNotFoundError means Python can't find the module "
                "or name you're trying to import."
            ),
            "fix": (
                "1. Install the package: `pip install <package-name>`.\n"
                "2. Check the module/file name for typos.\n"
                "3. Ensure the file exists in your Python path or current directory.\n"
                "4. For local modules: check relative vs absolute imports.\n"
                "5. Check for circular imports between your files."
            ),
        },
        "ZeroDivisionError": {
            "analysis": "A ZeroDivisionError occurs when you try to divide a number by zero.",
            "fix": (
                "1. Check the divisor before dividing: `if divisor != 0:`.\n"
                "2. Use a small epsilon for floats: `result = a / (b if b != 0 else 1e-10)`.\n"
                "3. In statistics, add `1e-10` to denominators to avoid division by zero.\n"
                "4. Consider using `try/except ZeroDivisionError` for defensive programming."
            ),
        },
        "RecursionError": {
            "analysis": (
                "A RecursionError means a function called itself too many times (default limit ~1000). "
                "Usually caused by missing or incorrect base case in recursion."
            ),
            "fix": (
                "1. Ensure your recursive function has a proper base case that returns without recursing.\n"
                "2. Verify the recursive step makes progress toward the base case.\n"
                "3. For deep recursion, consider an iterative solution or increase the limit:\n"
                "   `import sys; sys.setrecursionlimit(10000)`.\n"
                "4. Check for infinite recursion — the stack trace shows the repeating pattern."
            ),
        },
        "FileNotFoundError": {
            "analysis": "A FileNotFoundError means Python couldn't find the file at the specified path.",
            "fix": (
                "1. Verify the file path — absolute vs relative path.\n"
                "2. Check the current working directory: `import os; print(os.getcwd())`.\n"
                "3. Use `os.path.join()` to build paths correctly.\n"
                "4. Check file permissions and extensions.\n"
                "5. For user-provided paths: strip whitespace, validate input."
            ),
        },
        "ConnectionError": {
            "analysis": (
                "A ConnectionError means the network connection was refused or reset. "
                "The server may be down, or a firewall is blocking the connection."
            ),
            "fix": (
                "1. Check if the server is running: `ping <host>` or `curl <url>`.\n"
                "2. Verify the URL and port number.\n"
                "3. Check firewall and network settings.\n"
                "4. For APIs: check your API key and authentication headers.\n"
                "5. Add retry logic with exponential backoff for transient failures."
            ),
        },
    }

    info = solutions.get(
        error_type,
        {
            "analysis": (
                "An unexpected error occurred. Here's how to approach debugging it:\n\n"
                "1. Read the error message carefully — it often tells you exactly what's wrong.\n"
                "2. Look at the line number and surrounding code in the traceback.\n"
                "3. Isolate the problem by testing smaller pieces of code.\n"
                "4. Use `print()` or a debugger to inspect variable values.\n"
                "5. Search for the error message online — someone has likely encountered it before."
            ),
            "fix": (
                "General debugging steps:\n"
                "1. Reproduce the error with minimal code.\n"
                "2. Add `print()` statements before the failing line to check values.\n"
                "3. Use `assert` to validate assumptions.\n"
                "4. Write a unit test that covers the failing case.\n"
                "5. Use `pdb` or an IDE debugger to step through the code."
            ),
        },
    )

    result = {
        "error_type": error_type,
        "analysis": info["analysis"],
        "fix": info["fix"],
        "code": "",
    }

    if related_problem:
        try:
            solution_code = generate_code(related_problem)
            result["code"] = solution_code
            result["fix"] += (
                f"\n\n---\n\n"
                f"**Related solution for \"{related_problem}\":**\n\n"
                "The error might be related to generating code for \"%s\". "
                "Here's the correct implementation below." % related_problem
            )
        except Exception:
            pass

    return result


class DebugView(APIView):
    def post(self, request: Request):
        serializer = DebugInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        error_text = serializer.validated_data["error"]
        model = serializer.validated_data.get("model", "")
        if model:
            from src.llm_service import set_model

            set_model(model)

        result = _solve_error(error_text)
        return Response({
            "type": "debug",
            **result,
        })


class UploadFileView(APIView):
    def post(self, request: Request):
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        uploaded = serializer.validated_data["file"]
        prompt = serializer.validated_data.get("prompt", "")
        model = serializer.validated_data.get("model", "")
        agents = serializer.validated_data.get("agents", [])
        service = serializer.validated_data.get("service", "")
        history_raw = serializer.validated_data.get("history", [])
        plan = serializer.validated_data.get("plan", "")
        execute_plan = serializer.validated_data.get("execute_plan", False)
        plan_approved = serializer.validated_data.get("plan_approved", False)
        research_mode = serializer.validated_data.get("research_mode", False)

        # Support JSON string for history (from FormData)
        history = []
        if isinstance(history_raw, str):
            try:
                import json

                history = json.loads(history_raw)
            except (json.JSONDecodeError, TypeError):
                history = []
        elif isinstance(history_raw, list):
            history = history_raw

        if model:
            from src.llm_service import set_model

            set_model(model)

        # Save file temporarily
        upload_dir = Path(PROJECT_ROOT) / "uploads"
        upload_dir.mkdir(exist_ok=True)
        ext = Path(uploaded.name).suffix if uploaded.name else ".bin"
        dest = upload_dir / f"{int(time.time())}_{os.urandom(4).hex()}{ext}"
        with open(dest, "wb") as f:
            for chunk in uploaded.chunks():
                f.write(chunk)

        file_info = {
            "name": uploaded.name,
            "size": uploaded.size,
            "content_type": uploaded.content_type,
            "path": str(dest),
        }

        # Extract text content from file for LLM processing
        from src.file_utils import classify_mime, extract_text

        ct = (uploaded.content_type or "").lower()
        file_type = classify_mime(ct)
        extracted = extract_text(dest, ct)
        content_snippet = extracted[:2000] if extracted else ""

        type_labels = {
            "image": "image",
            "video": "video",
            "audio": "audio",
            "pdf": "PDF document",
            "word": "Word document",
            "excel": "Excel spreadsheet",
            "csv": "CSV file",
            "powerpoint": "PowerPoint presentation",
            "text": "text file",
        }
        label = type_labels.get(file_type, "file")

        if content_snippet:
            augmented = (
                f"[Uploaded {label}: {uploaded.name}]\n"
                f"--- File content ---\n{content_snippet}\n--- End ---\n{prompt}"
                if prompt else
                f"[Uploaded {label}: {uploaded.name}]\n--- File content ---\n{content_snippet}\n--- End ---"
            )
        elif file_type == "image":
            augmented = f"[Uploaded image: {uploaded.name}]\n{prompt}" if prompt else f"Describe this image: {uploaded.name}"
        elif file_type == "video":
            augmented = f"[Uploaded video: {uploaded.name}]\n{prompt}" if prompt else f"Describe this video: {uploaded.name}"
        elif file_type == "audio":
            augmented = f"[Uploaded audio: {uploaded.name}]\n{prompt}" if prompt else f"Transcribe this audio: {uploaded.name}"
        else:
            augmented = f"[Uploaded {label}: {uploaded.name}]\n{prompt}" if prompt else f"Process this {label}: {uploaded.name}"

        # Route to workflow if service is coding or default
        if service in ("", "coding"):
            orch = _ensure_orchestrator()
            future = asyncio.run_coroutine_threadsafe(
                orch.process_request(
                    augmented,
                    history,
                    agents=agents,
                    service=service,
                    plan=plan,
                    execute_plan=execute_plan,
                    plan_approved=plan_approved,
                    research_mode=research_mode,
                ),
                _loop,
            )
            result = future.result(timeout=120)
            return Response({
                "success": True,
                "file": file_info,
                "type": result.get("type", "code"),
                "code": result.get("code", ""),
                "review": result.get("review", ""),
                "tests": result.get("tests", ""),
                "research": result.get("research", ""),
                "plan": result.get("plan", ""),
                "requires_approval": result.get("requires_approval", False),
            })

        # Chat mode
        from src.llm_service import chat_with_llm

        reply = chat_with_llm(augmented, history, model=model or None)
        return Response({
            "success": True,
            "file": file_info,
            "type": "chat",
            "message": reply,
        })


class GenerateImageView(APIView):
    def post(self, request: Request):
        serializer = ImageInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        prompt = serializer.validated_data["prompt"]
        model = serializer.validated_data.get("model", "")

        try:
            from src.llm_service import generate_image_with_llm

            result = generate_image_with_llm(prompt, model=model or None)
            return Response({
                "success": result.get("success", False),
                "image_data": result.get("image_data", ""),
                "mime_type": result.get("mime_type", ""),
                "error": result.get("error", ""),
            })
        except Exception as exc:
            logger.exception("Image generation failed")
            return Response({
                "success": False,
                "error": str(exc),
            }, status=500)


class ApprovePlanView(APIView):
    def post(self, request: Request):
        serializer = WorkflowInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        prompt = serializer.validated_data["prompt"]
        history = serializer.validated_data.get("history", [])
        model = serializer.validated_data.get("model", "")
        agents = serializer.validated_data.get("agents", [])
        plan = serializer.validated_data.get("plan", "")
        start = time.perf_counter()

        if model:
            from src.llm_service import set_model

            set_model(model)

        try:
            orch = _ensure_orchestrator()
            future = asyncio.run_coroutine_threadsafe(
                orch.process_request(
                    prompt,
                    history,
                    agents=agents,
                    plan=plan,
                    plan_approved=True,
                ),
                _loop,
            )
            result = future.result(timeout=120)
            duration = time.perf_counter() - start

            return Response({
                "success": True,
                "code": result.get("code", ""),
                "review": result.get("review", ""),
                "tests": result.get("tests", ""),
                "duration": duration,
            })
        except Exception as exc:
            logger.exception("Plan approval execution failed")
            return Response({
                "success": False,
                "error": str(exc),
            }, status=500)


class UsageStatsView(APIView):
    def get(self, request: Request):
        from src.llm_service import get_available_models
        from src.usage_tracker import get_all_usage

        models = get_available_models()
        usage = get_all_usage(models)
        return Response({
            "usage": usage,
            "models": models,
        })

