"""Keycloak authentication utilities for ETL."""
from __future__ import annotations

from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakError


class KeycloakAuthenticator:
    """Authenticates users against Keycloak server."""

    def __init__(self, server_url: str, client_id: str, realm_name: str):
        """Initialize Keycloak connection.

        Args:
            server_url: Keycloak server URL (e.g., https://keycloak.example.com/auth/)
            client_id: Client ID configured in Keycloak
            realm_name: Realm name in Keycloak
        """
        self.server_url = server_url
        self.client_id = client_id
        self.realm_name = realm_name
        self._keycloak = None

    @property
    def keycloak(self) -> KeycloakOpenID:
        """Lazy-load Keycloak connection."""
        if self._keycloak is None:
            self._keycloak = KeycloakOpenID(
                server_url=self.server_url,
                client_id=self.client_id,
                realm_name=self.realm_name,
            )
        return self._keycloak

    def authenticate(self, username: str, password: str) -> dict | None:
        """Validate credentials against Keycloak.

        Args:
            username: Username
            password: Password

        Returns:
            Dictionary with user info if valid, None otherwise.
            Structure: {
                'username': str,
                'email': str,
                'first_name': str,
                'last_name': str,
            }
        """
        try:
            token = self.keycloak.token(username, password)
            userinfo = self.keycloak.userinfo(token['access_token'])

            return {
                'username': userinfo.get('preferred_username', ''),
                'email': userinfo.get('email', ''),
                'first_name': userinfo.get('given_name', ''),
                'last_name': userinfo.get('family_name', ''),
            }
        except KeycloakError as e:
            return None
        except Exception as e:
            return None
