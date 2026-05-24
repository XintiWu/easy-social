from __future__ import annotations

from sqlalchemy import inspect, text

from easy_social import create_app
from easy_social.extensions import db


def _column_names(inspector, table: str) -> set[str]:
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _constraint_names(inspector, table: str) -> set[str]:
    if not inspector.has_table(table):
        return set()
    names = {item["name"] for item in inspector.get_unique_constraints(table)}
    names.update(item["name"] for item in inspector.get_check_constraints(table))
    for fk in inspector.get_foreign_keys(table):
        if fk.get("name"):
            names.add(fk["name"])
    return names


def _apply(statement: str) -> None:
    db.session.execute(text(statement))
    db.session.commit()


def migrate_poll_schema() -> None:
    inspector = inspect(db.engine)
    applied = 0

    if inspector.has_table("poll") and "created_at" not in _column_names(inspector, "poll"):
        _apply(
            "ALTER TABLE poll "
            "ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
        )
        applied += 1
        inspector = inspect(db.engine)

    if inspector.has_table("poll_option"):
        constraints = _constraint_names(inspector, "poll_option")
        if "uq_poll_option_position" not in constraints:
            _apply(
                "ALTER TABLE poll_option "
                "ADD CONSTRAINT uq_poll_option_position UNIQUE (poll_id, position)"
            )
            applied += 1
            inspector = inspect(db.engine)
            constraints = _constraint_names(inspector, "poll_option")

        if "uq_poll_option_poll_id_id" not in constraints:
            _apply(
                "ALTER TABLE poll_option "
                "ADD CONSTRAINT uq_poll_option_poll_id_id UNIQUE (poll_id, id)"
            )
            applied += 1
            inspector = inspect(db.engine)
            constraints = _constraint_names(inspector, "poll_option")

        if "ck_poll_option_position" not in constraints:
            _apply(
                "ALTER TABLE poll_option "
                "ADD CONSTRAINT ck_poll_option_position "
                "CHECK (position >= 1 AND position <= 4)"
            )
            applied += 1
            inspector = inspect(db.engine)

    if inspector.has_table("poll_vote"):
        constraints = _constraint_names(inspector, "poll_vote")
        if (
            "uq_poll_vote_one_per_user" not in constraints
            and "uq_poll_vote_once" not in constraints
        ):
            _apply(
                "ALTER TABLE poll_vote "
                "ADD CONSTRAINT uq_poll_vote_one_per_user UNIQUE (poll_id, user_id)"
            )
            applied += 1
            inspector = inspect(db.engine)
            constraints = _constraint_names(inspector, "poll_vote")

        if "poll_vote_poll_option_fkey" not in constraints:
            _apply(
                "ALTER TABLE poll_vote "
                "ADD CONSTRAINT poll_vote_poll_option_fkey "
                "FOREIGN KEY (poll_id, option_id) "
                "REFERENCES poll_option (poll_id, id)"
            )
            applied += 1

    if applied:
        print(f"Applied {applied} poll schema migration(s).")
    else:
        print("Poll schema is already up to date.")


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        migrate_poll_schema()


if __name__ == "__main__":
    main()
