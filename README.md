<div align="center">

# 🏦 Banking Support Agent

### FCA-Compliant AI Banking Customer Support with Content Safety, Tool Calling & Audit Logging

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-0078D4?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
[![Content Safety](https://img.shields.io/badge/Azure_Content_Safety-1.0.0-0078D4?logo=microsoftazure)](https://azure.microsoft.com/en-us/products/ai-services/ai-content-safety)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*A production-grade banking customer support agent that screens every input and output through Azure AI Content Safety, executes banking operations via OpenAI tool calling, and writes immutable 7-year FCA audit trails to Cosmos DB — all behind a single API endpoint.*

*Chapter 20 of "Prompt to Production" by Maneesh Kumar*

[Architecture](#architecture) · [Quick Start](#quick-start) · [API Reference](#api-reference) · [Content Safety](#content-safety) · [Banking Tools](#banking-tools) · [Compliance](#fca-compliance--audit-logging)

</div>

---

## Why This Exists

Banking customer support agents face unique constraints that generic chatbots don't: regulatory compliance (FCA), data protection (PCI-DSS), duty of care (self-harm response), and audit trail requirements (7-year retention). Most AI chatbot frameworks ignore all of these.

**Banking Support Agent** solves this with a defense-in-depth architecture:

| Problem | Generic Chatbot | This System |
|---------|-----------------|-------------|
| Harmful content | Optional filter | **Dual screening** — input AND output through Azure Content Safety |
| Self-harm detection | Generic refusal | **Zero tolerance** + Samaritans crisis line (116 123) |
| Regulatory compliance | None | FCA/PRA/FSCS disclaimer on **every** response |
| Audit trail | Basic logging | **7-year immutable** Cosmos DB audit with per-interaction granularity |
| Card numbers | May leak in logs | **PCI-DSS by design** — masked at data layer (`****-****-****-XXXX`) |
| Banking operations | General tools | 6 purpose-built tools: balance, transactions, card, password, standing orders, fraud |
| Fraud handling | Not addressed | **Auto card block** + case creation + fraud team notification |
| Temperature | 0.7–1.0 (creative) | **0.3** (consistent, factual — banking requires accuracy) |

---

## Architecture

### High-Level Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL CLIENTS                                │
│              (Browser / Mobile App / API Consumer)                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP POST /api/v1/query
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   FastAPI Application (main.py)                     │
│                                                                     │
│  Lifespan Manager → BankingAgent + FCAauditLogger singletons       │
│  CORS Middleware (all origins)                                      │
│                                                                     │
│  Endpoints:                                                         │
│    GET  /health                  → Health check                     │
│    POST /api/v1/query            → Main chat endpoint               │
│    POST /api/v1/session/start    → Start new session                │
│    GET  /api/v1/session/{id}/history → Conversation history         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│  ContentSafetyGate   │  │         BankingAgent (agent.py)      │
│  ─────────────────── │  │                                      │
│                      │  │  ┌─────────────────────────────┐     │
│  1. Azure AI Content │  │  │  Azure OpenAI (GPT-4o)      │     │
│     Safety API       │  │  │  - temperature: 0.3          │     │
│  2. Local heuristic  │  │  │  - max_tokens: 800           │     │
│     fallback         │  │  │  - tool_choice: "auto"       │     │
│                      │  │  │  - max_retries: 3            │     │
│  Thresholds:         │  │  └─────────────┬───────────────┘     │
│  - hate: 2           │  │                │                      │
│  - self_harm: 0      │  │  ┌─────────────▼───────────────┐     │
│  - violence: 2       │  │  │  Tool Calling Loop          │     │
│  - sexual: 0         │  │  │  (max 5 iterations)         │     │
│                      │  │  │                              │     │
│  Screens BOTH input  │  │  │  Tools:                      │     │
│  AND output          │  │  │  ├─ check_account_balance    │     │
│                      │  │  │  ├─ get_recent_transactions  │     │
└──────────────────────┘  │  │  ├─ get_card_status          │     │
                          │  │  ├─ initiate_password_reset   │     │
                          │  │  ├─ get_standing_orders       │     │
                          │  │  └─ report_suspicious_activity│     │
                          │  └──────────────────────────────┘     │
                          │                                      │
                          │  Session: in-memory (last 10 msgs)   │
                          └──────────────────┬───────────────────┘
                                             │
                                             ▼
                          ┌──────────────────────────────────────┐
                          │     FCAauditLogger (audit.py)        │
                          │  - Cosmos DB async client             │
                          │  - 7-year TTL (220,752,000 seconds)  │
                          │  - Partition key: customer_id         │
                          │  - Records: input, output, scores,    │
                          │    tools called, tokens, latency      │
                          └──────────────────────────────────────┘
```

### Request Flow

```
Client              FastAPI          ContentSafety       BankingAgent        AzureOpenAI         Tools            FCAauditLogger
  │                   │                  │                   │                  │                 │                   │
  │─ POST /query ────►│                  │                   │                  │                 │                   │
  │                   │── screen_input()►│                   │                  │                 │                   │
  │                   │◄── safe/blocked─│                   │                  │                 │                   │
  │                   │                  │                   │                  │                 │                   │
  │                   │ [if blocked: return safety response + Samaritans info if self-harm]      │                   │
  │                   │                  │                   │                  │                 │                   │
  │                   │── handle_message()──────────────────►│                  │                 │                   │
  │                   │                  │                   │── completions() ►│                 │                   │
  │                   │                  │                   │◄── tool_calls ──│                 │                   │
  │                   │                  │                   │── execute_tool()──────────────────►│                   │
  │                   │                  │                   │◄── result ────────────────────────│                   │
  │                   │                  │                   │── completions() ►│ (with results) │                   │
  │                   │                  │                   │◄── final text ──│                 │                   │
  │                   │                  │                   │                  │                 │                   │
  │                   │── screen_output()►                   │                  │                 │                   │
  │                   │◄── safe/blocked─│                   │                  │                 │                   │
  │                   │                  │                   │                  │                 │                   │
  │                   │── log_interaction()─────────────────────────────────────────────────────►│
  │                   │◄── audit_id ───────────────────────────────────────────────────────────│
  │                   │                  │                   │                  │                 │                   │
  │◄── JSON response─│                  │                   │                  │                 │                   │
```

---

## Design Decisions

### Why Dual Content Screening (Input AND Output)?

```
Input screening alone:
  Safe input → LLM → ⚠️ LLM generates harmful content → Customer sees it

Dual screening (this system):
  Safe input → LLM → Output screening → ✅ Harmful output blocked
  Harmful input → ❌ Blocked before LLM → Customer gets safety response
```

**Decision**: In regulated financial services, the LLM can generate harmful content even from safe inputs (e.g., discussing debt could trigger self-harm references). Screening output provides defense-in-depth.

### Why Zero-Tolerance Self-Harm (Threshold = 0)?

| Category | Threshold | Rationale |
|----------|-----------|-----------|
| Hate | 2 | Allow mild expressions, block moderate+ |
| Self-harm | **0** | **Duty of care** — any detection triggers Samaritans hotline |
| Violence | 2 | Allow mild context, block moderate+ |
| Sexual | **0** | Completely inappropriate in banking context |

**Decision**: FCA-regulated firms have a duty of care obligation. When a customer expresses self-harm ideation, the system must respond with crisis support (Samaritans: 116 123) rather than banking answers.

### Why Hardcoded Disclaimer on Every Response?

```python
DISCLAIMER_TEXT = """
---
*Contoso Bank is authorised by the Prudential Regulation Authority and regulated
by the Financial Conduct Authority and the Prudential Regulation Authority.
Financial services are provided subject to our terms and conditions. FSCS protection
applies to eligible deposits up to £85,000.*
"""
```

**Decision**: FCA requires regulatory status disclosure. Appending it automatically (not relying on the LLM) ensures 100% compliance regardless of model behaviour.

### Why PCI-DSS Masking at Data Layer?

```python
# Card numbers masked IN the mock data, not in presentation
MOCK_CUSTOMERS = {
    "CUST001": {"card_number_masked": "****-****-****-4821", ...}
}
```

**Decision**: Masking at the data layer means even internal logs, debugging sessions, and error traces cannot leak card numbers. This is PCI-DSS by design, not by configuration.

### Why 7-Year Audit TTL?

**Decision**: FCA record-keeping rules require firms to retain records of customer interactions for a minimum of 5 years (MiFID II) to 7 years. Cosmos DB TTL automates purging — no manual cleanup required.

### Why `uksouth` Azure Region?

**Decision**: UK data residency compliance. FCA-regulated customer data should not leave UK jurisdiction. `uksouth` ensures data sovereignty.

---

## Content Safety

### Architecture

```
Input Text (max 1000 chars)
    │
    ▼
┌───────────────────────────────────┐
│ ContentSafetyGate                 │
│                                   │
│  ┌─── Primary: Azure API ──────┐ │
│  │ Analyzes for:               │ │
│  │  • Hate speech (threshold 2)│ │
│  │  • Self-harm (threshold 0)  │ │
│  │  • Violence (threshold 2)   │ │
│  │  • Sexual (threshold 0)     │ │
│  └─────────────────────────────┘ │
│           │                       │
│    [API unavailable?]             │
│           │                       │
│  ┌─── Fallback: Keywords ──────┐ │
│  │ "suicide", "kill myself",   │ │
│  │ "end my life", "self-harm", │ │
│  │ "hurt myself"               │ │
│  └─────────────────────────────┘ │
└───────────────────────────────────┘
```

### Screening Responses

| Detection | Response |
|-----------|----------|
| Self-harm detected | "I'm concerned about your wellbeing. If you're going through a difficult time, please reach out to the Samaritans: **116 123** (free, 24/7). Our specialist support team is also available at 0800-CONTOSO." |
| Other content blocked | "I'm unable to process this request. Please contact us directly at 0800-CONTOSO for assistance." |
| Output blocked | "I apologise, but I'm unable to provide this response. Please contact us directly at 0800-CONTOSO." |

---

## Banking Tools

### Tool Roster

| # | Tool | Function | Description |
|---|------|----------|-------------|
| 1 | `check_account_balance` | `tools.py` | Returns balance, currency, account type, available balance |
| 2 | `get_recent_transactions` | `tools.py` | Generates randomized transaction history (max 15, configurable days) |
| 3 | `get_card_status` | `tools.py` | PCI-DSS compliant masked card info, limits, contactless/international status |
| 4 | `initiate_password_reset` | `tools.py` | Creates password reset with PSW-XXXXXX reference, 24h expiry |
| 5 | `get_standing_orders` | `tools.py` | Returns standing orders and direct debits |
| 6 | `report_suspicious_activity` | `tools.py` | Creates FRAUD-XXXXXX case, **auto-blocks card**, notifies fraud team |

### Tool Calling Loop

```
User message → LLM (tool_choice="auto")
     │
     ├── LLM decides: no tools needed → return text response
     │
     └── LLM decides: call tool(s) → execute → feed results back → repeat
                                                     │
                                          (max 5 iterations)
                                                     │
                                          → final text response
```

### Mock Customer Data

<details>
<summary><strong>CUST001 — Alice Johnson (Premier Current Account)</strong></summary>

```python
{
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
}
```

</details>

<details>
<summary><strong>CUST002 — Bob Smith (Classic Current Account, BLOCKED card)</strong></summary>

```python
{
    "name": "Bob Smith",
    "account_type": "Classic Current Account",
    "balance": 234.12,
    "currency": "GBP",
    "card_number_masked": "****-****-****-9043",
    "card_status": "blocked",
    "daily_limit": 300.00,
    "standing_orders": [],
}
```

</details>

<details>
<summary><strong>CUST003 — Carol Davis (Savings Account)</strong></summary>

```python
{
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
}
```

</details>

---

## Agent Prompts

<details>
<summary><strong>Banking System Prompt (IDENTITY + COMPLIANCE + PCI-DSS + TONE + ESCALATION)</strong></summary>

```
You are a professional banking customer support assistant for Contoso Bank.

IDENTITY & ROLE:
- You are a knowledgeable, empathetic banking assistant
- You handle account inquiries, transaction questions, card services, and general banking queries

COMPLIANCE RULES (NON-NEGOTIABLE):
- NEVER display full account numbers — always mask as ****XXXX (last 4 digits only)
- NEVER confirm or deny specific account balances to unverified users without tool verification
- ALWAYS add appropriate disclaimers when discussing financial products
- For fraud suspicions, IMMEDIATELY direct to fraud line: 0800-FRAUD-1
- You cannot authorize transactions, approve loans, or change account limits

PCI-DSS AWARENESS:
- Do not store, log, or repeat card numbers in any response
- Direct card number queries to secure channels only
- Never ask customers to provide full card numbers in chat

TONE:
- Professional, warm, and empathetic
- Use clear, plain English — avoid banking jargon
- Acknowledge customer frustration with empathy before providing solutions
- Be concise but thorough

ESCALATION:
- Bereavement, power of attorney, domestic abuse situations → connect to specialist team
- Regulatory complaints → provide FCA reference and formal complaint process
- Complex fraud → Fraud Investigation Team (0800-FRAUD-1)
```

</details>

<details>
<summary><strong>Escalation Prompt</strong></summary>

```
The customer's issue requires specialist assistance that I cannot provide in this channel.
Please acknowledge their concern with empathy, provide the relevant specialist contact, and note that
their case has been flagged for priority handling.
```

</details>

<details>
<summary><strong>Regulatory Disclaimer (appended to every response)</strong></summary>

```
---
*Contoso Bank is authorised by the Prudential Regulation Authority and regulated by the
Financial Conduct Authority and the Prudential Regulation Authority. Financial services
are provided subject to our terms and conditions. FSCS protection applies to eligible
deposits up to £85,000.*
```

</details>

---

## FCA Compliance & Audit Logging

### Audit Record Schema

Every customer interaction creates an immutable record in Cosmos DB:

```python
{
    "id": "uuid-v4",                           # Unique audit ID
    "customer_id": "CUST001",                  # Partition key
    "session_id": "session-001",
    "timestamp": "2024-01-01T00:00:00.000Z",   # ISO 8601
    "input": "What is my balance?",            # Truncated to 500 chars
    "output": "Your balance is £4,523.67...",  # Truncated to 1000 chars
    "content_safety_scores": {
        "hate": 0, "self_harm": 0, "violence": 0, "sexual": 0
    },
    "tools_called": ["check_account_balance"],
    "tokens_used": 350,
    "latency_ms": 1234.56,
    "channel": "chat",
    "ttl": 220752000,                          # 7 years in seconds
    "_partitionKey": "CUST001"
}
```

### Compliance Design

| FCA Requirement | Implementation |
|-----------------|----------------|
| Record retention (5-7 years) | Cosmos DB TTL: 220,752,000 seconds (7 years) |
| Immutability | Write-once pattern — no update/delete methods exposed |
| Completeness | Records input, output, safety scores, tools, tokens, latency, channel |
| Customer lookup | Partition key = `customer_id` for O(1) regulatory queries |
| Non-blocking | Audit failures logged but don't fail the customer request |
| Input privacy | Input truncated to 500 chars, output to 1000 chars |

---

## Data Models

### Pydantic Models

```python
class QueryRequest(BaseModel):
    customer_id: str                              # Customer identifier
    message: str = Field(min_length=3)            # Customer message
    session_id: Optional[str] = None              # Session for continuity

class SessionStartRequest(BaseModel):
    customer_id: str                              # Customer identifier

class Settings(BaseSettings):
    azure_openai_endpoint: str                    # Azure OpenAI URL
    azure_openai_api_key: str                     # API key
    azure_openai_api_version: str = "2024-02-01"  # API version
    azure_openai_deployment: str = "gpt-4o"       # Model deployment
    content_safety_endpoint: str                  # Content Safety URL
    content_safety_key: str                       # Content Safety key
    cosmos_endpoint: str                          # Cosmos DB URL
    cosmos_key: str                               # Cosmos DB key
    cosmos_database: str = "banking-support"      # Database name
    cosmos_audit_container: str = "fca-audit"     # Audit container
    cosmos_sessions_container: str = "sessions"   # Sessions container
    use_managed_identity: bool = False            # Managed Identity toggle
    log_level: str = "INFO"                       # Log level
```

### Tool Response Schemas

| Tool | Key Response Fields |
|------|-------------------|
| `check_account_balance` | `balance`, `currency`, `account_type`, `available_balance`, `last_updated` |
| `get_recent_transactions` | List of `{date, description, amount, currency, category, reference, balance_after}` |
| `get_card_status` | `card_number_masked`, `status`, `expiry`, `daily_limit`, `contactless_limit` |
| `initiate_password_reset` | `success`, `reference` (PSW-XXXXXX), `expires_in` (24h) |
| `get_standing_orders` | List of `{payee, amount, frequency, next_date}` |
| `report_suspicious_activity` | `case_id` (FRAUD-XXXXXX), `temporary_card_block=True`, `fraud_team_notified=True` |

---

## API Reference

### `GET /health`

```bash
curl http://localhost:8000/health
```

```json
{"status": "healthy", "service": "banking-support-agent", "version": "1.0.0"}
```

### `POST /api/v1/query`

Main chat endpoint — full pipeline: safety → agent → tools → safety → audit.

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST001",
    "message": "What is my balance?",
    "session_id": "session-001"
  }'
```

**Response** (200):

```json
{
  "response": "Your current account balance is £4,523.67.\n---\n*Contoso Bank is authorised...*",
  "session_id": "session-001",
  "safety_scores": {"hate": 0, "self_harm": 0, "violence": 0, "sexual": 0},
  "blocked": false,
  "tool_calls": [{"tool": "check_account_balance", "args": {"customer_id": "CUST001"}}],
  "latency_ms": 1234.56,
  "tokens_used": 350
}
```

**Response** (blocked):

```json
{
  "response": "I'm concerned about your wellbeing...",
  "blocked": true,
  "safety_scores": {"self_harm": 6}
}
```

### `POST /api/v1/session/start`

```bash
curl -X POST http://localhost:8000/api/v1/session/start \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "CUST001"}'
```

```json
{"session_id": "uuid-v4", "customer_id": "CUST001", "status": "active"}
```

### `GET /api/v1/session/{session_id}/history`

```bash
curl http://localhost:8000/api/v1/session/session-001/history
```

```json
{
  "session_id": "session-001",
  "messages": [
    {"role": "user", "content": "What is my balance?"},
    {"role": "assistant", "content": "Your balance is..."}
  ],
  "count": 2
}
```

---

## Quick Start

### Prerequisites

| Requirement | Version | Check |
|------------|---------|-------|
| Python | 3.11+ | `python --version` |
| Azure OpenAI | GPT-4o deployment | Azure Portal |
| Azure Content Safety | (optional) | Falls back to local heuristics |
| pip | Latest | `pip --version` |

### Local Development

```bash
# Clone
git clone https://github.com/maneeshkumar52/banking-support-agent.git
cd banking-support-agent

# Virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
# Content Safety and Cosmos DB are optional (graceful fallbacks)

# Run
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Offline Validation (No Azure Needed)

```bash
python demo_e2e.py
```

```
=== Banking Support Agent - E2E Demo ===
✓ All 6 banking tools validated (balance, transactions, card, password, standing orders, fraud)
✓ Content safety local heuristics working (safe + blocked)
✓ System prompt loaded (BANKING_SYSTEM_PROMPT)
✓ QueryRequest model validated
=== All validations passed ===
```

### Docker

```bash
cd infra
docker build -f Dockerfile -t banking-support-agent ..
docker run -p 8000:8000 --env-file ../.env banking-support-agent
```

---

## Project Structure

```
banking-support-agent/
├── src/
│   ├── main.py                 # FastAPI app, endpoints, lifespan manager
│   ├── agent.py                # BankingAgent — tool loop, session, disclaimer
│   ├── tools.py                # 6 banking tools + mock data (3 customers)
│   ├── content_safety.py       # Azure Content Safety + local fallback
│   ├── audit.py                # FCA audit logger (Cosmos DB, 7yr TTL)
│   ├── prompts.py              # System prompt, escalation, disclaimer
│   └── config.py               # Settings via pydantic-settings
├── tests/
│   ├── test_content_safety.py  # 4 tests: safe, blocked, output, fallback
│   ├── test_tools.py           # 7 tests: all 6 tools + edge cases
│   └── test_e2e.py             # 2 tests: full pipeline + blocked input
├── infra/
│   ├── Dockerfile              # python:3.11-slim container
│   └── azure-deploy.sh         # Container Apps deployment (uksouth)
├── .env.example                # Environment variable template
├── demo_e2e.py                 # Offline validation script
└── requirements.txt            # 13 dependencies with pinned versions
```

### Module Responsibility Table

| Module | Files | Responsibility | Key Pattern |
|--------|-------|---------------|-------------|
| `src/agent.py` | 1 | Tool-calling loop, session management, disclaimer injection | Iterative agent loop (max 5) |
| `src/tools.py` | 1 | 6 banking tools + 3 mock customers | Registry pattern (TOOL_HANDLERS dict) |
| `src/content_safety.py` | 1 | Dual screening (input + output) with fallback | Strategy + graceful degradation |
| `src/audit.py` | 1 | Immutable FCA audit trail | Write-once, 7yr TTL |
| `src/prompts.py` | 1 | System prompt + escalation + disclaimer | Named constants |
| `src/config.py` | 1 | Environment configuration | LRU-cached singleton |
| `src/main.py` | 1 | FastAPI endpoints, lifespan | Async context manager |

---

## Configuration Reference

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | — | ✅ | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | — | ✅ | Azure OpenAI API key |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` | — | API version |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o` | — | Model deployment name |
| `CONTENT_SAFETY_ENDPOINT` | — | Optional | Content Safety URL (falls back to local) |
| `CONTENT_SAFETY_KEY` | — | Optional | Content Safety API key |
| `COSMOS_ENDPOINT` | — | Optional | Cosmos DB for audit logging |
| `COSMOS_KEY` | — | Optional | Cosmos DB key |
| `COSMOS_DATABASE` | `banking-support` | — | Database name |
| `COSMOS_AUDIT_CONTAINER` | `fca-audit` | — | Audit records container |
| `USE_MANAGED_IDENTITY` | `false` | — | Toggle Managed Identity |
| `LOG_LEVEL` | `INFO` | — | Logging level |

### Hardcoded Constants

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| `MAX_TOOL_ITERATIONS` | 5 | `agent.py` | Prevent infinite tool loops |
| Temperature | 0.3 | `agent.py` | Consistent banking responses |
| Max tokens | 800 | `agent.py` | Bounded response length |
| Max retries | 3 | `agent.py` | OpenAI client retries |
| History window | 10 messages | `agent.py` | Session context limit |
| Audit TTL | 220,752,000s | `audit.py` | 7-year FCA retention |
| Input truncation | 500 chars | `audit.py` | Audit storage limit |
| Output truncation | 1000 chars | `audit.py` | Audit storage limit |
| API text limit | 1000 chars | `content_safety.py` | Content Safety API limit |

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.111.0 | Web framework |
| `uvicorn` | 0.30.0 | ASGI server |
| `openai` | 1.40.0 | Azure OpenAI (AsyncAzureOpenAI) |
| `azure-ai-contentsafety` | 1.0.0 | Content screening API |
| `azure-cosmos` | 4.7.0 | Audit trail persistence |
| `azure-identity` | 1.16.0 | Managed Identity support |
| `azure-keyvault-secrets` | 4.8.0 | Key Vault integration |
| `pydantic` | 2.7.0 | Data models |
| `pydantic-settings` | 2.3.0 | Environment config |
| `structlog` | 24.2.0 | Structured JSON logging |
| `python-dotenv` | 1.0.1 | `.env` file loading |
| `pytest` | 8.2.0 | Test framework |
| `pytest-asyncio` | 0.23.0 | Async test support |

---

## Testing

### Run Tests

```bash
pytest tests/ -v
```

### Test Coverage

| Test File | Tests | What's Validated |
|-----------|-------|-----------------|
| `test_content_safety.py` | 4 | Safe banking query passes, self-harm blocked, output screening, API fallback to local |
| `test_tools.py` | 7 | All 6 tools + unknown customer edge case, PCI-DSS masking, fraud auto-block |
| `test_e2e.py` | 2 | Full agent pipeline (mocked), harmful input blocked before LLM |

All tests use `unittest.mock.AsyncMock` — no live API calls.

---

## Error Handling Strategy

| Component | Error Type | Behaviour |
|-----------|-----------|-----------|
| Content Safety API | Unavailable | Falls back to local keyword heuristics |
| Content Safety | Self-harm detected | Returns Samaritans hotline (116 123) |
| Content Safety | Other block | Returns "contact 0800-CONTOSO" message |
| OpenAI tool loop | Max iterations (5) | Returns "gathering information" fallback |
| OpenAI output | Blocked by output screening | Returns "unable to provide this response" |
| Audit logger | Cosmos DB write failure | Logged but doesn't fail customer request |
| API endpoint | General exception | HTTP 500 with error detail |

---

## Deployment

### Docker

```bash
docker build -f infra/Dockerfile -t banking-support-agent .
docker run -p 8000:8000 --env-file .env banking-support-agent
```

### Azure Container Apps

```bash
bash infra/azure-deploy.sh
```

Deploys to `uksouth` (UK data residency):

| Resource | Configuration |
|----------|---------------|
| Resource Group | `rg-banking-agent` |
| Container Registry | Basic SKU |
| Container Apps Environment | `uksouth` |
| Container App | Port 8000, external ingress, 1-10 replicas |

### Azure Production Architecture

```
┌──────────────────────────────────────────────────────────┐
│                Azure (uksouth)                            │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Azure OpenAI │  │ Content      │  │  Cosmos DB   │   │
│  │ (GPT-4o)     │  │ Safety       │  │ (fca-audit)  │   │
│  │ temp=0.3     │  │ (dual screen)│  │ 7yr TTL      │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         └──────────────────┼──────────────────┘          │
│                            │                              │
│                   ┌────────▼────────┐                     │
│                   │ Container App   │                     │
│                   │ (FastAPI)       │                     │
│                   │ 1-10 replicas   │                     │
│                   └─────────────────┘                     │
└──────────────────────────────────────────────────────────┘
```

---

## Design Patterns Summary

| # | Pattern | Where | Purpose |
|---|---------|-------|---------|
| 1 | Dual-Screening Gateway | `content_safety.py` | Input AND output content filtering |
| 2 | Iterative Tool Agent | `agent.py` | LLM decides tools, max 5 iterations |
| 3 | Strategy + Fallback | `content_safety.py` | Azure API primary, local heuristic fallback |
| 4 | Write-Once Audit | `audit.py` | Immutable FCA compliance records |
| 5 | Registry | `tools.py` | `TOOL_HANDLERS` dict maps names to functions |
| 6 | Singleton (LRU) | `config.py` | Single Settings instance |
| 7 | Lifespan Manager | `main.py` | Async context for startup/shutdown |
| 8 | Lazy Initialization | `content_safety.py` | Client created on first use |
| 9 | Session Sliding Window | `agent.py` | Last 10 messages per session |

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `openai.AuthenticationError` | Invalid credentials | Verify `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` |
| Content safety always uses local | Missing Content Safety config | Set `CONTENT_SAFETY_ENDPOINT` and `CONTENT_SAFETY_KEY` |
| All responses blocked | Content Safety thresholds too strict | Check that legitimate banking queries aren't triggering false positives |
| Audit records not appearing | Cosmos DB not configured | Set `COSMOS_ENDPOINT`, `COSMOS_KEY`, create `fca-audit` container |
| "Tool loop exhausted" response | Complex query requiring >5 tool calls | Increase `MAX_TOOL_ITERATIONS` or simplify the query |
| Missing disclaimer on response | Code issue | Verify `DISCLAIMER_TEXT` in `prompts.py` is non-empty |
| Docker build fails | Wrong build context | Build from repo root: `docker build -f infra/Dockerfile .` |
| Session history empty | New session ID | Sessions are in-memory only — restart clears them |

---

## Production Checklist

- [ ] Add API authentication (OAuth 2.0 / API key middleware)
- [ ] Restrict CORS from `["*"]` to specific domains
- [ ] Add rate limiting per customer
- [ ] Replace mock customer data with real account integrations
- [ ] Add non-root `USER` directive in Dockerfile
- [ ] Move sessions from in-memory to Cosmos DB
- [ ] Enable Managed Identity (`USE_MANAGED_IDENTITY=true`)
- [ ] Configure Application Insights for telemetry
- [ ] Add circuit breaker for Azure OpenAI calls
- [ ] Set up Cosmos DB backup policies
- [ ] Add real-time fraud alerting integration
- [ ] Implement multi-channel support (voice, email, SMS)

---

## License

This project is part of **"Prompt to Production"** by Maneesh Kumar (Chapter 20).

---

<div align="center">

**[⬆ Back to Top](#-banking-support-agent)**

</div>