import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func, case, literal, tuple_
from sqlalchemy.dialects.postgresql import insert

from database import SessionLocal
from models import User, Feed, UserInteraction, CategoryPreference

logger = logging.getLogger(__name__)

# How many users to score per round trip. Keeps the IN (...) list and the
# upsert VALUES list to a sane size while still collapsing thousands of
# queries into a handful.
BATCH_SIZE = 1000

# Time constant of the interaction decay, in days. An interaction counts
# fully today, ~37% at 30 days, ~5% at 90, effectively nothing at 6 months,
# so preferences follow what a user is doing now rather than what they did
# once and moved on from.
#
# 30 is a judgement call, not a fitted value. Choosing it properly means
# holding out a later week and picking the tau that best predicts it, which
# needs real traffic.
DECAY_DAYS = 30

ACTION_WEIGHTS = {"viewed": 1, "liked": 3, "saved": 5}


def _decayed_weight():
    """weight(action) * exp(-age_in_days / DECAY_DAYS), computed in SQL."""
    weight = case(
        *[(UserInteraction.action == action, literal(w))
          for action, w in ACTION_WEIGHTS.items()],
        else_=literal(0),
    )
    age_days = (
        func.extract("epoch", func.now() - UserInteraction.created_at) / 86400.0
    )
    return func.sum(weight * func.exp(-age_days / literal(float(DECAY_DAYS))))


def recalculate_all_scores():
    """Refresh every active user's category preferences, in batches."""
    db = SessionLocal()
    total = 0
    try:
        last_id = 0
        while True:
            user_ids = [
                row[0] for row in
                db.query(User.id)
                  .filter(
                      User.is_active.is_(True),
                      User.is_blocked.is_(False),
                      User.id > last_id,
                  )
                  .order_by(User.id)
                  .limit(BATCH_SIZE)
                  .all()
            ]
            if not user_ids:
                break

            # Advance before the work, so a failing batch cannot wedge the
            # loop on the same ids forever.
            last_id = user_ids[-1]

            try:
                update_scores_for_users(user_ids, db)
                total += len(user_ids)
            except Exception:
                db.rollback()
                logger.exception(
                    "Score update failed for batch starting at %s", user_ids[0]
                )

        logger.info("Scheduler: updated %s users", total)
    finally:
        db.close()


def normalize_batch(user_ids, rows):
    """
    Turn raw (user_id, category_id, decayed_score) rows into the upsert
    VALUES list and the set of (user_id, category_id) pairs that survive
    this run.

    Split out from update_scores_for_users because it is the part where the
    correctness lives -- normalisation, the dormant-user guard, and which
    pairs escape the delete -- and it needs no session, so it can be tested
    directly. The statements around it cannot: tuple_(...).notin_() is
    PostgreSQL-only and the test database is SQLite.

    Note what this does NOT cover: the action weights and the 30-day decay
    are applied in SQL by _decayed_weight(), so `rows` arrives already
    aggregated. Those remain untested.
    """
    # user_id -> {category_id: decayed score}
    per_user = {}
    for user_id, category_id, score in rows:
        per_user.setdefault(user_id, {})[category_id] = float(score or 0.0)

    values = []
    keep = set()      # (user_id, category_id) pairs that survive this run
    for user_id in user_ids:
        scores = per_user.get(user_id, {})
        total = sum(scores.values())
        # Guard against a vanishing total: every interaction may have
        # decayed to near zero for a long-dormant user, and dividing by
        # that is meaningless. Such a user contributes nothing to `keep`,
        # so their stale preferences are deleted rather than kept at a
        # score that no longer means anything.
        if total <= 1e-9:
            continue
        for category_id, score in scores.items():
            values.append({
                "user_id": user_id,
                "category_id": category_id,
                "score": round(score / total, 4),
            })
            keep.add((user_id, category_id))

    return values, keep


def update_scores_for_users(user_ids, db):
    """
    Score a whole batch in three statements.

    The previous version ran one grouped query plus an exists-check per
    category per user. Grouping by (user_id, category_id) rather than
    category_id alone lets a single query cover the entire batch, and
    ON CONFLICT removes the lookup before each write.
    """
    rows = (
        db.query(
            UserInteraction.user_id,
            Feed.category_id,
            _decayed_weight().label("score"),
        )
        .join(Feed, Feed.id == UserInteraction.feed_id)
        .filter(UserInteraction.user_id.in_(user_ids))
        .group_by(UserInteraction.user_id, Feed.category_id)
        .all()
    )

    values, keep = normalize_batch(user_ids, rows)

    # Drop preferences with no interaction behind them any more, otherwise a
    # score survives forever after the last like is removed. Scoped to this
    # batch so it never touches users we did not just score.
    delete_q = db.query(CategoryPreference).filter(
        CategoryPreference.user_id.in_(user_ids)
    )
    if keep:
        delete_q = delete_q.filter(
            tuple_(CategoryPreference.user_id,
                   CategoryPreference.category_id).notin_(list(keep))
        )
    delete_q.delete(synchronize_session=False)

    if values:
        stmt = insert(CategoryPreference).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "category_id"],
            set_={"score": stmt.excluded.score, "updated_at": func.now()},
        )
        db.execute(stmt)

    db.commit()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        recalculate_all_scores,
        "interval",
        minutes=50,
        misfire_grace_time=300,
    )
    scheduler.start()
    logger.info("Scheduler started — recalculates every 50 minutes")
    return scheduler