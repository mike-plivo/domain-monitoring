import requests

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
