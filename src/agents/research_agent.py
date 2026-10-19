from __future__ import annotations

import logging
import uuid
from src.agents.base_agent import BaseAgent, AgentRole, AgentResult, Task
from src.communication.message_queue import MessageQueue
from src.web_search import search_web

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    def __init__(self, message_queue: MessageQueue, retriever=None) -> None:
        super().__init__(AgentRole.RESEARCHER, message_queue)
        self.role = AgentRole.RESEARCHER
        self.id = f"researcher-{uuid.uuid4().hex[:6]}"

    async def execute_task(self, task: Task) -> AgentResult:
        prompt = task.description
        history = task.context.get("history", [])
        max_results = task.context.get("max_results", 5)

        from src.llm_service import chat_with_llm

        queries = self._generate_search_queries(prompt)
        all_results = []
        seen_urls = set()

        for query in queries[:3]:
            results = search_web(query)
            for r in results:
                if r.get("url") and r["url"] not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r["url"])
                    if len(all_results) >= max_results:
                        break
            if len(all_results) >= max_results:
                break

        system_context = ""
        if history:
            system_context = "Previous conversation:\n" + "\n".join(
                f"User: {h.get('prompt', '')}\nAssistant: {h.get('result', {}).get('message', '')}"
                for h in history[-4:]
            ) + "\n\n"

        sources_text = ""
        if all_results:
            sources_text = "\n\nWeb Search Results:\n" + "\n".join(
                f"- {r.get('title', 'Untitled')}: {r.get('snippet', '')}"
                for r in all_results[:max_results]
            )

        research_prompt = (
            "You are a deep research assistant. Given the user's query and the web search results below, "
            "provide a comprehensive, well-structured answer. Include relevant facts, data, and cite sources. "
            "If the search results are insufficient, state what additional information would be needed.\n\n"
            f"User Query: {prompt}"
            f"{sources_text}"
        )

        full_prompt = f"{system_context}{research_prompt}"
        answer = chat_with_llm(full_prompt)

        return AgentResult(
            task_id=task.id,
            agent_role=self.role,
            success=True,
            output=answer,
            artifacts=[
                {"type": "sources", "content": all_results},
                {"type": "research", "content": answer},
            ],
        )

    def _generate_search_queries(self, prompt: str) -> list[str]:
        queries = [prompt]

        words = prompt.split()
        if len(words) > 6:
            queries.append(" ".join(words[:8]))
            queries.append(" ".join(words[-6:]))

        topics = [
            "overview",
            "tutorial",
            "documentation",
            "examples",
            "best practices",
        ]
        for topic in topics[:2]:
            queries.append(f"{prompt} {topic}")

        return queries
