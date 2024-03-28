import traceback
import time
import json
import hashlib
import argparse
from utils import slack, create_logger, create_redis_client, get_region, get_sensor_id

class BaseMonitor:
    def __init__(self, slack_webhook_url=None, **kwargs):
        self.class_name = self.__class__.__name__
        self.sensor_id = get_sensor_id()
        self.region = get_region()
        self.slack_webhook_url = slack_webhook_url
        self.redis_client = create_redis_client()
        self.redis_key = self._generate_redis_key(kwargs)
        self.prefix = f"[sensorid={self.sensor_id}][mod={self.class_name}][geo={self.region}]"
        self.parameters = kwargs.copy()
        for k, v in self.parameters.items():
            self.prefix += f"[{k}={v}]"
        self.logger = create_logger(self.prefix)
        self.logger.debug(f"initialized with parameters: {self.parameters}")
        self.logger.debug(f"initialized with redis key: {self.redis_key}")

    def _generate_redis_key(self, params):
        # Convert the dictionary to a JSON string. Ensure the dictionary is sorted by key to maintain order.
        d_str = json.dumps(params, sort_keys=True)
        # Use hashlib to create a hash of the JSON string. Here, sha256 is used for a good balance of speed and collision resistance.
        hash_obj = hashlib.sha256(d_str.encode())
        # Return the hexadecimal representation of the digest
        h = hash_obj.hexdigest()
        return f"{self.class_name}:{self.sensor_id}:{h}"

    def fetch_new_records(self):
        raise NotImplementedError()

    def _fetch_new_records(self):
        records = self.fetch_new_records()
        new_records = {}
        for k, v in records.items():
            if not isinstance(v, list):
                new_records[k] = [v]
            else:
                new_records[k] = v
        return new_records

    def store_records_in_redis(self, records):
        self.redis_client.set(self.redis_key, json.dumps(records))
        self.redis_client.expire(self.redis_key, 86400)

    def refresh_ttl(self):
        try:
            self.redis_client.expire(self.redis_key, 86400)
        except Exception as e:
            self.logger.warning(f"could not refresh Redis TTL: {e}", exc_info=True)

    def get_cached_records(self):
        return self.redis_client.get(self.redis_key)

    def detect_changes(self):
        new_records = self._fetch_new_records()
        self.logger.info(f"found new records: {json.dumps(new_records)}")
        changed = False
        changes = set()
        cached_records = self.get_cached_records()
        if not cached_records:
            msg = "records are not cached yet, nothing to compare with."
            self.logger.info(msg)
            for k, v in new_records.items():
                changes.add(f"{k}: {v}")
            changes = list(changes)
            self.logger.debug(f"caching records")
            self.store_records_in_redis(new_records)
            return changed, msg, list(changes)

        cached_records = json.loads(cached_records)
        self.logger.debug(f"cached records: {cached_records}")
        self.logger.debug(f"new records: {new_records}")
        for k, v in cached_records.items():
            if k not in new_records:
                self.logger.info(f"{k} -> record deleted: {v} -> (not present)")
                changes.add(f"{k} -> record deleted: {v} -> (not present)")
            elif k in new_records and sorted(new_records[k]) != sorted(v):
                self.logger.info(f"{k} -> record changed: {v} -> {new_records[k]}")
                changes.add(f"{k} -> record changed: {v} -> {new_records[k]}")
        for k, v in new_records.items():
            if k not in cached_records:
                self.logger.info(f"{k} -> record added: (not present) -> {v}")
                changes.add(f"{k} -> record added: (not present) -> {v}")
            elif k in cached_records and sorted(cached_records[k]) != sorted(v):
                self.logger.info(f"{k} -> record changed: {cached_records[k]} -> {v}")
                changes.add(f"{k} -> record changed: {cached_records[k]} -> {v}")
        if len(changes) > 0:
            msg = "records changed"
            changed = True
            self.logger.info(msg)
            self.logger.debug(f"caching new records")
            self.store_records_in_redis(new_records)
        else:
            msg = "records not changed"
            changed = False
            self.logger.info(msg)
            self.refresh_ttl()
        return changed, msg, list(changes)

    def monitor(self):
        """ Monitor records and send slack notifications if changes are detected """
        self.logger.info(f"monitoring started")
        changed, msg, changed_data = self.detect_changes()
        if changed_data and len(changed_data) > 0:
            if self.slack_webhook_url:
                if changed is True: emoji = ":warning:"
                else: emoji = ":information_source:"
                slack_message = f"{emoji} *{self.prefix}*\n{msg}\n"
                slack_message += '```'
                for data in changed_data:
                    slack_message += f"- {data}\n"
                slack_message += '```'
                slack(slack_message, self.slack_webhook_url)
        elif changed is True and len(changed_data) == 0:
            if self.slack_webhook_url:
                slack_message = f":warning: *{self.prefix}*\n{msg}\n"
                slack(slack_message, self.slack_webhook_url)
        else:
            self.logger.debug("no changes")
        self.logger.info(f"monitoring completed")

    def serve_forever(self, pause=60):
        slack_message = f":alert: *{self.prefix}*\nprocess started"
        slack(slack_message, self.slack_webhook_url)
        while True:
            try:
                self.monitor()
                time.sleep(pause)
            except KeyboardInterrupt:
                slack_message = f":alert: *{self.prefix}*\nprocess interrupted, exiting..."
                slack(slack_message, self.slack_webhook_url)
                break
            except Exception as e:
                self.logger.error(f"{e}", exc_info=True)
                slack_message = f":ouch: *{self.prefix}*\nerror: {e}"
                slack_message += f"\n```{traceback.format_exc()}```"
                slack(slack_message, self.slack_webhook_url)
                time.sleep(pause)
        slack_message = f":alert: *{self.prefix}*\nprocess stopped"
        slack(slack_message, self.slack_webhook_url)


class MonitorFactory(object):
    def __init__(self, monitor_class=None):
        self.monitor_class = monitor_class
        if not self.monitor_class:
            raise ValueError("monitor_class is required")
        self.name = self.monitor_class.__name__
        self.parser = argparse.ArgumentParser(description=self.name)

    def serve_forever(self):
        self.parser.add_argument("--slack_webhook_url", help="slack webhook url (default disabled)", default=None)
        self.parser.add_argument("--pause", help="pause time in seconds (default 60) between each check", type=int, default=60)
        self.args = self.parser.parse_args()
        self.slack_webhook_url = self.args.slack_webhook_url
        self.pause = self.args.pause
        self.monitor = self.monitor_class(self.slack_webhook_url, **self.kwargs)
        self.monitor.serve_forever(pause=self.pause)
        return self.monitor


if __name__ == "__main__":
    MonitorFactory(BaseMonitor).serve_forever()

