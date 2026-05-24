from __future__ import annotations

import pytest

from easy_social.poll_stats import build_poll_display, vote_percentage

pytestmark = pytest.mark.unit


class _Option:
    def __init__(self, option_id: int):
        self.id = option_id


def test_vote_percentage_with_zero_total():
    assert vote_percentage(0, 0) == 0
    assert vote_percentage(3, 0) == 0


def test_vote_percentage_rounds_to_nearest_integer():
    assert vote_percentage(1, 3) == 33
    assert vote_percentage(2, 3) == 67


def test_build_poll_display_before_any_votes():
    options = [_Option(1), _Option(2)]
    rows = build_poll_display(options, {}, None)

    assert len(rows) == 2
    assert rows[0]["show_results"] is False
    assert rows[0]["percentage"] == 0


def test_build_poll_display_after_user_votes():
    options = [_Option(1), _Option(2)]
    rows = build_poll_display(options, {1: 1}, 1)

    assert rows[0]["show_results"] is True
    assert rows[0]["percentage"] == 100
    assert rows[0]["is_selected"] is True
    assert rows[1]["percentage"] == 0
