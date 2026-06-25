from src.database.base import Base, engine, SessionLocal


def seed_default_user() -> None:
    """Ensure a default user exists for chat session creation."""
    import src.models  # noqa: F401
    from src.models.users import User

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(
                User(
                    name="Default User",
                    email="default@local",
                    password_hash="not-used",
                    role="user",
                )
            )
            db.commit()
            print("[DB] Seeded default user (id=1).")
    finally:
        db.close()


def _migrate_chat_sessions_to_uuid() -> None:
    """Recreate chat tables when upgrading from integer session IDs."""
    from sqlalchemy import inspect

    import src.models  # noqa: F401
    from src.models.messege import Message
    from src.models.session import ChatSession

    inspector = inspect(engine)
    if "chat_sessions" not in inspector.get_table_names():
        return

    id_col = next(
        (c for c in inspector.get_columns("chat_sessions") if c["name"] == "id"),
        None,
    )
    if id_col is None or "INT" not in str(id_col["type"]).upper():
        return

    Message.__table__.drop(engine, checkfirst=True)
    ChatSession.__table__.drop(engine, checkfirst=True)
    print("[DB] Recreating chat tables with UUID session IDs.")


def create_all_tables() -> None:
    """
    Import all models so SQLAlchemy is aware of them, then create all tables.
    Called once at application startup.
    """
    import src.models  # noqa: F401

    _migrate_chat_sessions_to_uuid()
    Base.metadata.create_all(bind=engine)
    seed_default_user()
    print("[DB] All tables created / verified.")
