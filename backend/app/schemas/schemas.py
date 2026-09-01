from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional

class NormalizedEvent(BaseModel):
    event_id: str
    entity_type: str
    entity_id: str
    customer_id: str
    event_type: str
    amount: float
    currency: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class WebhookPayload(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: Optional[str] = None
    event: str
    payload: Dict[str, Any]
