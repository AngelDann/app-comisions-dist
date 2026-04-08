from .base import *  # noqa: F403

DEBUG = True

# Dev: allow all hosts when DEBUG (optional convenience)
if DEBUG:
    ALLOWED_HOSTS = ["*"]
