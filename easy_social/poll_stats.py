from __future__ import annotations


def vote_percentage(count: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((count / total) * 100)


def build_poll_display(
    options: list,
    vote_counts: dict[int, int],
    user_voted_option_id: int | None,
) -> list[dict]:
    total = sum(vote_counts.get(option.id, 0) for option in options)
    has_votes = total > 0
    show_results = has_votes or user_voted_option_id is not None

    rows = []
    for option in options:
        count = vote_counts.get(option.id, 0)
        rows.append(
            {
                "option": option,
                "count": count,
                "percentage": vote_percentage(count, total),
                "show_results": show_results,
                "is_selected": user_voted_option_id == option.id,
            }
        )
    return rows
