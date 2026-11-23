"""Accounts and sessions, stored in PostgreSQL."""

import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv
from psycopg.errors import UniqueViolation

load_dotenv()  # DATABASE_URL may live in .env; this module can be imported before main.py

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vst:vst@127.0.0.1:5432/vst")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "14"))

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD = 8
MAX_PASSWORD = 128

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Earlier versions of this table used an e-mail column.
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'users' AND column_name = 'email') THEN
        ALTER TABLE users RENAME COLUMN email TO username;
    END IF;
END $$;
DROP INDEX IF EXISTS users_email_lower_idx;
CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_idx ON users (lower(username));
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL
);
"""


class AuthError(Exception):
    """A problem the user should see (bad input, wrong password, username taken)."""


def _connect():
    return psycopg.connect(DATABASE_URL, connect_timeout=5)


def init_db(wait_seconds: int = 30) -> None:
    """Create the tables, waiting for the database to accept connections."""
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            with _connect() as conn:
                conn.execute(SCHEMA)
            return
        except psycopg.OperationalError:
            if time.monotonic() > deadline:
                raise
            time.sleep(1)


# ---- passwords (scrypt from the standard library) ----

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(candidate, bytes.fromhex(digest))
    except ValueError:
        return False


# ---- accounts ----

def _clean(username: str, password: str) -> tuple[str, str]:
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise AuthError("Username must be 3-32 characters: letters, digits, '.', '_' or '-'.")
    if not MIN_PASSWORD <= len(password or "") <= MAX_PASSWORD:
        raise AuthError(f"Password must be {MIN_PASSWORD}-{MAX_PASSWORD} characters.")
    return username, password


def create_user(username: str, password: str) -> dict:
    username, password = _clean(username, password)
    try:
        with _connect() as conn:
            row = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id, username",
                (username, hash_password(password)),
            ).fetchone()
    except UniqueViolation:
        raise AuthError("This username is already taken.")
    return {"id": row[0], "username": row[1]}


# A hash to check against when the username is unknown, so the response time
# does not reveal whether an account exists.
_DUMMY_HASH = hash_password("not-a-real-password")


def check_login(username: str, password: str) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE lower(username) = lower(%s)",
            ((username or "").strip(),),
        ).fetchone()
    ok = verify_password(password or "", row[2] if row else _DUMMY_HASH)
    if not row or not ok:
        raise AuthError("Wrong username or password.")
    return {"id": row[0], "username": row[1]}


# ---- sessions (only a hash of the token is stored) ----

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < now()")
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
            (_token_hash(token), user_id, expires),
        )
    return token


def user_for_session(token: str | None) -> dict | None:
    if not token:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT u.id, u.username FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = %s AND s.expires_at > now()",
            (_token_hash(token),),
        ).fetchone()
    return {"id": row[0], "username": row[1]} if row else None


def delete_session(token: str | None) -> None:
    if token:
        with _connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = %s", (_token_hash(token),))
