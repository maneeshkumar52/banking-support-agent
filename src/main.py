"""Banking Support Agent FastAPI entry point."""
import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger(__name__)

from src.agent import BankingAgent
from src.audit import FCAauditLogger

agent: BankingAgent = None
auditor: FCAauditLogger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent, auditor
    agent = BankingAgent()
    auditor = FCAauditLogger()
    logger.info("banking_support_agent_starting")
    yield
    logger.info("banking_support_agent_stopping")


app = FastAPI(
    title="Contoso Banking Support Agent",
    description="FCA-compliant banking AI with content safety — Project 2, Chapter 20, Prompt to Production",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class QueryRequest(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    message: str = Field(..., min_length=3, description="Customer message")
    session_id: Optional[str] = Field(default=None)


class SessionStartRequest(BaseModel):
    customer_id: str


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "banking-support-agent", "version": "1.0.0"}


@app.post("/api/v1/query")
async def handle_query(request: QueryRequest) -> dict:
    """Process a banking support query with content safety and FCA audit logging."""
    try:
        result = await agent.handle_message(
            customer_id=request.customer_id,
            message=request.message,
            session_id=request.session_id,
        )

        # Async audit log (non-blocking)
        await auditor.log_interaction(
            customer_id=request.customer_id,
            session_id=result["session_id"],
            input_text=request.message,
            output_text=result["response"],
            content_safety_scores=result.get("safety_scores", {}),
            tools_called=[tc["tool"] for tc in result.get("tool_calls", [])],
            tokens_used=result.get("tokens_used", 0),
            latency_ms=result.get("latency_ms", 0),
        )

        return result
    except Exception as exc:
        logger.error("query_endpoint_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/session/start")
async def start_session(request: SessionStartRequest) -> dict:
    """Start a new conversation session."""
    import uuid
    session_id = str(uuid.uuid4())
    return {"session_id": session_id, "customer_id": request.customer_id, "status": "active"}


@app.get("/api/v1/session/{session_id}/history")
async def get_history(session_id: str) -> dict:
    """Get conversation history for a session."""
    history = agent._sessions.get(session_id, [])
    return {"session_id": session_id, "messages": history, "count": len(history)}
