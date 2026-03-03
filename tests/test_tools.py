"""Tests for banking tool handlers."""
import pytest
from src.tools import (
    check_account_balance, get_recent_transactions, get_card_status,
    initiate_password_reset, get_standing_orders, report_suspicious_activity,
)


@pytest.mark.asyncio
async def test_check_balance_known_customer():
    result = await check_account_balance("CUST001")
    assert result["balance"] == 4523.67
    assert result["currency"] == "GBP"
    assert "last_updated" in result


@pytest.mark.asyncio
async def test_check_balance_unknown_customer():
    result = await check_account_balance("CUST999")
    assert result["balance"] == 0.00


@pytest.mark.asyncio
async def test_get_transactions_returns_list():
    result = await get_recent_transactions("CUST001", days=30)
    assert isinstance(result, list)
    assert len(result) > 0
    for txn in result:
        assert "date" in txn
        assert "amount" in txn
        assert txn["amount"] < 0  # Debits are negative


@pytest.mark.asyncio
async def test_get_card_status_blocked():
    result = await get_card_status("CUST002")
    assert result["status"] == "blocked"
    assert "****" in result["card_number_masked"]


@pytest.mark.asyncio
async def test_get_card_status_active():
    result = await get_card_status("CUST001")
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_password_reset_returns_success():
    result = await initiate_password_reset("CUST001")
    assert result["success"] is True
    assert "reference" in result


@pytest.mark.asyncio
async def test_get_standing_orders():
    result = await get_standing_orders("CUST001")
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["payee"] == "Landlord Properties Ltd"


@pytest.mark.asyncio
async def test_report_suspicious_activity():
    result = await report_suspicious_activity("CUST001", "Unrecognised transaction of £500 in Paris")
    assert "case_id" in result
    assert result["case_id"].startswith("FRAUD-")
    assert result["temporary_card_block"] is True
