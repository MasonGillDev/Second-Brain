"""Read secrets from the macOS Keychain (stdlib only).

A self-contained copy of app/keychain.py so the voice service has no dependency
on the dashboard package.
"""

import subprocess

_cache: dict[str, str] = {}


def get_secret(service: str) -> str:
    """Fetch a secret from macOS Keychain by service name, cached in memory."""
    if service in _cache:
        return _cache[service]

    result = subprocess.run(
        ["security", "find-generic-password", "-a", subprocess.getoutput("whoami"), "-s", service, "-w"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Keychain lookup failed for '{service}': {result.stderr.strip()}")

    _cache[service] = result.stdout.strip()
    return _cache[service]
