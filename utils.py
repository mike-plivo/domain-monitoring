import os
import logging
import requests
import socket
import redis

def slack(message, slack_webhook_url):
    """
    Function to send slack messages
    :param message: message to be sent
    :return: None
    """
    res = requests.post(
        slack_webhook_url,
        json={"text": message})
    return res

def get_region():
    region = os.getenv("AWS_REGION", "")
    if not region:
        region = os.getenv("FLY_REGION", "")
    if not region:
        region = socket.gethostname() or "unknown"
    return region

def create_logger(name):
    logger = logging.getLogger(f"[{name}:{get_region()}]")
    level =  os.getenv("LOG_LEVEL", "DEBUG").upper()
    if level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif level == "INFO":
        logger.setLevel(logging.INFO)
    elif level == "WARNING":
        logger.setLevel(logging.WARNING)
    elif level == "ERROR":
        logger.setLevel(logging.ERROR)
    elif level == "CRITICAL":
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    fh = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(fh)
    logger.addHandler(ch)
    return logger

def create_redis_client():
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", 6379)
    db = os.getenv("REDIS_DB", 0)
    return redis.Redis(host=host, port=port, db=db)

