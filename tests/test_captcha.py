from __future__ import annotations

import pytest

from easy_social import create_app
from easy_social.captcha import (
    CAPTCHA_CHARSET,
    CAPTCHA_SESSION_KEY,
    TESTING_CAPTCHA_ANSWER,
    generate_captcha_text,
    render_captcha_image,
    set_captcha_answer,
    verify_and_clear_captcha,
)

pytestmark = pytest.mark.unit


def test_generate_captcha_text_uses_expected_charset():
    app = create_app({"SECRET_KEY": "test", "TESTING": False})
    with app.app_context():
        text = generate_captcha_text(length=8)

    assert len(text) == 8
    assert all(character in CAPTCHA_CHARSET for character in text)


def test_generate_captcha_text_is_fixed_in_testing_mode(app):
    with app.app_context():
        assert generate_captcha_text() == TESTING_CAPTCHA_ANSWER


def test_render_captcha_image_returns_png_bytes():
    image_bytes = render_captcha_image("ABC123")

    assert image_bytes
    assert image_bytes.startswith(b"\x89PNG\r\n\x1a\n")


def test_verify_and_clear_captcha_accepts_case_insensitive_match():
    sess = {CAPTCHA_SESSION_KEY: "ABC123"}

    assert verify_and_clear_captcha(sess, "abc123") is True
    assert CAPTCHA_SESSION_KEY not in sess


def test_verify_and_clear_captcha_rejects_wrong_or_missing_values():
    sess = {CAPTCHA_SESSION_KEY: "ABC123"}

    assert verify_and_clear_captcha(sess, "WRONG1") is False
    assert CAPTCHA_SESSION_KEY not in sess

    assert verify_and_clear_captcha({}, "ABC123") is False


def test_set_captcha_answer_normalizes_to_uppercase():
    sess = {}
    set_captcha_answer(sess, "abc123")

    assert sess[CAPTCHA_SESSION_KEY] == "ABC123"
