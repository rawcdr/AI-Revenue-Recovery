import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        
        # Add extra fields if passed via 'extra' dictionary
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "candidate_id"):
            log_record["candidate_id"] = record.candidate_id
        if hasattr(record, "action_type"):
            log_record["action_type"] = record.action_type
        if hasattr(record, "status"):
            log_record["status"] = record.status
        if hasattr(record, "event_type"):
            log_record["event_type"] = record.event_type
            
        return json.dumps(log_record)

def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        # Prevent propagation to avoid double logging
        logger.propagate = False
    return logger
