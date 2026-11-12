"""Store the local demo credential in the macOS login Keychain."""

import re
import subprocess
import sys


SERVICE = "FreshWise Gemini API"
ACCOUNT = "freshwise"


def normalize_gemini_key(value):
    key = re.sub(r"^(?:export\s+)?(?:GEMINI_API_KEY|GOOGLE_API_KEY)\s*=\s*", "", value.strip())
    if len(key) >= 2 and (key[0], key[-1]) in {('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’")}:
        key = key[1:-1].strip()
    if not re.fullmatch(r"[!-~]+", key):
        raise ValueError("In Google AI Studio, use Copy API key and paste it here.")
    return key


def read_gemini_key():
    if sys.platform != "darwin":
        return ""
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", SERVICE, "-a", ACCOUNT, "-w"],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def save_gemini_key(key):
    if sys.platform != "darwin":
        raise ValueError("Keychain storage is available on macOS.")
    key = normalize_gemini_key(key)
    encoded = key.encode("utf-8").hex()
    # Use security's interactive stdin so the key stays out of the process arguments.
    subprocess.run(
        ["/usr/bin/security", "-i"],
        input=f'add-generic-password -U -a {ACCOUNT} -s "{SERVICE}" -X {encoded}\n',
        capture_output=True, text=True, check=False,
    )
    if read_gemini_key() != key:
        raise ValueError("The key could not be saved in Keychain.")
    return key
