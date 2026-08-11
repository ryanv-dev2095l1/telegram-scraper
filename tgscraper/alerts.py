import logging
import re
import time
import httpx
from tgscraper.metrics import ALERT_TRIGGERS, ALERT_DISPATCH_FAILURES

logger = logging.getLogger(__name__)


class AlertRule:
    def __init__(self, name, pattern, webhook_url, channels=None):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.webhook_url = webhook_url
        self.channels = set(channels) if channels else None

    def matches(self, channel, text):
        if self.channels and channel not in self.channels:
            return False
        if not text:
            return False
        return bool(self.pattern.search(text))


class AlertManager:
    """Evaluates incoming messages against keyword regexes and posts alerts."""

    def __init__(self, rules=None, http_timeout=6.0, max_retries=2):
        self.rules = rules or []
        self.timeout = http_timeout
        self.max_retries = max_retries
        self._client = httpx.Client(timeout=self.timeout)

    def check_and_notify(self, message):
        channel = message.get("channel", "")
        text = message.get("text", "")
        msg_id = message.get("message_id")
        link = message.get("link", f"https://t.me/{channel}/{msg_id}")

        for rule in self.rules:
            if not rule.matches(channel, text):
                continue

            ALERT_TRIGGERS.labels(channel=channel, rule_name=rule.name).inc()
            payload = {
                "rule": rule.name,
                "channel": channel,
                "message_id": msg_id,
                "text": text,
                "link": link,
                "matched_at": int(time.time()),
            }
            self._send_webhook(rule, payload)

    def _send_webhook(self, rule, payload):
        attempts = 0
        while attempts <= self.max_retries:
            try:
                resp = self._client.post(rule.webhook_url, json=payload)
                # don't retry bad request or auth error
                if resp.status_code < 500:
                    if resp.is_error:
                        ALERT_DISPATCH_FAILURES.labels(rule_name=rule.name).inc()
                        logger.warning("webhook client error %s: %s", resp.status_code, resp.text)
                    return
                # 5xx server error, give it another shot
                attempts += 1
                if attempts <= self.max_retries:
                    time.sleep(0.5 * attempts)
            except httpx.RequestError as exc:
                attempts += 1
                if attempts <= self.max_retries:
                    time.sleep(0.5 * attempts)
                else:
                    logger.warning("failed to send webhook for rule %s: %s", rule.name, exc)
                    ALERT_DISPATCH_FAILURES.labels(rule_name=rule.name).inc()

    def close(self):
        self._client.close()
