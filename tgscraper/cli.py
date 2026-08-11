import argparse
import logging
import random
import signal
import sys
import time
from prometheus_client import start_http_server
from tgscraper.alerts import KeywordAlertEngine
from tgscraper.metrics import SCRAPE_ERRORS, SCRAPE_TOTAL, NEW_MESSAGES
from tgscraper.parser import ChannelScraper
from tgscraper.storage import MessageStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("tgscraper.cli")

running = True

def _sig_handler(signum, frame):
    global running
    log.info("Received stop signal (%s), shutting down cleanly...", signum)
    running = False

def parse_args():
    p = argparse.ArgumentParser(description="Telegram preview scraper daemon")
    p.add_argument("-c", "--channels", nargs="+", required=True, help="Channel usernames without @")
    p.add_argument("--db", default="tgscraper.db", help="Path to SQLite database")
    p.add_argument("--interval", type=int, default=120, help="Base scrape interval in seconds")
    p.add_argument("--metrics-port", type=int, default=9108, help="Prometheus metrics port (0 to disable)")
    p.add_argument("-k", "--keywords", nargs="*", default=[], help="Keywords to track for prometheus alerts")
    p.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return p.parse_args()

def main():
    global running
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    if args.metrics_port > 0:
        try:
            start_http_server(args.metrics_port)
            log.info("Prometheus metrics exposed on :%d", args.metrics_port)
        except Exception as err:
            log.error("could not start metrics server: %s", err)
            return 1

    store = MessageStore(args.db)
    scraper = ChannelScraper()
    alert_engine = KeywordAlertEngine(args.keywords) if args.keywords else None

    # Early check so we fail fast before entering the infinite loop
    chan_list = [c.lstrip("@").strip() for c in args.channels if c.strip()]
    if not chan_list:
        log.error("No valid channels specified")
        return 1

    log.info("Daemon started. Tracking channels: %s (interval: %ds)", ", ".join(chan_list), args.interval)

    while running:
        loop_start = time.monotonic()

        for ch in chan_list:
            if not running:
                break

            SCRAPE_TOTAL.labels(channel=ch).inc()
            try:
                messages = scraper.get_messages(ch)
                new_count = 0
                for msg in messages:
                    # print(f"[DEBUG] raw msg id: {msg.get('msg_id')} text len: {len(msg.get('text', ''))}")
                    if store.save_message(msg):
                        new_count += 1
                        if alert_engine:
                            alert_engine.inspect(msg)

                NEW_MESSAGES.labels(channel=ch).inc(new_count)
                log.info("channel=%s scraped=%d new=%d", ch, len(messages), new_count)
            except Exception as e:
                SCRAPE_ERRORS.labels(channel=ch).inc()
                # TODO: telegram sometimes gives 429 html page without retry-after header
                log.warning("failed to scrape %s: %s", ch, e)

            # small jitter between channels to avoid looking like a synchronous burst
            time.sleep(random.uniform(1.2, 3.0))

        elapsed = time.monotonic() - loop_start
        sleep_time = max(0.0, args.interval - elapsed)

        # Sleep in tiny slices so SIGINT responds immediately
        wake_up_at = time.monotonic() + sleep_time
        while running and time.monotonic() < wake_up_at:
            time.sleep(0.5)

    log.info("Scraper daemon stopped.")
    return 0
