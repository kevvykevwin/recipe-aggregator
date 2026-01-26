#!/usr/bin/env python3
"""
One-time Instagram login to create a session file.

Run this once to authenticate, then the API will reuse the session.
This avoids logging in on every request (which triggers anti-bot detection).

Supports 2FA - will prompt for code if enabled.

Usage:
    python scripts/instagram_login.py
"""

import sys
from pathlib import Path
from getpass import getpass

sys.path.insert(0, str(Path(__file__).parent.parent))

import instaloader
from backend.services.instagram import _get_session_file

SESSION_DIR = Path(__file__).parent.parent / ".instagram_sessions"


def create_session_with_2fa(username: str, password: str) -> bool:
    """Create session with 2FA support."""
    loader = instaloader.Instaloader()

    try:
        loader.login(username, password)
    except instaloader.TwoFactorAuthRequiredException:
        print()
        print("2FA is enabled on this account.")
        code = input("Enter 2FA code from your authenticator app: ").strip()
        try:
            loader.two_factor_login(code)
        except Exception as e:
            print(f"2FA login failed: {e}")
            return False
    except instaloader.BadCredentialsException:
        print("Invalid username or password.")
        return False
    except instaloader.ConnectionException as e:
        print(f"Connection error: {e}")
        return False
    except Exception as e:
        print(f"Login failed: {e}")
        return False

    # Save session
    SESSION_DIR.mkdir(exist_ok=True)
    session_file = _get_session_file(username)
    loader.save_session_to_file(str(session_file))
    return True


def main():
    print("Instagram Session Setup")
    print("=" * 40)
    print()
    print("This will create a session file so the API")
    print("can access Instagram without logging in each time.")
    print()

    username = input("Instagram username: ").strip()
    if not username:
        print("Username required")
        sys.exit(1)

    password = getpass("Instagram password: ")
    if not password:
        print("Password required")
        sys.exit(1)

    print()
    print("Logging in...")

    if create_session_with_2fa(username, password):
        session_file = _get_session_file(username)
        print()
        print("Success! Session saved.")
        print(f"File: {session_file}")
        print()
        print("Now add to your .env:")
        print(f"  INSTAGRAM_USERNAME={username}")
        print()
        print("(Password not needed in .env - session file is used)")
    else:
        print()
        print("Login failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
