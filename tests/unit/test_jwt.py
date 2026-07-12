import pytest
from utils.security import create_access_token,decodeJWT
from datetime import timedelta


def test_create_access_token_returns_string():
    data = {"subject": "user_123"}
    token = create_access_token(data)
    assert isinstance(token,str)

def test_create_access_token_contains_subject():
    token = create_access_token(subject = "123")
    payload = decodeJWT(token)
    assert payload["sub"] == "123"

def test_decode_valid_token():
    subject = "123"
    token = create_access_token(subject)
    payload = decodeJWT(token)
    assert payload["sub"] == subject

def test_create_access_token_contains_expiry():
    token = create_access_token(subject = "123")
    payload = decodeJWT(token)
    assert 'exp' in payload

def test_decode_invalid_token_returns_none():
    token = "this.is.not.jwt"
    payload = decodeJWT(token)
    assert payload == None

from jose import jwt
from datetime import datetime, timedelta
def test_decode_expired_token_returns_none():
    expires_delta=timedelta(minutes=-1)
    token = create_access_token(
    subject="123",
    expires_delta=expires_delta
    )
    payload = decodeJWT(token)

    assert payload is None
