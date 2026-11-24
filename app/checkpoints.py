from flask_imp.security import SessionCheckpoint

LOGIN_REQUIRED = SessionCheckpoint("logged_in", True).action(
    fail_json={
        "status": "unauthorized",
        "message": "You need to be logged in.",
    },
    fail_status=401,
)

__all__ = ["LOGIN_REQUIRED"]
