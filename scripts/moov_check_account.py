"""
Moov Sandbox Account Check
--------------------------
Fetches an OAuth2 access token using HTTP Basic auth (public/private key pair),
then retrieves basic account info and capabilities for the configured account ID.

Required environment variables:
  MOOV_PUBLIC_KEY   – Moov API public key
  MOOV_PRIVATE_KEY  – Moov API private key
  MOOV_ACCOUNT_ID   – Moov account UUID to inspect

Optional environment variables:
  MOOV_BASE_URL  – defaults to https://api.sandbox.moov.io
  MOOV_VERSION   – defaults to v2026.01.00
  MOOV_SCOPES    – space-separated OAuth scopes (defaults to /accounts.read /capabilities.read)

The script never prints the access token or the raw credentials.
"""

import os
import sys
import requests

BASE_URL = os.environ.get("MOOV_BASE_URL", "https://api.sandbox.moov.io").rstrip("/")
VERSION = os.environ.get("MOOV_VERSION", "v2026.01.00")
SCOPES = os.environ.get("MOOV_SCOPES", "/accounts.read /capabilities.read")


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: required environment variable {name!r} is not set.", file=sys.stderr)
        sys.exit(1)
    return value


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "x-moov-version": VERSION,
        "Content-Type": "application/json",
    }


def get_access_token(public_key: str, private_key: str) -> str:
    """Request an OAuth2 access token using client_credentials grant."""
    url = f"{BASE_URL}/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "scope": SCOPES,
    }
    try:
        response = requests.post(
            url,
            auth=(public_key, private_key),
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"ERROR: token request failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if not response.ok:
        print(
            f"ERROR: token endpoint returned HTTP {response.status_code}:\n{response.text}",
            file=sys.stderr,
        )
        sys.exit(1)

    token = response.json().get("access_token")
    if not token:
        print("ERROR: no access_token in response.", file=sys.stderr)
        sys.exit(1)

    print("✓ Access token obtained (not printed).")
    return token


def _redact_account(data: dict) -> dict:
    """Return a copy of the account dict with sensitive fields redacted."""
    redacted = dict(data)
    for field in ("taxID", "ssn", "ein", "foreignID"):
        if field in redacted:
            redacted[field] = "***REDACTED***"
    return redacted


def get_account(token: str, account_id: str) -> None:
    """Fetch and print a summary of the Moov account."""
    url = f"{BASE_URL}/accounts/{account_id}"
    try:
        response = requests.get(url, headers=_headers(token), timeout=30)
    except requests.RequestException as exc:
        print(f"ERROR: GET account failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if not response.ok:
        print(
            f"ERROR: GET /accounts/{account_id} returned HTTP {response.status_code}:\n{response.text}",
            file=sys.stderr,
        )
        sys.exit(1)

    account = _redact_account(response.json())
    print("\n=== Account ===")
    print(f"  accountID   : {account.get('accountID', 'n/a')}")
    print(f"  displayName : {account.get('displayName', 'n/a')}")
    print(f"  accountType : {account.get('accountType', 'n/a')}")
    print(f"  mode        : {account.get('mode', 'n/a')}")
    print(f"  createdOn   : {account.get('createdOn', 'n/a')}")
    print(f"  updatedOn   : {account.get('updatedOn', 'n/a')}")


def get_capabilities(token: str, account_id: str) -> None:
    """Fetch and print the capabilities for the Moov account."""
    url = f"{BASE_URL}/accounts/{account_id}/capabilities"
    try:
        response = requests.get(url, headers=_headers(token), timeout=30)
    except requests.RequestException as exc:
        print(f"ERROR: GET capabilities failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if not response.ok:
        print(
            f"ERROR: GET /accounts/{account_id}/capabilities returned HTTP {response.status_code}:\n{response.text}",
            file=sys.stderr,
        )
        sys.exit(1)

    capabilities = response.json()
    print("\n=== Capabilities ===")
    if not capabilities:
        print("  (none returned)")
        return
    for cap in capabilities:
        name = cap.get("capability", "unknown")
        status = cap.get("status", "unknown")
        print(f"  {name}: {status}")


def main() -> None:
    public_key = _require_env("MOOV_PUBLIC_KEY")
    private_key = _require_env("MOOV_PRIVATE_KEY")
    account_id = _require_env("MOOV_ACCOUNT_ID")

    print(f"Target account : {account_id}")
    print(f"Base URL       : {BASE_URL}")
    print(f"API version    : {VERSION}")
    print(f"Scopes         : {SCOPES}")
    print()

    token = get_access_token(public_key, private_key)
    get_account(token, account_id)
    get_capabilities(token, account_id)

    print("\nDone.")


if __name__ == "__main__":
    main()
