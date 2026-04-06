"""
test_wallet.py
Switchr - Regression Test Suite
Tests for adding funds and checking balance.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app, get_db


# ============ FIXTURES ============

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def db_cleanup():
    yield
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE email LIKE 'wallettest_%@switchr.test'")
    conn.close()


@pytest.fixture
def user_token(client):
    """Register a user and return their token."""
    resp = client.post('/api/auth/register', json={
        'email': 'wallettest_user@switchr.test',
        'username': 'wallettest_user',
        'password': 'Password123!'
    })
    return resp.get_json()['token']


def auth(token):
    return {'Authorization': f'Bearer {token}'}


# ============ GET BALANCE TESTS ============

def test_new_user_balance_is_zero(client, user_token):
    """New account starts with a zero balance."""
    resp = client.get('/api/wallet/balance', headers=auth(user_token))

    assert resp.status_code == 200
    assert resp.get_json()['balance'] == 0.0


def test_balance_requires_auth(client):
    """Cannot check balance without a token."""
    resp = client.get('/api/wallet/balance')
    assert resp.status_code == 401


# ============ ADD FUNDS TESTS ============

def test_add_funds_success(client, user_token):
    """Adding funds increases the balance by the correct amount."""
    resp = client.post('/api/wallet/add',
        json={'amount': 50.00}, headers=auth(user_token))

    assert resp.status_code == 200
    assert resp.get_json()['balance'] == 50.0

    # Round-trip: verify balance endpoint matches
    resp = client.get('/api/wallet/balance', headers=auth(user_token))
    assert resp.get_json()['balance'] == 50.0


def test_add_funds_accumulates(client, user_token):
    """Multiple deposits stack correctly."""
    client.post('/api/wallet/add',
        json={'amount': 25.00}, headers=auth(user_token))
    client.post('/api/wallet/add',
        json={'amount': 75.00}, headers=auth(user_token))

    resp = client.get('/api/wallet/balance', headers=auth(user_token))
    assert resp.get_json()['balance'] == 100.0


def test_add_funds_zero_rejected(client, user_token):
    """Cannot add zero dollars."""
    resp = client.post('/api/wallet/add',
        json={'amount': 0}, headers=auth(user_token))

    assert resp.status_code == 400


def test_add_funds_negative_rejected(client, user_token):
    """Cannot add a negative amount."""
    resp = client.post('/api/wallet/add',
        json={'amount': -10}, headers=auth(user_token))

    assert resp.status_code == 400


def test_add_funds_requires_auth(client):
    """Cannot add funds without a token."""
    resp = client.post('/api/wallet/add', json={'amount': 50.00})
    assert resp.status_code == 401
