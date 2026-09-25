from openai import AsyncOpenAI

from app.core.config import Settings
from app.models.domain import RetrievalHit


class OpenRouterAnswerService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = (
            AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=str(settings.openrouter_base_url),
                default_headers=self._default_headers(settings),
            )
            if settings.openrouter_api_key
            else None
        )

    async def answer(self, question: str, contexts: list[RetrievalHit]) -> str:
        if not contexts:
            return "I could not find indexed evidence for that question yet."
        if not self._client:
            return self._fallback_answer(contexts)

        context_text = "\n\n".join(
            f"[{hit.citation_label}] {hit.title} | section={hit.section or 'n/a'} | page={hit.page or 'n/a'}\n{hit.content}"
            for hit in contexts
        )
        response = await self._client.chat.completions.create(
            model=self._settings.openrouter_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are FactChat, a research assistant. Answer using only the provided context. "
                        "Cite evidence inline with the provided citation labels. Mention paper titles when helpful. "
                        "If evidence is incomplete, say so explicitly."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nContext:\n{context_text}",
                },
            ],
        )
        message = response.choices[0].message.content if response.choices else None
        if not message:
            return self._fallback_answer(contexts)
        return message.strip()

    @staticmethod
    def _default_headers(settings: Settings) -> dict[str, str]:
        headers: dict[str, str] = {}
        if settings.openrouter_http_referer:
            headers["HTTP-Referer"] = settings.openrouter_http_referer
        if settings.openrouter_app_title:
            headers["X-Title"] = settings.openrouter_app_title
        return headers

    @staticmethod
    def _fallback_answer(contexts: list[RetrievalHit]) -> str:
        lines = [f"{hit.citation_label} {hit.title}: {hit.content}" for hit in contexts[:4]]
        return "OpenRouter is not configured. Top retrieved evidence:\n\n" + "\n\n".join(lines)
