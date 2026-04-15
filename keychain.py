"""
Retrieve secrets from macOS Keychain — nothing stored on disk.

Usage:
    from keychain import get_secret
    key = get_secret("anthropic-api-key")
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
