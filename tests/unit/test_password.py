import pytest
from utils.password import pwd_context

def test_password_encryption():
    password = "qwerty"
    hashed = pwd_context.hash(password)
    assert pwd_context.verify(password, hashed)

def test_password_encryption_fails_for_mismatch():
    password = "qwerty"
    wrong_pasword = 'abc'
    hashed = pwd_context.hash(password)
    assert pwd_context.verify(wrong_pasword, hashed) is False

def test_hash_is_not_plaintext():
    password = 'qwerty'
    hashed = pwd_context.hash(password)
    assert hashed != password

def test_same_password_generates_different_hashes():
    password = 'abc'
    hashed = pwd_context.hash(password)
    assert hashed != pwd_context.hash(password)