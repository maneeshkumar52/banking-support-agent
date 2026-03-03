"""Banking agent with tool calling loop and content safety."""
import json
import time
import uuid
from typing import List, Dict, Any, Optional
import structlog
from openai import AsyncAzureOpenAI
from src.config import get_settings
from src.content_safety import ContentSafetyGate
from src.tools import TOOL_DEFINITIONS, TOOL_HANDLERS
from src.prompts import BANKING_SYSTEM_PROMPT, DISCLAIMER_TEXT

logger = structlog.get_logger(__name__)

MAX_TOOL_ITERATIONS = 5


class BankingAgent:
    """
    Banking support agent with content safety, tool calling, and session management.
    FCA-compliant with comprehensive audit logging.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = AsyncAzureOpenAI(
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_key=self.settings.azure_openai_api_key,
            api_version=self.settings.azure_openai_api_version,
            max_retries=3,
        )
        self.safety_gate = ContentSafetyGate()
        self._sessions: Dict[str, List[Dict]] = {}

    def _get_session_history(self, session_id: str) -> List[Dict]:
        """Get or create conversation history for a session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        return self._sessions[session_id]

    async def handle_message(
        self,
        customer_id: str,
        message: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle a customer message through the full agent pipeline.

        Args:
            customer_id: Customer identifier.
            message: Customer's message text.
            session_id: Optional session ID for conversation continuity.

        Returns:
            Dict with response, safety_scores, tool_calls, session_id, latency_ms.
        """
        start_time = time.time()
        session_id = session_id or str(uuid.uuid4())
        total_tokens = 0

        logger.info("agent_message_received", customer_id=customer_id, session_id=session_id)

        # Screen input
        input_safety = await self.safety_gate.screen_input(message)
        if not input_safety["safe"]:
            logger.warning("input_blocked_content_safety", reason=input_safety["reason"])
            response_text = self._get_safety_response(input_safety["reason"])
            return {
                "response": response_text,
                "session_id": session_id,
                "safety_scores": input_safety["scores"],
                "blocked": True,
                "tool_calls": [],
                "latency_ms": round((time.time() - start_time) * 1000, 2),
            }

        # Build messages with conversation history
        history = self._get_session_history(session_id)
        messages = [{"role": "system", "content": BANKING_SYSTEM_PROMPT}]
        messages.extend(history[-10:])  # Last 5 exchanges
        messages.append({"role": "user", "content": f"[Customer ID: {customer_id}] {message}"})

        tool_calls_made = []

        # Agent loop
        for iteration in range(MAX_TOOL_ITERATIONS):
            response = await self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=800,
            )

            if response.usage:
                total_tokens += response.usage.total_tokens

            choice = response.choices[0]

            if not choice.message.tool_calls:
                final_response = choice.message.content or ""
                break

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in choice.message.tool_calls
                ],
            })

            # Execute tool calls
            for tool_call in choice.message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                handler = TOOL_HANDLERS.get(func_name)
                result = await handler(**func_args) if handler else {"error": f"Unknown tool: {func_name}"}
                tool_calls_made.append({"tool": func_name, "args": func_args, "result": result})
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})
        else:
            final_response = "I've gathered the information needed to assist you. Please allow me a moment to finalize my response."

        # Append banking disclaimer
        final_response_with_disclaimer = final_response + DISCLAIMER_TEXT

        # Screen output
        output_safety = await self.safety_gate.screen_output(final_response)
        if not output_safety["safe"]:
            final_response_with_disclaimer = "I apologise, but I'm unable to provide this response. Please contact us directly at 0800-CONTOSO."
            logger.warning("output_blocked_content_safety")

        # Update conversation history
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": final_response})
        self._sessions[session_id] = history

        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.info("agent_response_generated", customer_id=customer_id, latency_ms=latency_ms, tokens=total_tokens)

        return {
            "response": final_response_with_disclaimer,
            "session_id": session_id,
            "safety_scores": input_safety["scores"],
            "blocked": False,
            "tool_calls": [{"tool": tc["tool"], "args": tc["args"]} for tc in tool_calls_made],
            "latency_ms": latency_ms,
            "tokens_used": total_tokens,
        }

    def _get_safety_response(self, reason: str) -> str:
        """Return appropriate response for blocked content."""
        if "self_harm" in reason.lower():
            return ("I'm concerned about your wellbeing. If you're going through a difficult time, "
                    "please reach out to the Samaritans: 116 123 (free, 24/7). "
                    "Our specialist support team is also available at 0800-CONTOSO.")
        return "I'm unable to process this request. Please contact us directly at 0800-CONTOSO for assistance."
