"""
Google OAuth Authentication for Knowledge Expert.

Provides Google Sign-In functionality for user authentication.

Setup:
1. Go to https://console.cloud.google.com/
2. Create a new project or select existing
3. Enable Google+ API
4. Go to Credentials > Create Credentials > OAuth 2.0 Client ID
5. Set authorized redirect URI to: https://your-domain.com/auth/google/callback
6. Set environment variables:
   - GOOGLE_CLIENT_ID
   - GOOGLE_CLIENT_SECRET
"""

import json
import logging
import os
import secrets
from typing import Optional, Dict, Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Scopes we need
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile"
]


class GoogleOAuth:
    """
    Google OAuth 2.0 authentication handler.
    """

    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.environ.get("GOOGLE_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("GOOGLE_CLIENT_SECRET")

    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured."""
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """
        Get the Google authorization URL.

        Args:
            redirect_uri: The callback URL
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "select_account"  # Always show account chooser
        }

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            redirect_uri: The same redirect URI used in authorization

        Returns:
            Token response dict or None on error
        """
        try:
            import requests

            response = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Token exchange failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user info from Google.

        Args:
            access_token: OAuth access token

        Returns:
            User info dict with id, email, name, picture, etc.
        """
        try:
            import requests

            response = requests.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"User info request failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"User info error: {e}")
            return None

    def authenticate(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """
        Full authentication flow: exchange code and get user info.

        Args:
            code: Authorization code from callback
            redirect_uri: Callback URI

        Returns:
            User info dict or None on error
        """
        tokens = self.exchange_code(code, redirect_uri)
        if not tokens:
            return None

        access_token = tokens.get("access_token")
        if not access_token:
            logger.error("No access token in response")
            return None

        user_info = self.get_user_info(access_token)
        if user_info:
            # Add tokens to user info for potential future use
            user_info["_tokens"] = {
                "access_token": access_token,
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens.get("expires_in")
            }

        return user_info


# Global instance
_google_oauth: Optional[GoogleOAuth] = None


def get_google_oauth() -> GoogleOAuth:
    """Get or create the global Google OAuth instance."""
    global _google_oauth

    if _google_oauth is None:
        _google_oauth = GoogleOAuth()

    return _google_oauth


def is_google_oauth_configured() -> bool:
    """Check if Google OAuth is configured."""
    return get_google_oauth().is_configured()
