from src.database.base import Base, engine


def create_all_tables() -> None:
    """
    Import all models so SQLAlchemy is aware of them, then create all tables.
    Called once at application startup.
    """
    # Import models to register them with Base.metadata
    import src.models.users          # noqa: F401
    import src.models.session        # noqa: F401
    import src.models.messege        # noqa: F401
    import src.models.invoice        # noqa: F401
    import src.models.workflow_run   # noqa: F401
    import src.models.tool_call_log  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("[DB] All tables created / verified.")
