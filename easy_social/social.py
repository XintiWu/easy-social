from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from .extensions import db
from .media import save_media
from .models import Comment, Poll, PollOption, PollVote, Post, User, followers
from .poll_stats import build_poll_display

bp = Blueprint("social", __name__)

POLL_PLACEHOLDER_BODY = "Poll"


def _post_query():
    return Post.query.options(
        joinedload(Post.author),
        joinedload(Post.repost_of).joinedload(Post.author),
        joinedload(Post.poll).joinedload(Poll.options),
        joinedload(Post.repost_of).joinedload(Post.poll).joinedload(Poll.options),
    )


def _comment_counts_for_posts(posts: list[Post]) -> dict[int, int]:
    post_ids = {post.display_post.id for post in posts}
    if not post_ids:
        return {}

    counts = dict.fromkeys(post_ids, 0)
    rows = (
        db.session.query(Comment.post_id, func.count(Comment.id))
        .filter(Comment.post_id.in_(post_ids))
        .group_by(Comment.post_id)
        .all()
    )
    counts.update({post_id: count for post_id, count in rows})
    return counts


def _poll_stats_for_posts(posts: list[Post]) -> dict[int, list[dict]]:
    contents: list[Post] = []
    poll_ids: list[int] = []
    for post in posts:
        content = post.display_post
        if content.poll:
            contents.append(content)
            poll_ids.append(content.poll.id)

    if not poll_ids:
        return {}

    vote_rows = (
        db.session.query(PollVote.poll_id, PollVote.option_id, func.count(PollVote.id))
        .filter(PollVote.poll_id.in_(poll_ids))
        .group_by(PollVote.poll_id, PollVote.option_id)
        .all()
    )
    counts_by_poll: dict[int, dict[int, int]] = {poll_id: {} for poll_id in poll_ids}
    for poll_id, option_id, count in vote_rows:
        counts_by_poll[poll_id][option_id] = count

    user_votes = {
        poll_id: option_id
        for poll_id, option_id in db.session.query(PollVote.poll_id, PollVote.option_id)
        .filter(
            PollVote.poll_id.in_(poll_ids),
            PollVote.user_id == current_user.id,
        )
        .all()
    }

    stats: dict[int, list[dict]] = {}
    for content in contents:
        poll = content.poll
        stats[content.id] = build_poll_display(
            poll.options,
            counts_by_poll.get(poll.id, {}),
            user_votes.get(poll.id),
        )
    return stats


def _followed_user_ids(users: list[User]) -> set[int]:
    user_ids = [user.id for user in users]
    if not user_ids:
        return set()

    return {
        followed_id
        for (followed_id,) in db.session.query(followers.c.followed_id)
        .filter(
            followers.c.follower_id == current_user.id,
            followers.c.followed_id.in_(user_ids),
        )
        .all()
    }


def _parse_poll_option_labels() -> list[str]:
    labels: list[str] = []
    for index in range(1, 5):
        label = request.form.get(f"option_{index}", "").strip()
        if label:
            labels.append(label)
    return labels


def _render_posts(
    template: str,
    posts: list[Post],
    **context,
):
    return render_template(
        template,
        posts=posts,
        comment_counts=_comment_counts_for_posts(posts),
        poll_stats=_poll_stats_for_posts(posts),
        **context,
    )


@bp.route("/")
@login_required
def feed():
    followed_ids = db.session.query(followers.c.followed_id).filter(
        followers.c.follower_id == current_user.id
    )
    posts = (
        _post_query()
        .filter(or_(Post.author_id == current_user.id, Post.author_id.in_(followed_ids)))
        .order_by(desc(Post.created_at))
        .limit(100)
        .all()
    )
    return _render_posts("social/feed.html", posts)


@bp.route("/explore")
@login_required
def explore():
    posts = _post_query().order_by(desc(Post.created_at)).limit(100).all()
    users = User.query.filter(User.id != current_user.id).order_by(User.username).limit(50).all()
    return _render_posts(
        "social/explore.html",
        posts,
        users=users,
        followed_user_ids=_followed_user_ids(users),
    )


@bp.post("/posts")
@login_required
def create_post():
    post_kind = request.form.get("post_kind", "normal").strip()
    body = request.form.get("body", "").strip()

    if post_kind == "poll":
        option_labels = _parse_poll_option_labels()
        if len(option_labels) < 2:
            flash("Poll posts need between 2 and 4 options.", "error")
            return redirect(request.referrer or url_for("social.feed"))
        if len(option_labels) > 4:
            flash("Poll posts can have at most 4 options.", "error")
            return redirect(request.referrer or url_for("social.feed"))

        post = Post(
            body=body or POLL_PLACEHOLDER_BODY,
            author=current_user,
        )
        poll = Poll(post=post)
        for position, label in enumerate(option_labels, start=1):
            poll.options.append(PollOption(label=label, position=position))
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("social.feed"))

    try:
        media_filename, media_type = save_media(request.files.get("media"))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("social.feed"))

    if not body and not media_filename:
        flash("Add text, an image, or a video before posting.", "error")
        return redirect(request.referrer or url_for("social.feed"))

    post = Post(
        body=body,
        media_filename=media_filename,
        media_type=media_type,
        author=current_user,
    )
    db.session.add(post)
    db.session.commit()
    return redirect(url_for("social.feed"))


@bp.get("/posts/<int:post_id>")
@login_required
def post_detail(post_id: int):
    post = _post_query().filter(Post.id == post_id).first_or_404()
    comments = post.comments.order_by(Comment.created_at.asc()).all()
    poll_stats = _poll_stats_for_posts([post])
    return render_template(
        "social/post_detail.html",
        post=post,
        comments=comments,
        comment_counts={post.display_post.id: len(comments)},
        poll_stats=poll_stats,
    )


@bp.post("/posts/<int:post_id>/vote")
@login_required
def vote_post(post_id: int):
    post = _post_query().filter(Post.id == post_id).first_or_404()
    content = post.display_post
    poll = content.poll
    if poll is None:
        flash("This post is not a poll.", "error")
        return redirect(request.referrer or url_for("social.feed"))

    if content.author_id == current_user.id:
        flash("You cannot vote on your own poll.", "error")
        return redirect(request.referrer or url_for("social.post_detail", post_id=post.id))

    option_id = request.form.get("option_id", type=int)
    option = PollOption.query.filter_by(id=option_id, poll_id=poll.id).first()
    if option is None:
        flash("Invalid poll option.", "error")
        return redirect(request.referrer or url_for("social.post_detail", post_id=post.id))

    if poll.user_vote(current_user.id) is not None:
        flash("You already voted on this poll.", "error")
        return redirect(request.referrer or url_for("social.post_detail", post_id=post.id))

    db.session.add(PollVote(poll=poll, option=option, user=current_user))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("You already voted on this poll.", "error")

    return redirect(request.referrer or url_for("social.post_detail", post_id=post.id))


@bp.post("/posts/<int:post_id>/comments")
@login_required
def add_comment(post_id: int):
    post = db.get_or_404(Post, post_id)
    body = request.form.get("body", "").strip()
    if not body:
        flash("Comment cannot be empty.", "error")
    else:
        db.session.add(Comment(body=body, author=current_user, post=post))
        db.session.commit()
    return redirect(url_for("social.post_detail", post_id=post.id))


@bp.post("/posts/<int:post_id>/repost")
@login_required
def repost(post_id: int):
    original = db.get_or_404(Post, post_id).display_post
    if original.author_id == current_user.id:
        flash("You cannot repost your own post.", "error")
        return redirect(request.referrer or url_for("social.feed"))

    existing = Post.query.filter_by(author_id=current_user.id, repost_of_id=original.id).first()
    if existing:
        flash("You already reposted this.", "error")
        return redirect(request.referrer or url_for("social.feed"))

    db.session.add(Post(author=current_user, repost_of=original))
    db.session.commit()
    return redirect(request.referrer or url_for("social.feed"))


@bp.route("/users/<username>")
@login_required
def profile(username: str):
    user = User.query.filter_by(username=username).first_or_404()
    posts = (
        _post_query()
        .filter(Post.author_id == user.id)
        .order_by(desc(Post.created_at))
        .all()
    )
    return _render_posts(
        "social/profile.html",
        posts,
        profile_user=user,
    )


@bp.post("/users/<username>/follow")
@login_required
def follow(username: str):
    user = User.query.filter_by(username=username).first_or_404()
    current_user.follow(user)
    db.session.commit()
    return redirect(request.referrer or url_for("social.profile", username=user.username))


@bp.post("/users/<username>/unfollow")
@login_required
def unfollow(username: str):
    user = User.query.filter_by(username=username).first_or_404()
    current_user.unfollow(user)
    db.session.commit()
    return redirect(request.referrer or url_for("social.profile", username=user.username))
