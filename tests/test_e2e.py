"""End-to-end tests for the banking support agent."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_agent_handles_balance_query():
    """Test agent can handle a balance inquiry."""
    balance_result = {"balance": 4523.67, "currency": "GBP", "account_type": "Premier Current Account", "last_updated": "2024-11-15 10:00 UTC", "available_balance": 4523.67, "customer_id": "CUST001"}

    mock_no_tool = MagicMock()
    mock_no_tool.choices[0].message.content = "Your current account balance is £4,523.67."
    mock_no_tool.choices[0].message.tool_calls = None
    mock_no_tool.usage.total_tokens = 120

    with patch("openai.AsyncAzureOpenAI") as mock_openai:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_no_tool)
        mock_openai.return_value = mock_client

        from src.agent import BankingAgent
        agent = BankingAgent()
        agent.client = mock_client
        agent.safety_gate.screen_input = AsyncMock(return_value={"safe": True, "reason": "OK", "scores": {}})
        agent.safety_gate.screen_output = AsyncMock(return_value={"safe": True, "reason": "OK", "scores": {}})

        result = await agent.handle_message("CUST001", "What is my balance?", "session-001")

        assert result["blocked"] is False
        assert result["session_id"] == "session-001"
        assert "response" in result


@pytest.mark.asyncio
async def test_agent_blocks_harmful_input():
    """Test that harmful input is blocked before reaching the LLM."""
    from src.agent import BankingAgent
    with patch("openai.AsyncAzureOpenAI"):
        agent = BankingAgent()
        agent.safety_gate.screen_input = AsyncMock(return_value={
            "safe": False, "reason": "self_harm content detected", "scores": {"self_harm": 6}
        })

        result = await agent.handle_message("CUST001", "I want to hurt myself", "session-002")

        assert result["blocked"] is True
        assert "116 123" in result["response"] or "wellbeing" in result["response"].lower()
