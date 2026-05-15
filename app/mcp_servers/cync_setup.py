#!/usr/bin/env python3
"""
One-time Cync authentication setup.

Logs in with email/password from keychain, handles 2FA,
and caches tokens so the light server can connect without interaction.

Usage:
    1. Store credentials:
       security add-generic-password -a $(whoami) -s cync-email -w "you@email.com"
       security add-generic-password -a $(whoami) -s cync-password -w "yourpassword"

    2. Run this script:
       python mcp_servers/cync_setup.py

    3. Enter the 2FA code sent to your email when prompted.
"""

import sys
import os
import json
import asyncio
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keychain import get_secret

TOKEN_FILE = Path(__file__).parent.parent / ".cync_tokens.json"


async def main():
    import aiohttp
    from pycync import Auth, Cync
    from pycync.exceptions import TwoFactorRequiredError, AuthFailedError

    email = get_secret("cync-email")
    password = get_secret("cync-password")
    print(f"Logging in as {email}...")

    session = aiohttp.ClientSession()
    auth = Auth(session, username=email, password=password)

    try:
        await auth.login()
        print("Logged in (no 2FA needed).")
    except TwoFactorRequiredError:
        print("2FA code sent to your email.")
        code = input("Enter the 2FA code: ").strip()
        try:
            await auth.login(code)
            print("Logged in with 2FA.")
        except AuthFailedError as e:
            print(f"Authentication failed: {e}")
            await session.close()
            sys.exit(1)
    
    # Save tokens
    user = auth._user
        
    TOKEN_FILE.write_text(json.dumps({
        "access_token": user.access_token,
        "refresh_token": user.refresh_token,
        "expires_at": user.expires_at,
        "user_id": getattr(user, "user_id", ""),
        "authorize": getattr(user, "_authorize", ""),  # Add this

    }))
    print(f"Tokens saved to {TOKEN_FILE}")

    # Verify by listing devices
    cync = await Cync.create(auth)
    devices = cync.get_devices()
    print(f"\nFound {len(devices)} Cync device(s):")
    for dev in devices:
        name = dev.name
        on = getattr(dev, "is_on", "?")
        bri = getattr(dev, "brightness", "?")
        print(f"  - {name} (on={on}, brightness={bri})")

    await cync.shut_down()
    await session.close()
    print("\nSetup complete! The light server will now connect automatically.")


if __name__ == "__main__":
    asyncio.run(main())
