# telegram-scraper

Lightweight scraper for public Telegram channels. Uses the `t.me/s/<channel>` web preview endpoints so you don't need API keys, phone sessions, or bot tokens. Stores seen messages in SQLite, runs regex matches for alerts, and exposes Prometheus metrics.

I built this to monitor a handful of infra status channels and regional outage feeds without keeping a full Telethon client running.

## Requirements

- Python 3.10+
- SQLite 3

## Install

```bash
git clone https://github.com/user/telegram-scraper.git
cd telegram-scraper
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

Basic run watching two channels every 60 seconds:

```bash
python -m tgscraper run --channels cloudflare_status,hetzner_status --interval 60 --db ./data/tg.db
```

With Prometheus metrics and webhook alerts:

```bash
python -m tgscraper run \
  --channels cloudflare_status \
  --metrics-port 9108 \
  --webhook-url http://localhost:9090/webhook \
  --keywords "outage,degraded,incident"
```

Export stored messages to JSON lines:

```bash
python -m tgscraper export --db ./data/tg.db --channel cloudflare_status --output dump.jsonl
```

## Limitations

- Only works for public channels that have web previews enabled.
- Rate limits happen if you scrape too aggressively. Default interval is 60s per channel which hasn't triggered IP blocks for me.

## License

MIT
