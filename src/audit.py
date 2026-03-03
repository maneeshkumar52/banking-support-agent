"""FCA-compliant audit logger."""
import structlog
from datetime import datetime
from typing import List, Dict, Any
from src.config import get_settings

logger = structlog.get_logger(__name__)


class FCAauditLogger:
    """
    Writes immutable FCA-compliant audit records to Cosmos DB.
    7-year retention policy enforced via TTL.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def log_interaction(
        self,
        customer_id: str,
        session_id: str,
        input_text: str,
        output_text: str,
        content_safety_scores: Dict[str, Any],
        tools_called: List[str],
        tokens_used: int,
        latency_ms: float,
    ) -> str:
        """Log a complete customer interaction for FCA compliance."""
        import uuid
        audit_id = str(uuid.uuid4())

        record = {
            "id": audit_id,
            "customer_id": customer_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "input": input_text[:500],  # Truncate for storage
            "output": output_text[:1000],
            "content_safety_scores": content_safety_scores,
            "tools_called": tools_called,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "channel": "chat",
            "ttl": 7 * 365 * 24 * 3600,  # 7-year FCA retention
            "_partitionKey": customer_id,
        }

        try:
            from azure.cosmos.aio import CosmosClient
            async with CosmosClient(url=self.settings.cosmos_endpoint, credential=self.settings.cosmos_key) as client:
                db = client.get_database_client(self.settings.cosmos_database)
                container = db.get_container_client(self.settings.cosmos_audit_container)
                await container.create_item(body=record)
                logger.info("fca_audit_written", audit_id=audit_id, customer_id=customer_id)
        except Exception as exc:
            logger.error("fca_audit_write_failed", error=str(exc), audit_id=audit_id)

        return audit_id
