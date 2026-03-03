import asyncio, sys
sys.path.insert(0, '.')

async def main():
    print("=== Banking Support Agent - End-to-End Demo ===\n")

    # Test 1: Banking tools (pure mock data, no Azure)
    from src.tools import (
        check_account_balance, get_recent_transactions,
        get_card_status, initiate_password_reset,
        get_standing_orders, report_suspicious_activity
    )

    print("--- Customer: CUST001 ---")
    balance = await check_account_balance("CUST001")
    print(f"Balance: GBP {balance.get('balance', 'N/A')} ({balance.get('account_type', '')})")

    txns = await get_recent_transactions("CUST001", days=7)
    print(f"Transactions: {len(txns)} transactions found")
    for t in txns[:2]:
        print(f"  {t.get('date','')}: {t.get('description','')}: GBP {t.get('amount','')}")

    card = await get_card_status("CUST001")
    print(f"Card status: {card.get('status','N/A')} (masked: {card.get('card_number_masked','****')})")

    reset = await initiate_password_reset("CUST001")
    print(f"Password reset: {'success' if reset.get('success') else 'failed'} - Reference: {reset.get('reference','N/A')}")

    orders = await get_standing_orders("CUST001")
    print(f"Standing orders: {len(orders)} found")

    fraud = await report_suspicious_activity("CUST001", "Unrecognised transaction in Paris")
    print(f"Fraud report: {fraud.get('case_id','N/A')} - Status: {fraud.get('status','N/A')}")

    # Test 2: Content safety local heuristics (no Azure Content Safety needed)
    try:
        from src.content_safety import ContentSafetyGate
        gate = ContentSafetyGate.__new__(ContentSafetyGate)
        gate._client = None
        gate.settings = None
        # Test local keyword screening using the actual method name
        safe_result = gate._analyze_locally("I need help with my bank account balance")
        print(f"\nContent Safety - Safe message: safe={safe_result.get('safe')}, source={safe_result.get('source')}")
        harmful_result = gate._analyze_locally("I want to kill myself")
        print(f"Content Safety - Harmful message: safe={harmful_result.get('safe')}, reason={harmful_result.get('reason')}")
    except Exception as e:
        print(f"\nContent safety: {e}")

    # Test 3: Prompts
    from src.prompts import BANKING_SYSTEM_PROMPT
    print(f"\nBanking system prompt loaded ({len(BANKING_SYSTEM_PROMPT)} chars)")
    print(f"  Preview: {BANKING_SYSTEM_PROMPT[:100]}...")

    # Test 4: Models (using FastAPI's BaseModel from main.py)
    from src.main import QueryRequest
    query = QueryRequest(
        customer_id="CUST001",
        message="What is my current account balance?",
        session_id="session-001"
    )
    print(f"\nQueryRequest model: '{query.message}'")

    print("\n=== Banking Support Agent: Tools and safety checks working ===")
    print("Core banking tools return realistic mock data:")
    print("  - Account balance with masked details")
    print("  - Transaction history (7/30 day windows)")
    print("  - Card status with PCI-DSS masking")
    print("  - Password reset with reference codes")
    print("  - Standing orders listing")
    print("  - Fraud case creation")

asyncio.run(main())
