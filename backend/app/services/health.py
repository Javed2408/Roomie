"""Health-check logic."""

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def is_database_reachable(db: Session) -> bool:
    """Run the cheapest possible query to prove the database answers.

    A failure here is an expected outcome of a health check, not a crash, so
    it is logged with its full cause and reported as False rather than raised.
    """
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return False
    return True
