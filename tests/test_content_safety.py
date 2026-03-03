"""Tests for the content safety gate."""
import pytest
from unittest.mock import AsyncMock, patch
from src.content_safety import ContentSafetyGate


@pytest.mark.asyncio
async def test_safe_banking_query():
    """Safe banking query should pass content safety."""
    gate = ContentSafetyGate()
    gate._client = None  # Force local check
    result = await gate.screen_input("What is my current account balance?")
    assert result["safe"] is True


@pytest.mark.asyncio
async def test_self_harm_content_blocked():
    """Self-harm content must be blocked with zero tolerance."""
    gate = ContentSafetyGate()
    gate._client = None  # Force local check
    result = await gate.screen_input("I want to kill myself")
    assert result["safe"] is False
    assert result["scores"]["self_harm"] > 0


@pytest.mark.asyncio
async def test_screen_output_safe():
    """Safe banking response should pass output screening."""
    gate = ContentSafetyGate()
    gate._client = None
    result = await gate.screen_output("Your balance is £4,523.67. Is there anything else I can help you with?")
    assert result["safe"] is True


@pytest.mark.asyncio
async def test_azure_api_failure_falls_back_to_local():
    """Content safety falls back to local check when Azure API fails."""
    gate = ContentSafetyGate()
    # Mock a failing Azure client
    with patch.object(gate, '_get_client', return_value=None):
        result = await gate.screen_input("What are the transfer fees?")
        assert result["safe"] is True
        assert result["source"] == "local_heuristic"
