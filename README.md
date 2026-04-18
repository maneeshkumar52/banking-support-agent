# Banking Support Agent

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

AI-powered banking support agent with content safety filtering, FCA-compliant audit logging, tool-based account operations, and structured prompt engineering — built with Azure OpenAI and FastAPI.

## Architecture

```
Customer Message
        │
        ▼
┌──────────────────────────────────────┐
│  FastAPI Service (:8000)             │
│                                      │
│  ContentSafetyFilter ──► Screening  │──► Block harmful/PII content
│       │                              │
│  BankingAgent ──► Azure OpenAI      │──► Tool-augmented responses
│       ├── Tools:                     │
│       │   ├── account_balance       │
│       │   ├── transaction_history   │
│       │   ├── transfer_funds        │
│       │   └── card_management       │
│       │                              │
│  FCAauditLogger ──► Audit trail     │──► FCA-compliant logging
└──────────────────────────────────────┘
```

## Key Features

- **Content Safety** — `ContentSafetyFilter` screens inputs/outputs for harmful content and PII before processing
- **Tool-Augmented Agent** — `BankingAgent` with structured tools for account balance, transactions, transfers, and card management
- **FCA Audit Logging** — `FCAauditLogger` records all interactions for Financial Conduct Authority compliance
- **Structured Prompts** — Dedicated `prompts.py` with banking-specific system prompts and guardrails
- **End-to-End Demo** — `demo_e2e.py` exercises the full agent pipeline

## Step-by-Step Flow

### Step 1: Message Received
Customer sends a support message via `POST /chat`.

### Step 2: Content Safety
`ContentSafetyFilter` screens the input for harmful content, PII, and prompt injection attempts.

### Step 3: Agent Processing
`BankingAgent` processes the query using GPT-4o with banking-specific prompts. If the query requires data, it invokes tools (balance lookup, transaction history, etc.).

### Step 4: Tool Execution
Tools execute against mock/real banking backends, returning structured results.

### Step 5: Audit Logging
`FCAauditLogger` records the full interaction (query, response, tools used, timestamps) for compliance.

### Step 6: Response
Filtered and audited response returned to the customer.

## Repository Structure

```
banking-support-agent/
├── src/
│   ├── main.py              # FastAPI entry point
│   ├── agent.py              # BankingAgent with tool calling
│   ├── tools.py              # Account/transaction/card tools
│   ├── content_safety.py     # ContentSafetyFilter
│   ├── audit.py              # FCAauditLogger
│   ├── prompts.py            # Banking system prompts
│   └── config.py             # Environment settings
├── tests/
│   ├── test_content_safety.py
│   ├── test_tools.py
│   └── test_e2e.py
├── demo_e2e.py
├── requirements.txt
└── .env.example
```

## Quick Start

```bash
git clone https://github.com/maneeshkumar52/banking-support-agent.git
cd banking-support-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Testing

```bash
pytest -q
python demo_e2e.py
```

## License

MIT
