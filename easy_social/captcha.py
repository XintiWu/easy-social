from __future__ import annotations

import random
import secrets
from io import BytesIO

from flask import session
from PIL import Image, ImageDraw

CAPTCHA_SESSION_KEY = "captcha_answer"
TESTING_CAPTCHA_ANSWER = "TEST12"
CAPTCHA_CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_captcha_text(length: int = 6) -> str:
    if _testing_mode():
        return TESTING_CAPTCHA_ANSWER
    return "".join(secrets.choice(CAPTCHA_CHARSET) for _ in range(length))


def render_captcha_image(text: str) -> bytes:
    width, height = 180, 60
    image = Image.new("RGB", (width, height), color=(247, 247, 244))
    draw = ImageDraw.Draw(image)

    for _ in range(6):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        draw.line([start, end], fill=(200, 210, 220), width=1)

    draw.text((20, 18), text, fill=(28, 35, 43))

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def set_captcha_answer(sess, text: str) -> None:
    sess[CAPTCHA_SESSION_KEY] = text.upper()


def verify_and_clear_captcha(sess, user_input: str) -> bool:
    expected = sess.get(CAPTCHA_SESSION_KEY)
    if not expected or not user_input:
        return False
    if user_input.strip().upper() != expected:
        return False
    sess.pop(CAPTCHA_SESSION_KEY, None)
    return True


def _testing_mode() -> bool:
    from flask import current_app, has_app_context

    if not has_app_context():
        return False
    return bool(current_app.config.get("TESTING"))
