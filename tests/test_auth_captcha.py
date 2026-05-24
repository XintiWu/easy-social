from __future__ import annotations

import pytest

from easy_social.captcha import CAPTCHA_SESSION_KEY, TESTING_CAPTCHA_ANSWER
from easy_social.extensions import db
from easy_social.models import User

pytestmark = pytest.mark.integration


def test_captcha_image_route_sets_session_answer(client):
    response = client.get("/auth/captcha")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG\r\n\x1a\n")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"

    with client.session_transaction() as sess:
        assert sess[CAPTCHA_SESSION_KEY] == TESTING_CAPTCHA_ANSWER


def test_register_without_captcha_does_not_create_user(client, app):
    response = client.post(
        "/auth/register",
        data={
            "username": "bot",
            "email": "bot@example.com",
            "password": "password",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid or expired verification code." in response.data

    with app.app_context():
        assert User.query.filter_by(username="bot").first() is None


def test_register_with_wrong_captcha_does_not_create_user(client, app):
    client.get("/auth/captcha")

    response = client.post(
        "/auth/register",
        data={
            "username": "bot",
            "email": "bot@example.com",
            "password": "password",
            "captcha": "WRONG1",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid or expired verification code." in response.data

    with client.session_transaction() as sess:
        assert sess[CAPTCHA_SESSION_KEY] == TESTING_CAPTCHA_ANSWER

    with app.app_context():
        assert User.query.filter_by(username="bot").first() is None


def test_register_with_valid_captcha_creates_user(client, app):
    client.get("/auth/captcha")

    response = client.post(
        "/auth/register",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password",
            "captcha": TESTING_CAPTCHA_ANSWER,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Feed" in response.data

    with app.app_context():
        user = User.query.filter_by(username="alice").one()
        assert user.email == "alice@example.com"

    with client.session_transaction() as sess:
        assert CAPTCHA_SESSION_KEY not in sess
