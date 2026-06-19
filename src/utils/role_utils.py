import enum


class RoleEnum(str, enum.Enum):
    """User role enumeration used across the application."""
    admin = "admin"
    user = "user"
    manager = "manager"
