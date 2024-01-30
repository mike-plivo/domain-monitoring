import traceback
import time
import json
from utils import slack, create_logger, create_redis_client, get_region, get_sensor_id

class BaseMonitor:
    def __init__(self, slack_webhook_url=None, **kwargs):
        self.class_name = self.__class__.__name__
        self.sensor_id = get_sensor_id()
        self.region = get_region()
        self.slack_webhook_url = slack_webhook_url
        self.redis_client = create_redis_client()
        self.redis_key = f'{self.class_name}:{self.sensor_id}'
        self.prefix = f"[{self.class_name}][id={self.sensor_id}][geo={self.region}]"
        self.parameters = kwargs.copy()
        for k, v in self.parameters.items():
            self.prefix += f"[{k}={v}]"
        self.logger = create_logger(self.prefix)

    def fetch_new_records(self):
        raise NotImplementedError()

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
        new_records = self.fetch_new_records()
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
        while True:
            try:
                self.monitor()
            except Exception as e:
                self.logger.error(f"{e}", exc_info=True)
                slack_message = f":ouch: *{self.prefix}*\nerror: {e}"
                slack_message += f"\n```{traceback.format_exc()}```"
                slack(slack_message, self.slack_webhook_url)
            time.sleep(pause)

def cli():
    import argparse
    parser = argparse.ArgumentParser(description='Monitor records changes')
    parser.add_argument("--slack_webhook_url", help="slack webhook url (default disabled)", default=None)
    parser.add_argument("--pause", help="pause time in seconds (default 60) between each check", type=int, default=60)
    args = parser.parse_args()
    slack_webhook_url = args.slack_webhook_url
    BaseMonitor(domain, resolvers, slack_webhook_url).serve_forever(pause=args.pause)


if __name__ == "__main__":
    cli()

