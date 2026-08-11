import re
from bs4 import BeautifulSoup


def clean_preview_text(elem):
    if not elem:
        return ""
    for br in elem.find_all("br"):
        br.replace_with("\n")
    return elem.get_text().strip()


def extract_messages(html_content, channel_name):
    """Extracts message dictionaries from a t.me/s/<channel> HTML preview page."""
    soup = BeautifulSoup(html_content, "html.parser")
    cards = soup.find_all("div", class_="tgme_widget_message")
    results = []

    for card in cards:
        post_attr = card.get("data-post")
        if not post_attr:
            # sometimes telegram embeds media group children with wrap classes only
            continue

        # data-post can look like 'channel/123' or have custom slug prefixes
        match = re.search(r"/(\d+)$", post_attr)
        if not match:
            continue
        msg_id = int(match.group(1))

        text_elem = card.find("div", class_="tgme_widget_message_text")
        text = clean_preview_text(text_elem)

        time_elem = card.find("time")
        msg_datetime = ""
        if time_elem and time_elem.has_attr("datetime"):
            msg_datetime = time_elem["datetime"]

        views_elem = card.find("span", class_="tgme_widget_message_views")
        views = views_elem.text.strip() if views_elem else None

        # check forwarded from header
        fwd_elem = card.find("a", class_="tgme_widget_message_forwarded_from_name")
        forwarded_from = fwd_elem.text.strip() if fwd_elem else None

        has_photo = bool(card.find("a", class_="tgme_widget_message_photo_wrap"))
        has_video = bool(card.find("i", class_="tgme_widget_message_video_thumb") or card.find("video"))
        has_document = bool(card.find("div", class_="tgme_widget_message_document"))

        # TODO: handle poll options extraction when telegram switches markup again
        is_poll = bool(card.find("div", class_="tgme_widget_message_poll"))

        # print(f"DEBUG raw wrap: {post_attr}")

        # check edited mark
        is_edited = bool(card.find("span", class_="tgme_widget_message_edited"))

        results.append({
            "channel": channel_name,
            "message_id": msg_id,
            "datetime": msg_datetime,
            "text": text,
            "views": views,
            "forwarded_from": forwarded_from,
            "is_edited": is_edited,
            "has_media": has_photo or has_video or has_document or is_poll,
            "raw_html": str(card),
        })

    return results
