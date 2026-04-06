"""
test_auth.py
Switchr - Regression Test Suite
Tests for registration, login, and current user endpoint.
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
    """Clean up test auth data after each test."""
    yield
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'authtest_%@switchr.test')")
    cur.execute("DELETE FROM cart WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'authtest_%@switchr.test')")
    cur.execute("DELETE FROM users WHERE email LIKE 'authtest_%@switchr.test'")
    conn.close()


def register_user(client, email='authtest_user@switchr.test', username='authtest_user', password='Password123!'):
    """Helper to register a test user."""
    return client.post('/api/auth/register', json={
        'email': email,
        'username': username,
        'password': password
    })


# ============ REGISTER TESTS ============

def test_register_success(client):
    """New user can register and gets back a token and user object."""
    resp = register_user(client)

    assert resp.status_code == 201
    data = resp.get_json()
    assert 'token' in data
    assert data['user']['email'] == 'authtest_user@switchr.test'
    assert data['user']['username'] == 'authtest_user'
    assert data['user']['role'] == 'user'
    assert data['user']['status'] == 'pending'


def test_register_missing_email(client):
    """Registration fails without an email."""
    resp = client.post('/api/auth/register', json={
        'username': 'authtest_noemail',
        'password': 'Password123!'
    })
    assert resp.status_code == 400


def test_register_missing_username(client):
    """Registration fails without a username."""
    resp = client.post('/api/auth/register', json={
        'email': 'authtest_nouser@switchr.test',
        'password': 'Password123!'
    })
    assert resp.status_code == 400


def test_register_missing_password(client):
    """Registration fails without a password."""
    resp = client.post('/api/auth/register', json={
        'email': 'authtest_nopass@switchr.test',
        'username': 'authtest_nopass'
    })
    assert resp.status_code == 400


def test_register_duplicate_email(client):
    """Cannot register two accounts with the same email."""
    register_user(client)
    resp = register_user(client, username='authtest_user2')

    assert resp.status_code == 409


def test_register_duplicate_username(client):
    """Cannot register two accounts with the same username."""
    register_user(client)
    resp = register_user(client, email='authtest_user2@switchr.test')

    assert resp.status_code == 409


# ============ LOGIN TESTS ============

def test_login_success(client):
    """Registered user can log in with correct credentials."""
    register_user(client)
    resp = client.post('/api/auth/login', json={
        'email': 'authtest_user@switchr.test',
        'password': 'Password123!'
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert 'token' in data
    assert data['user']['email'] == 'authtest_user@switchr.test'


def test_login_wrong_password(client):
    """Login fails with incorrect password."""
    register_user(client)
    resp = client.post('/api/auth/login', json={
        'email': 'authtest_user@switchr.test',
        'password': 'WrongPassword!'
    })

    assert resp.status_code == 401


def test_login_nonexistent_email(client):
    """Login fails for an email that doesn't exist."""
    resp = client.post('/api/auth/login', json={
        'email': 'authtest_nobody@switchr.test',
        'password': 'Password123!'
    })

    assert resp.status_code == 401


def test_login_missing_email(client):
    """Login fails without an email."""
    resp = client.post('/api/auth/login', json={
        'password': 'Password123!'
    })

    assert resp.status_code == 400


def test_login_missing_password(client):
    """Login fails without a password."""
    resp = client.post('/api/auth/login', json={
        'email': 'authtest_user@switchr.test'
    })

    assert resp.status_code == 400


# ============ GET CURRENT USER TESTS ============

def test_me_returns_user_data(client):
    """Authenticated user can fetch their own profile."""
    resp = register_user(client)
    token = resp.get_json()['token']

    resp = client.get('/api/auth/me',
        headers={'Authorization': f'Bearer {token}'})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['user']['email'] == 'authtest_user@switchr.test'
    assert data['user']['role'] == 'user'
    assert 'balance' in data['user']


def test_me_requires_auth(client):
    """Cannot fetch profile without a token."""
    resp = client.get('/api/auth/me')

    assert resp.status_code == 401


def test_me_invalid_token(client):
    """Fake token is rejected."""
    resp = client.get('/api/auth/me',
        headers={'Authorization': 'Bearer fake.token.here'})

    assert resp.status_code == 401


def test_me_reflects_approval_status(client):
    """After admin approves, /me returns updated status."""
    resp = register_user(client)
    data = resp.get_json()
    token = data['token']
    user_id = data['user']['id']

    # Simulate admin approval
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE id=%s", (user_id,))
    conn.close()

    resp = client.get('/api/auth/me',
        headers={'Authorization': f'Bearer {token}'})

    assert resp.status_code == 200
    assert resp.get_json()['user']['status'] == 'approved'
