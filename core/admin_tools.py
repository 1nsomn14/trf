"""
core/admin_tools.py — FULL
Feature-gating ready: generate user + keypair + token + editable features
"""

import os, json, uuid, datetime as dt, hashlib, jwt
from typing import List, Optional, Dict, Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# ==============================
# Path Setup
# ==============================
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
KEYS_DIR = os.path.join(ASSETS, "keys")
DATA_DIR = os.path.join(ROOT, "data")
LOGS_DIR = os.path.join(ROOT, "logs")

PRIVATE_KEY_PATH = os.path.join(ROOT, "private_key.pem")
USERS_PATH = os.path.join(DATA_DIR, "users.json")
LICENSE_LOG_PATH = os.path.join(LOGS_DIR, "licenses.log")

os.makedirs(KEYS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ==============================
# Helpers
# ==============================
def ensure_paths():
    os.makedirs(KEYS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _load_users() -> List[Dict[str, Any]]:
    ensure_paths()
    if not os.path.exists(USERS_PATH):
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return []
    try:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return []

def _save_users(users: List[Dict[str, Any]]):
    ensure_paths()
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

# ==============================
# Admin Keypair (Optional)
# ==============================
def generate_admin_keypair(overwrite: bool = False, passphrase: Optional[bytes] = None) -> str:
    ensure_paths()
    if os.path.exists(PRIVATE_KEY_PATH) and not overwrite:
        raise FileExistsError("private_key.pem sudah ada.")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    encryption = serialization.BestAvailableEncryption(passphrase) if passphrase else serialization.NoEncryption()
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=encryption
    )
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(priv_pem)
    return PRIVATE_KEY_PATH

# ==============================
# Per-user Keypair
# ==============================
def generate_keypair_for_user(username: str, overwrite: bool = False) -> Dict[str, str]:
    ensure_paths()
    if not username:
        raise ValueError("Username tidak boleh kosong.")
    priv_path = os.path.join(KEYS_DIR, f"{username}_private_key.pem")
    pub_path = os.path.join(KEYS_DIR, f"{username}_public_key.pem")

    if os.path.exists(priv_path) and os.path.exists(pub_path) and not overwrite:
        return {"private": priv_path, "public": pub_path}

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(priv_path, "wb") as f:
        f.write(priv_pem)

    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(pub_path, "wb") as f:
        f.write(pub_pem)

    return {"private": priv_path, "public": pub_path}

# ==============================
# Generate New User (Keypair + Token + Features)
# ==============================
def generate_new_user(
    username: str,
    license_type: str = "user",
    days_valid: int = 365,
    features: Optional[List[str]] = None,
    overwrite_keys: bool = False
) -> Dict[str, Any]:
    ensure_paths()
    if not username:
        raise ValueError("Username wajib diisi.")

    users = _load_users()
    if any(u.get("username", "").lower() == username.lower() for u in users):
        raise ValueError(f"Username '{username}' sudah ada!")

    user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
    feats = features or ["seo_info"]  # default minimal

    paths = generate_keypair_for_user(username, overwrite=overwrite_keys)
    priv_path = paths["private"]; pub_path = paths["public"]

    with open(pub_path, "rb") as f:
        pub_bytes = f.read()
    fingerprint = _sha256_hex(pub_bytes)

    now = dt.datetime.utcnow()
    exp = now + dt.timedelta(days=days_valid)
    iat_int = int(now.timestamp()); exp_int = int(exp.timestamp())

    payload = {
        "sub": user_id,
        "username": username,
        "type": license_type,
        "features": feats,                 # >>> features masuk ke token
        "iat": iat_int,
        "exp": exp_int,
        "pub_fingerprint": fingerprint,
        "jti": str(uuid.uuid4())
    }

    with open(priv_path, "rb") as f:
        priv_bytes = f.read()
    token = jwt.encode(payload, priv_bytes, algorithm="RS256")

    record = {
        "user_id": user_id,
        "username": username,
        "license_type": license_type,
        "features": feats,                 # >>> features disimpan di users.json
        "exp": exp.isoformat() + "Z",
        "token_preview": token[:40] + "…",
        "public_key_path": os.path.relpath(pub_path, ROOT),
        "private_key_path": os.path.relpath(priv_path, ROOT),
        "pubkey_fingerprint": fingerprint
    }
    users.append(record)
    _save_users(users)

    try:
        with open(LICENSE_LOG_PATH, "a", encoding="utf-8") as lf:
            lf.write(json.dumps({
                "ts": dt.datetime.utcnow().isoformat() + "Z",
                "action": "CREATE_USER",
                "user_id": user_id,
                "username": username,
                "token_preview": token[:40] + "…"
            }) + "\n")
    except Exception:
        pass

    return {
        "user_id": user_id,
        "username": username,
        "public_key": pub_path,
        "private_key": priv_path,
        "pubkey_fingerprint": fingerprint,
        "license_token": token,
        "features": feats,
        "expires": exp.isoformat() + "Z"
    }

# ==============================
# Get Users & License History
# ==============================
def get_all_users() -> List[Dict[str, Any]]:
    return _load_users()

def get_license_history(limit: int = 100) -> List[Dict[str, Any]]:
    ensure_paths()
    if not os.path.exists(LICENSE_LOG_PATH):
        return []
    recs = []
    try:
        with open(LICENSE_LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
        for line in lines:
            try:
                recs.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return list(reversed(recs))

# ==============================
# Update / Query User Features
# ==============================
def update_user_features(username: str, new_features: List[str]) -> bool:
    users = _load_users()
    for u in users:
        if u["username"].lower() == username.lower():
            u["features"] = new_features
            _save_users(users)
            return True
    return False

def get_user_features(username: str) -> List[str]:
    users = _load_users()
    for u in users:
        if u["username"].lower() == username.lower():
            return u.get("features", [])
    return []
