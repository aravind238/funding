import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

print("Loading function")

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    log_level_name = event["log_level_name"]
    
    if log_level_name == "error":
        logger.error(event)
    elif log_level_name == "warning":
        logger.warning(event)
    else:
        logger.info(event)
