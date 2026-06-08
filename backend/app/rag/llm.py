from dataclasses import dataclass

import httpx

from backend.app.core.config import settings
from backend.app.rag.vector_store import SearchHit


@dataclass
class LLMResult:
    answer: str
    model_name: str


class LLMClient:
    refusal = "I do not know based on the available workspace documents."

    def generate_answer(self, question: str, contexts: list[SearchHit]) -> LLMResult:
        if not contexts:
            return LLMResult(answer=self.refusal, model_name=settings.llm_model)
        if settings.llm_provider == "openai-compatible":
            return self._openai_compatible_answer(question, contexts)
        return LLMResult(answer=self._local_answer(question, contexts), model_name=settings.llm_model)

    def _openai_compatible_answer(self, question: str, contexts: list[SearchHit]) -> LLMResult:
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        context_text = "\n\n".join(
            f"[{idx}] {hit.payload.get('filename')} p.{hit.payload.get('page_number')}: "
            f"{hit.payload.get('text')}"
            for idx, hit in enumerate(contexts, start=1)
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You answer enterprise knowledge-base questions only from the supplied context. "
                    "If the context is insufficient, say you do not know. Keep answers concise and "
                    "grounded in the cited context."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nContext:\n{context_text}",
            },
        ]
        response = httpx.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": settings.llm_model,
                "messages": messages,
                "temperature": settings.llm_temperature,
            },
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        answer = payload["choices"][0]["message"]["content"].strip()
        return LLMResult(answer=answer or self.refusal, model_name=settings.llm_model)

    def _local_answer(self, question: str, contexts: list[SearchHit]) -> str:
        snippets = []
        for hit in contexts[:3]:
            text = str(hit.payload.get("text", "")).strip()
            sentence = text.split(". ")[0].strip()
            if sentence:
                snippets.append(sentence[:500])
        if not snippets:
            return self.refusal
        return (
            "Based on the available workspace documents: "
            + " ".join(snippets)
            + f" Question answered: {question}"
        )

