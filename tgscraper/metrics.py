from prometheus_client import Counter, Histogram

SCRAPE_DURATION = Histogram(
    "tgscraper_scrape_duration_seconds",
    "Time spent fetching and parsing channel preview pages",
    ["channel"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

MESSAGES_SCRAPED = Counter(
    "tgscraper_messages_scraped_total",
    "Total preview messages extracted from telegram html",
    ["channel"],
)

SCRAPE_ERRORS = Counter(
    "tgscraper_scrape_errors_total",
    "Count of scrape failures by stage",
    ["channel", "stage"],
)

ALERT_TRIGGERS = Counter(
    "tgscraper_keyword_alerts_total",
    "Number of keyword rule matches triggered on new posts",
    ["channel", "rule_name"],
)

ALERT_DISPATCH_FAILURES = Counter(
    "tgscraper_alert_dispatch_failures_total",
    "Failed webhook alerts by rule",
    ["rule_name"],
)
