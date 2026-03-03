# Secure Banking Support Agent

**Project 2, Chapter 20 of "Prompt to Production" by Maneesh Kumar**

A production-grade, FCA-compliant banking customer support AI agent built with Azure OpenAI, Azure AI Content Safety, and Cosmos DB. Demonstrates secure agentic design patterns for regulated financial services.

---

## Overview

This project implements a banking-grade AI support agent with enterprise security controls:

- **Azure OpenAI GPT-4o** with function calling for intelligent tool orchestration
- **Azure AI Content Safety** screening every input and output (zero-tolerance for self-harm)
- **FCA-compliant audit logging** to Cosmos DB with 7-year TTL retention
- **PCI-DSS awareness** — card numbers are never stored or echoed
- **Conversation memory** with session management
- **FastAPI** REST API ready for containerised deployment

---

## Architecture

```
                        Customer Request
                              |
                    +---------v----------+
                    |   FastAPI Layer    |
                    |  /api/v1/query     |
                    +---------+---------+
                              |
                    +---------v----------+
                    |  Content Safety    |  <-- Azure AI Content Safety
                    |  Input Screening   |      (self_harm=0 threshold)
                    +---------+---------+
                              |
                    +---------v----------+
                    |   BankingAgent     |
                    |  (Agent Loop)      |
                    +---------+---------+
                      |               |
          +-----------v--+    +-------v-----------+
          | Azure OpenAI |    |   Tool Handlers   |
          |   GPT-4o     |    | - check_balance   |
          |  (temp=0.3)  |    | - get_transactions|
          +-----------+--+    | - get_card_status |
                      |       | - password_reset  |
                      |       | - standing_orders |
                      |       | - report_fraud    |
                      |       +-------------------+
                      |
            +---------v----------+
            |  Content Safety    |  <-- Output screening
            |  Output Screening  |
            +---------+---------+
                      |
            +---------v----------+
            |   FCA Audit Log    |  <-- Cosmos DB (7-year TTL)
            |   (Cosmos DB)      |
            +--------------------+
```

---

## Security Features

### Content Safety Thresholds (Banking-Specific)
| Category   | Threshold | Policy                          |
|------------|-----------|----------------------------------|
| hate       | 2         | Block severity >= 2              |
| self_harm  | 0         | ZERO TOLERANCE — block any score |
| violence   | 2         | Block severity >= 2              |
| sexual     | 0         | Zero tolerance in banking        |

When Azure Content Safety is unavailable, local keyword heuristics provide fallback protection.

### PCI-DSS Compliance
- Card numbers are always masked: `****-****-****-XXXX`
- Full card numbers are never requested, stored, or echoed in chat
- Customers are directed to secure channels for card-sensitive operations

### FCA Audit Logging
- Every interaction is written to Cosmos DB with a 7-year TTL (`ttl = 7 * 365 * 24 * 3600`)
- Records include: customer_id, session_id, timestamps, tool calls, safety scores, token counts
- Input truncated to 500 chars, output to 1000 chars — no PII over-retention
- Partition key on `customer_id` for efficient regulatory retrieval

### Data Masking
- Account numbers shown as `****XXXX` (last 4 only)
- Balance confirmed only after tool-based verification
- Fraud line always surfaced: `0800-FRAUD-1`

---

## Sample Conversation

```
Customer: "What's my current balance and any recent transactions?"

Agent (internal):
  1. Calls check_account_balance(customer_id="CUST001")
     -> {"balance": 4523.67, "currency": "GBP", "account_type": "Premier Current Account"}
  2. Calls get_recent_transactions(customer_id="CUST001", days=30)
     -> [{"date": "2024-11-14", "description": "Tesco Express", "amount": -23.45}, ...]

Agent Response:
  "Your Premier Current Account balance is £4,523.67.

  Here are your recent transactions:
  - 14 Nov: Tesco Express — -£23.45
  - 12 Nov: Amazon.co.uk — -£67.99
  - 10 Nov: Netflix — -£15.99
  ...

  ---
  *Contoso Bank is authorised by the Prudential Regulation Authority...*"
```

---

## Prerequisites

- Python 3.11+
- Azure subscription with:
  - Azure OpenAI resource (GPT-4o deployment)
  - Azure AI Content Safety resource
  - Azure Cosmos DB account
  - (Optional) Azure Key Vault for secret management

---

## Local Development Setup

1. **Clone and install dependencies:**
   ```bash
   cd banking-support-agent
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure resource credentials
   ```

3. **Run the API server:**
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

4. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

---

## API Examples

### Health Check
```bash
curl http://localhost:8000/health
```
**Response:**
```json
{"status": "healthy", "service": "banking-support-agent", "version": "1.0.0"}
```

### Start a Session
```bash
curl -X POST http://localhost:8000/api/v1/session/start \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "CUST001"}'
```
**Response:**
```json
{
  "session_id": "3f8a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "customer_id": "CUST001",
  "status": "active"
}
```

### Submit a Banking Query
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST001",
    "message": "What is my current balance?",
    "session_id": "3f8a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
  }'
```

**Expected JSON Output:**
```json
{
  "response": "Your Premier Current Account balance is £4,523.67, with £4,523.67 available...\n\n---\n*Contoso Bank is authorised by the Prudential Regulation Authority...*",
  "session_id": "3f8a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "safety_scores": {
    "hate": 0,
    "self_harm": 0,
    "violence": 0,
    "sexual": 0
  },
  "blocked": false,
  "tool_calls": [
    {
      "tool": "check_account_balance",
      "args": {"customer_id": "CUST001"}
    }
  ],
  "latency_ms": 1243.5,
  "tokens_used": 387
}
```

### Query Blocked by Content Safety
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST001",
    "message": "I want to kill myself",
    "session_id": "3f8a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c"
  }'
```
**Response:**
```json
{
  "response": "I'm concerned about your wellbeing. If you're going through a difficult time, please reach out to the Samaritans: 116 123 (free, 24/7). Our specialist support team is also available at 0800-CONTOSO.",
  "session_id": "3f8a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "blocked": true,
  "tool_calls": [],
  "latency_ms": 12.3
}
```

### Get Session History
```bash
curl http://localhost:8000/api/v1/session/3f8a2b1c-4d5e-6f7a-8b9c-0d1e2f3a4b5c/history
```

---

## Containerised Deployment (Azure Container Apps)

```bash
chmod +x infra/azure-deploy.sh
./infra/azure-deploy.sh
```

The script provisions:
- Azure Container Registry
- Container Apps Environment
- Container App with autoscaling (1–10 replicas)

---

## Project Structure

```
banking-support-agent/
├── src/
│   ├── __init__.py          # Package init
│   ├── main.py              # FastAPI application entry point
│   ├── agent.py             # Core banking agent with tool loop
│   ├── content_safety.py    # Azure AI Content Safety gate
│   ├── tools.py             # Banking tool definitions and handlers
│   ├── audit.py             # FCA-compliant Cosmos DB audit logger
│   ├── prompts.py           # Banking system prompts and disclaimers
│   └── config.py            # Pydantic settings with Azure config
├── tests/
│   ├── __init__.py
│   ├── test_content_safety.py  # Content safety unit tests
│   ├── test_tools.py           # Tool handler unit tests
│   └── test_e2e.py             # End-to-end agent tests
├── infra/
│   ├── Dockerfile           # Container image definition
│   └── azure-deploy.sh      # Azure Container Apps deployment script
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

---

## Regulatory Compliance Notes

- **FCA SYSC 3.2.6**: All AI-generated customer communications are logged with full audit trail
- **PCI-DSS Requirement 3**: Cardholder data is never stored, processed, or transmitted in plaintext
- **GDPR Article 5(1)(e)**: Audit records are retained for the minimum period required (7 years per FCA rules) and no longer
- **FCA CONC**: Appropriate disclaimers and regulated entity disclosures appended to all responses

---

## Book Reference

This project is **Project 2** from **Chapter 20: "Agentic AI in Regulated Industries"** of:

> **"Prompt to Production: Building Production AI Systems"**
> by Maneesh Kumar

The chapter covers enterprise patterns for deploying agentic AI in regulated environments including banking, healthcare, and legal services, with emphasis on content safety, audit compliance, and responsible AI guardrails.
