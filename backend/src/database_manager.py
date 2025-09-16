"""
Database connection manager for System Builder Hub
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

logger = logging.getLogger(__name__)

ENGINE = None
Session = None

def init_engine(database_url: str):
    global ENGINE, Session
    if ENGINE is None:
        ENGINE = create_engine(
            database_url,
            pool_pre_ping=True,
            future=True,
        )
        Session = scoped_session(sessionmaker(
            bind=ENGINE,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,   # ← important: no detached surprises after commit
        ))
    return ENGINE

def get_current_session():
    # Returns the thread/greenlet-local Session for this request
    return Session()

def remove_current_session():
    # Called at teardown to clear the scoped registry
    if Session is not None:
        Session.remove()