"""
core/auth_tools.py — FULL
"""

import os, json, hashlib, jwt
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import serialization

# ==============================
# Path Setup
# ==============================
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
USERS_PATH = os.path.join(DATA_DIR, "users.json")
PRIVATE_KEY_PATH = os.path.join(ROOT, "private_key.pem")

# ==============================
# Helper
# ==============================
def _sha256(d: bytes): return hashlib.sha256(d).hexdigest()

def _load_user(username: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(USERS_PATH):
        return None
    with open(USERS_PATH, "r", encoding="utf-8") as f:
        users = json.load(f)
    for u in users:
        if u["username"].lower() == username.lower():
            return u
    return None

# ==============================
# Admin Validation
# ==============================
def validate_admin_login() -> bool:
    if not os.path.exists(PRIVATE_KEY_PATH):
        return False
    try:
        with open(PRIVATE_KEY_PATH, "rb") as f:
            serialization.load_pem_private_key(f.read(), password=None)
        return True
    except Exception:
        return False

# ==============================
# User Validation
# ==============================
def validate_user_login(username: str, token: Optional[str], pub_path: Optional[str]) -> Dict[str, Any]:

    user = _load_user(username)
    if not user:
        raise ValueError(f"User '{username}' tidak ditemukan.")

    if pub_path and os.path.exists(pub_path):
        with open(pub_path, "rb") as f:
            pub_bytes = f.read()
    else:
        pub_abs = os.path.join(ROOT, user["public_key_path"])
        if not os.path.exists(pub_abs):
            raise ValueError("Public key user tidak ditemukan.")
        with open(pub_abs, "rb") as f:
            pub_bytes = f.read()
    try:
        pub_obj = serialization.load_pem_public_key(pub_bytes)
    except Exception:
        raise ValueError("File public key tidak valid.")

    features = user.get("features", [])
    claims = None

    # Mode A: pakai token
    if token:
        try:
            claims = jwt.decode(token.strip(), pub_obj, algorithms=["RS256"])
            features = claims.get("features", features)
        except Exception as e:
            raise ValueError(f"Token invalid: {e}")
        return {"username": username, "features": features, "claims": claims}

    # Mode B: tanpa token → verifikasi fingerprint saja
    fp = _sha256(pub_bytes)
    if user.get("pubkey_fingerprint") != fp:
        raise ValueError("Fingerprint key tidak cocok — file bukan milik user.")
    return {"username": username, "features": features, "claims": None}
