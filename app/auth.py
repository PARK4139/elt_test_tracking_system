from typing import Annotated

from fastapi import Header, HTTPException, status


ROLE_TESTER = "tester"
ROLE_ADMIN = "admin"
ROLE_MASTER_ADMIN = "master_admin"


def get_current_role_name(x_user_role: Annotated[str | None, Header()] = None) -> str:
    if x_user_role is None:
        return ROLE_TESTER
    return x_user_role


def ensure_role_allowed(current_role_name: str, allowed_role_names: set[str]) -> None:
    if current_role_name not in allowed_role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This role is not allowed for this action.",
        )


def concurrency_limit_guard_placeholder() -> None:
    # Placeholder for future active user concurrency guard (>5 users).
    return None

