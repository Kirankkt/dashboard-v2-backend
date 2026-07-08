import os

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from .database import engine


def _alembic_config() -> Config:
    # alembic.ini + alembic/ live at the project root (next to the app package),
    # so resolve them absolutely — the runtime CWD may differ (Railway uses /app).
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(root, "alembic"))
    return cfg


def run_migrations() -> None:
    """Bring the database schema up to date.

    Handles three cases without any manual steps:
    - Fresh database        -> upgrade head (creates all tables).
    - Pre-Alembic database  -> the prod DB was created by create_all before we
                               adopted Alembic; stamp it at head so we don't try
                               to recreate existing tables.
    - Already-managed DB    -> upgrade head (applies any pending migrations).
    """
    cfg = _alembic_config()
    insp = inspect(engine)
    if not insp.has_table("alembic_version") and insp.has_table("users"):
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")
