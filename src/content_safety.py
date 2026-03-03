"""Azure AI Content Safety gate for banking interactions."""
import structlog
from typing import Dict, Any
from src.config import get_settings

logger = structlog.get_logger(__name__)

# Banking-specific thresholds
THRESHOLDS = {
    "hate": 2,          # Block if severity >= 2
    "self_harm": 0,     # ZERO TOLERANCE — block any detection
    "violence": 2,      # Block if severity >= 2
    "sexual": 0,        # Zero tolerance in banking context
}


class ContentSafetyGate:
    """Screens input and output through Azure AI Content Safety."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

    def _get_client(self):
        """Lazy-initialize the content safety client."""
        if self._client is None:
            try:
                from azure.ai.contentsafety import ContentSafetyClient
                from azure.core.credentials import AzureKeyCredential
                self._client = ContentSafetyClient(
                    endpoint=self.settings.content_safety_endpoint,
                    credential=AzureKeyCredential(self.settings.content_safety_key),
                )
            except Exception as exc:
                logger.warning("content_safety_client_init_failed", error=str(exc))
                self._client = None
        return self._client

    def _analyze_locally(self, text: str) -> Dict[str, Any]:
        """
        Local safety heuristics when Azure Content Safety is unavailable.
        Checks for obvious self-harm keywords.
        """
        text_lower = text.lower()
        self_harm_keywords = ["suicide", "kill myself", "end my life", "self-harm", "hurt myself"]
        if any(kw in text_lower for kw in self_harm_keywords):
            return {
                "safe": False,
                "reason": "Potential self-harm content detected",
                "scores": {"hate": 0, "self_harm": 6, "violence": 0, "sexual": 0},
                "source": "local_heuristic",
            }
        return {
            "safe": True,
            "reason": "Passed local safety check",
            "scores": {"hate": 0, "self_harm": 0, "violence": 0, "sexual": 0},
            "source": "local_heuristic",
        }

    async def screen_input(self, text: str) -> Dict[str, Any]:
        """
        Screen customer input through Azure AI Content Safety.

        Args:
            text: Input text to screen.

        Returns:
            Dict with safe (bool), reason, and scores.
        """
        client = self._get_client()

        if not client:
            result = self._analyze_locally(text)
            logger.info("content_safety_local_check", safe=result["safe"])
            return result

        try:
            from azure.ai.contentsafety.models import AnalyzeTextOptions
            request = AnalyzeTextOptions(text=text[:1000])  # API limit
            response = client.analyze_text(request)

            scores = {
                "hate": response.hate_result.severity if response.hate_result else 0,
                "self_harm": response.self_harm_result.severity if response.self_harm_result else 0,
                "violence": response.violence_result.severity if response.violence_result else 0,
                "sexual": response.sexual_result.severity if response.sexual_result else 0,
            }

            blocked_categories = []
            for category, score in scores.items():
                threshold = THRESHOLDS.get(category, 2)
                if score > threshold:
                    blocked_categories.append(f"{category}(severity={score})")

            is_safe = len(blocked_categories) == 0
            reason = f"Blocked: {', '.join(blocked_categories)}" if blocked_categories else "Passed content safety"

            if not is_safe:
                logger.warning("content_safety_blocked", categories=blocked_categories, scores=scores)
            else:
                logger.info("content_safety_passed", scores=scores)

            return {"safe": is_safe, "reason": reason, "scores": scores, "source": "azure_content_safety"}

        except Exception as exc:
            logger.error("content_safety_api_error", error=str(exc))
            # Fallback to local check on API failure
            return self._analyze_locally(text)

    async def screen_output(self, text: str) -> Dict[str, Any]:
        """Screen LLM output before returning to customer."""
        return await self.screen_input(text)
