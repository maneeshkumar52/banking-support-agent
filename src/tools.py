"""Banking tool definitions with OpenAI function calling schemas."""
import json
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List
import structlog

logger = structlog.get_logger(__name__)

# Mock customer data
MOCK_CUSTOMERS = {
    "CUST001": {
        "name": "Alice Johnson",
        "account_type": "Premier Current Account",
        "balance": 4523.67,
        "currency": "GBP",
        "card_number_masked": "****-****-****-4821",
        "card_status": "active",
        "daily_limit": 500.00,
        "standing_orders": [
            {"payee": "Landlord Properties Ltd", "amount": 1200.00, "frequency": "monthly", "next_date": "2024-12-01"},
            {"payee": "Netflix", "amount": 15.99, "frequency": "monthly", "next_date": "2024-11-28"},
        ],
    },
    "CUST002": {
        "name": "Bob Smith",
        "account_type": "Classic Current Account",
        "balance": 234.12,
        "currency": "GBP",
        "card_number_masked": "****-****-****-9043",
        "card_status": "blocked",
        "daily_limit": 300.00,
        "standing_orders": [],
    },
    "CUST003": {
        "name": "Carol Davis",
        "account_type": "Savings Account",
        "balance": 28750.00,
        "currency": "GBP",
        "card_number_masked": "****-****-****-1122",
        "card_status": "active",
        "daily_limit": 1000.00,
        "standing_orders": [
            {"payee": "Council Tax Direct Debit", "amount": 145.00, "frequency": "monthly", "next_date": "2024-12-03"},
        ],
    },
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_account_balance",
            "description": "Check the current account balance for a verified banking customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer's unique identifier"}
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_transactions",
            "description": "Get recent transaction history for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "days": {"type": "integer", "default": 30, "description": "Number of days of history"},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_card_status",
            "description": "Get the status of a customer's debit or credit card",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "initiate_password_reset",
            "description": "Initiate an online banking password reset for a customer",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_standing_orders",
            "description": "Retrieve a customer's standing orders and direct debits",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_suspicious_activity",
            "description": "Report and flag suspicious account activity for investigation",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "description": {"type": "string", "description": "Description of the suspicious activity"},
                },
                "required": ["customer_id", "description"],
            },
        },
    },
]


async def check_account_balance(customer_id: str) -> Dict[str, Any]:
    """Return masked account balance."""
    customer = MOCK_CUSTOMERS.get(customer_id, {"balance": 0.00, "currency": "GBP", "account_type": "Current Account"})
    result = {
        "customer_id": customer_id,
        "balance": customer["balance"],
        "currency": customer["currency"],
        "account_type": customer["account_type"],
        "available_balance": customer["balance"] - 0,
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
    logger.info("tool_check_balance", customer_id=customer_id)
    return result


async def get_recent_transactions(customer_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """Return mock transaction history."""
    merchants = ["Tesco Express", "Amazon.co.uk", "Netflix", "Shell", "Marks & Spencer", "ASOS", "Deliveroo", "Sainsbury's", "Costa Coffee", "Boots"]
    categories = ["groceries", "shopping", "entertainment", "transport", "food_drink", "utilities", "health"]
    transactions = []
    for i in range(min(days // 3, 15)):
        date = (datetime.utcnow() - timedelta(days=i*2)).strftime("%Y-%m-%d")
        amount = -round(random.uniform(3.50, 120.00), 2)
        transactions.append({
            "date": date,
            "description": f"{random.choice(merchants)}",
            "amount": amount,
            "currency": "GBP",
            "category": random.choice(categories),
            "reference": f"TXN{random.randint(1000000, 9999999)}",
            "balance_after": round(1000 + random.uniform(-200, 200), 2),
        })
    logger.info("tool_get_transactions", customer_id=customer_id, count=len(transactions))
    return transactions


async def get_card_status(customer_id: str) -> Dict[str, Any]:
    """Return masked card status."""
    customer = MOCK_CUSTOMERS.get(customer_id, {"card_number_masked": "****-****-****-0000", "card_status": "active", "daily_limit": 300.00})
    result = {
        "customer_id": customer_id,
        "card_number_masked": customer["card_number_masked"],
        "status": customer["card_status"],
        "expiry": "09/27",
        "daily_limit": customer["daily_limit"],
        "contactless_limit": 100.00,
        "online_transactions": "enabled",
        "international_use": "enabled",
    }
    logger.info("tool_get_card_status", customer_id=customer_id, status=result["status"])
    return result


async def initiate_password_reset(customer_id: str) -> Dict[str, Any]:
    """Initiate password reset process."""
    result = {
        "success": True,
        "customer_id": customer_id,
        "message": "Password reset instructions sent to your registered email and mobile",
        "expires_in": "24 hours",
        "reference": f"PSW-{random.randint(100000, 999999)}",
        "timestamp": datetime.utcnow().isoformat(),
    }
    logger.info("tool_password_reset", customer_id=customer_id)
    return result


async def get_standing_orders(customer_id: str) -> List[Dict[str, Any]]:
    """Return standing orders for customer."""
    customer = MOCK_CUSTOMERS.get(customer_id, {})
    orders = customer.get("standing_orders", [])
    logger.info("tool_get_standing_orders", customer_id=customer_id, count=len(orders))
    return orders


async def report_suspicious_activity(customer_id: str, description: str) -> Dict[str, Any]:
    """Report suspicious activity."""
    case_id = f"FRAUD-{random.randint(100000, 999999)}"
    result = {
        "case_id": case_id,
        "customer_id": customer_id,
        "status": "opened",
        "priority": "high",
        "description": description,
        "fraud_team_notified": True,
        "temporary_card_block": True,
        "message": f"Your fraud case {case_id} has been opened. Our fraud team will contact you within 2 hours. Your card has been temporarily blocked for your protection.",
        "timestamp": datetime.utcnow().isoformat(),
    }
    logger.warning("tool_suspicious_activity_reported", customer_id=customer_id, case_id=case_id)
    return result


TOOL_HANDLERS = {
    "check_account_balance": check_account_balance,
    "get_recent_transactions": get_recent_transactions,
    "get_card_status": get_card_status,
    "initiate_password_reset": initiate_password_reset,
    "get_standing_orders": get_standing_orders,
    "report_suspicious_activity": report_suspicious_activity,
}
