"""
Authentication module for Knowledge Expert.

Provides various authentication methods:
- Email/password
- Google OAuth
"""

from .google_oauth import (
    GoogleOAuth,
    get_google_oauth,
    is_google_oauth_configured
)

__all__ = [
    'GoogleOAuth',
    'get_google_oauth',
    'is_google_oauth_configured'
]
