import os
from utils import slack, get_region, get_sensor_id
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--message', type=str, default='Hello World!')
    parser.add_argument('--slack_webhook_url', type=str, default=None)
    args = parser.parse_args()
    if args.slack_webhook_url:
        prefix = f'[id={get_sensor_id()}][geo={get_region()}]'
        prefix = f"[sensorid={get_sensor_id()}][mod=CORE][geo={get_region()}]"
        msg = f':alert: *{prefix}*\n{args.message}'
        slack(msg, args.slack_webhook_url)
