import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings

SCHEMA = "langgraph"
_checkpointer: PostgresSaver | None = None

def _conninfo() -> str:
    # SQLAlchemy URLs say "postgresql+psycopg://", plain psycopg wants "postgresql://"
    return get_settings().database_url.replace("postgresql+psycopg://", "postgresql://", 1)

def get_checkpointer() -> PostgresSaver:
    global _checkpointer
    if _checkpointer is None:
        with psycopg.connect(_conninfo(), autocommit=True) as conn:
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

        pool = ConnectionPool(
            conninfo=_conninfo(),
            max_size=10,
            open=True,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
                "options": f"-c search_path={SCHEMA}",
            },
        )
        saver = PostgresSaver(pool)
        saver.setup()
        _checkpointer = saver
    return _checkpointer