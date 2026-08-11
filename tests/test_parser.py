import pytest
from datetime import datetime, timezone
from tgscraper.parser import parse_channel_page, extract_views, parse_single_message


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="tgme_widget_message_wrap js-widget_message_wrap">
  <div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="testchan/101">
    <div class="tgme_widget_message_text js-message_text" dir="auto">Hello world! Visit https://example.com for info.</div>
    <div class="tgme_widget_message_footer js-message_footer">
      <div class="tgme_widget_message_info">
        <span class="tgme_widget_message_views">1.2K</span>
        <span class="tgme_widget_message_meta">
          <a class="tgme_widget_message_date" href="https://t.me/testchan/101"><time datetime="2023-11-01T14:30:00+00:00">14:30</time></a>
        </span>
      </div>
    </div>
  </div>
</div>
<div class="tgme_widget_message_wrap js-widget_message_wrap">
  <div class="tgme_widget_message text_not_supported_wrap js-widget_message" data-post="testchan/102">
    <div class="tgme_widget_message_forwarded_from">
      <span class="tgme_widget_message_forwarded_from_name">Forwarded from <a href="https://t.me/source_feed">Source Channel</a></span>
    </div>
    <div class="tgme_widget_message_text js-message_text" dir="auto">Breaking news alert!</div>
    <div class="tgme_widget_message_footer js-message_footer">
      <div class="tgme_widget_message_info">
        <span class="tgme_widget_message_views">15.4K</span>
        <span class="tgme_widget_message_meta">
          <a class="tgme_widget_message_date" href="https://t.me/testchan/102"><time datetime="2023-11-01T15:00:00+00:00">15:00</time></a>
        </span>
      </div>
    </div>
  </div>
</div>
<div class="tgme_widget_message_wrap js-widget_message_wrap">
  <!-- service message or poll with no text wrapper -->
  <div class="tgme_widget_message js-widget_message service_message" data-post="testchan/103">
    <div class="tgme_widget_message_footer js-message_footer">
      <div class="tgme_widget_message_info">
        <span class="tgme_widget_message_meta">
          <a class="tgme_widget_message_date" href="https://t.me/testchan/103"><time datetime="2023-11-01T16:00:00+00:00">16:00</time></a>
        </span>
      </div>
    </div>
  </div>
</div>
</body>
</html>
"""


def test_extract_views():
    assert extract_views("1.2K") == 1200
    assert extract_views("450") == 450
    assert extract_views("2.5M") == 2500000
    assert extract_views("10.1K") == 10100
    assert extract_views("invalid") is None
    assert extract_views("") is None
    assert extract_views(None) is None


def test_parse_channel_page_with_forwards():
    posts = parse_channel_page(SAMPLE_HTML, channel="testchan")
    # Post 103 is a service message without text/media, should still parse with empty text
    assert len(posts) == 3

    first = posts[0]
    assert first.channel == "testchan"
    assert first.post_id == 101
    assert "Hello world!" in first.text
    assert first.views == 1200
    assert first.forwarded_from is None

    second = posts[1]
    assert second.post_id == 102
    assert second.views == 15400
    assert second.forwarded_from == "Source Channel"
    assert second.text == "Breaking news alert!"

    third = posts[2]
    assert third.post_id == 103
    assert third.text == ""
    assert third.views is None


def test_photo_caption_parsing():
    snippet = """
    <div class="tgme_widget_message js-widget_message" data-post="photochan/55">
      <div class="tgme_widget_message_photo_wrap" style="background-image:url('https://cdn4.telesco.pe/file/123.jpg')"></div>
      <div class="tgme_widget_message_text js-message_text" dir="auto">Look at this chart: <b>growth</b></div>
      <div class="tgme_widget_message_footer">
        <div class="tgme_widget_message_info">
          <span class="tgme_widget_message_views">890</span>
          <span class="tgme_widget_message_meta">
            <a class="tgme_widget_message_date" href="https://t.me/photochan/55"><time datetime="2023-11-02T10:00:00+00:00">10:00</time></a>
          </span>
        </div>
      </div>
    </div>
    """
    # print("debugging raw snippet", snippet)
    post = parse_single_message(snippet, default_channel="photochan")
    assert post is not None
    assert post.post_id == 55
    assert post.has_media is True
    assert "Look at this chart: growth" in post.text


def test_empty_page():
    posts = parse_channel_page("<html><body><div>No posts here</div></body></html>", channel="empty")
    assert posts == []
