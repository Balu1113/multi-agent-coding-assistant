from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from src.agents.base_agent import BaseAgent, AgentRole, Task, AgentResult
from src.llm_service import generate_code_with_llm, review_code_with_llm, generate_tests_with_llm
from src.communication.message_queue import MessageQueue
from src.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)

_LANG_EXT = {
    "python": "py", "javascript": "js", "typescript": "ts", "java": "java",
    "cpp": "cpp", "c++": "cpp", "go": "go", "rust": "rs",
    "ruby": "rb", "php": "php", "swift": "swift", "kotlin": "kt",
    "scala": "scala", "r": "r", "sql": "sql",
}
_DEFAULT_EXT = "txt"


def _detect_language(prompt: str) -> str:
    lower = prompt.lower()
    for alias, lang in _LANG_EXT.items():
        if re.search(rf'\b{re.escape(alias)}\b', lower):
            return lang
    return "python"


def _format_history(history: list[dict[str, Any]]) -> str:
    if not history:
        return ""
    lines = ["\n\nPrevious conversation:"]
    workspace_chars = 0
    for h in history:
        p = h.get("prompt", "")
        r = h.get("result", {})
        if isinstance(r, dict) and r.get("type") == "workspace_context":
            inventory = r.get("inventory", "")
            if isinstance(inventory, str) and inventory:
                lines.append(f"\nProject file inventory:\n{inventory[:8000]}")
            lines.append("\nCurrent workspace files:")
            for file in r.get("files", []):
                if not isinstance(file, dict) or workspace_chars >= 60000:
                    break
                path = file.get("path", "(unknown path)")
                content = file.get("content", "")
                if not isinstance(content, str):
                    continue
                snippet = content[:60000 - workspace_chars]
                lines.append(f"\n--- {path} ---\n{snippet}")
                workspace_chars += len(snippet)
                if file.get("truncated") or len(snippet) < len(content):
                    lines.append("[File content truncated to fit model context]")
            continue
        if isinstance(r, dict) and r.get("type") == "coding":
            lines.append(f"User: {p[:200]}")
            lines.append(f"Assistant: [generated code with review and tests]")
        elif isinstance(r, dict) and r.get("type") == "chat":
            lines.append(f"User: {p[:200]}")
            lines.append(f"Assistant: {r.get('message', '')[:200]}")
    return "\n".join(lines)


_LEETCODE_KEYWORDS = [
    "leetcode", "solution", "class solution", "isvalidsudoku", "solven-queens",
    "foursum", "threesum", "twosum", "mergetwosortedlists", "addtwonumbers",
    "longestsubstring", "median", "longestpalindrome", "reverseinteger",
    "stringtointeger", "palindromenumber", "romantointeger", "longestcommonprefix",
    "3sum", "4sum", "containerwithmostwater",
]


def _is_lc_request(prompt: str) -> bool:
    lower = prompt.lower().replace(" ", "")
    if re.search(r'\bclass\s+solution\b', lower):
        return True
    for kw in _LEETCODE_KEYWORDS:
        if kw.replace(" ", "") in lower:
            return True
    return False


class CoderAgent(BaseAgent):
    def __init__(self, message_queue: MessageQueue, retriever: RAGRetriever) -> None:
        super().__init__(AgentRole.CODER, message_queue)
        self.retriever = retriever

    async def execute_task(self, task: Task) -> AgentResult:
        prompt = task.description
        history = task.context.get("history", [])
        plan = task.context.get("plan", "")
        logger.info("CoderAgent executing task: %s", prompt)

        code = await self._write_code(prompt, history, plan)
        review = await self._review_code(code, prompt)
        tests = await self._generate_tests(code, prompt)

        language = _detect_language(prompt)
        ext = _LANG_EXT.get(language, _DEFAULT_EXT)

        return AgentResult(
            task_id=task.id,
            agent_role=self.role,
            success=True,
            output=f"--- Code ---\n{code}\n\n--- Review ---\n{review}\n\n--- Tests ---\n{tests}",
            artifacts=[f"code_{task.id}.{ext}", f"test_{task.id}.py"],
            metadata={
                "code": code,
                "review": review,
                "tests": tests,
                "language": language,
            },
        )

    async def _write_code(self, prompt: str, history: list, plan: str) -> str:
        logger.info("CoderAgent phase 1/3: Writing code for: %s", prompt)
        language = _detect_language(prompt)
        is_lc = _is_lc_request(prompt)
        lc_instruction = (
            "\n\nIMPORTANT: Output as a class `Solution` with a method that takes `self` as the first parameter. "
            "Do NOT output a standalone function."
        ) if is_lc else ""

        context_prompt = prompt + _format_history(history) + lc_instruction
        if plan:
            context_prompt = f"Plan:\n{plan}\n\n{context_prompt}"

        try:
            code = await asyncio.to_thread(lambda: generate_code_with_llm(context_prompt, language))
        except Exception as exc:
            logger.exception("LLM code generation failed")
            raise RuntimeError(
                "Code generation failed because the configured model request failed. "
                "Check the selected model and provider credentials, then retry."
            ) from exc

        docs = await self.retriever.retrieve(prompt, top_k=2)
        context_lines = "\n".join(
            f"# {d['content'][:100]}" for d in docs
        )
        return f"{context_lines}\n\n{code}"

    async def _review_code(self, code: str, prompt: str) -> str:
        logger.info("CoderAgent phase 2/3: Reviewing code")
        try:
            review = await asyncio.to_thread(review_code_with_llm, code, prompt)
            return review
        except Exception as e:
            logger.warning("LLM review failed, using rule-based: %s", e)
            issues = []
            if "pass" in code and "raise NotImplementedError" not in code:
                issues.append("Contains placeholder `pass` statement")
            if "TODO:" in code:
                issues.append("Contains TODO markers")
            if not issues:
                issues.append("No obvious issues found")
            return (
                "## Code Review Report (rule-based)\n\n"
                "### Issues:\n" + "\n".join(f"- {i}" for i in issues) + "\n\n"
                "*LLM unavailable — used basic pattern checks*"
            )

    async def _generate_tests(self, code: str, prompt: str) -> str:
        logger.info("CoderAgent phase 3/3: Generating tests")
        try:
            tests = await asyncio.to_thread(generate_tests_with_llm, code, prompt)
            return tests
        except Exception as e:
            logger.warning("LLM test generation failed, using template: %s", e)
            return (
                "import pytest\n\n"
                "# Test file generated (rule-based fallback)\n"
                f"# For prompt: {prompt[:80]}\n\n"
                "def test_basic():\n"
                '    """Basic functionality test."""\n'
                "    assert True\n\n"
                "if __name__ == '__main__':\n"
                "    pytest.main([__file__])\n"
            )
