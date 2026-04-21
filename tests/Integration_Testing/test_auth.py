"""
test_auth.py
Switchr - Sprint 3 Integration Test Cases
Tests for user registration, login, and authentication.
Covers.REQ-17
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


@pytest.fixture
def db_cleanup():
    """Clean up test data after each test."""
    yield
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM users WHERE email LIKE 'test_%@switchr.test'")
    conn.close()


# ============ REGISTRATION TESTS ============

def test_register_success(client, db_cleanup):
    """REQ-1, REQ-5, REQ-7: User can register with valid details."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_newuser@switchr.test',
        'username': 'test_newuser',
        'password': 'Password123!'
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'token' in data
    assert data['user']['email'] == 'test_newuser@switchr.test'
    assert data['user']['username'] == 'test_newuser'


def test_register_requires_email(client, db_cleanup):
    """REQ-2: Email is required for registration."""
    resp = client.post('/api/auth/register', json={
        'username': 'test_noemail',
        'password': 'Password123!'
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_register_requires_username(client, db_cleanup):
    """REQ-3: Username is required for registration."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_nousername@switchr.test',
        'password': 'Password123!'
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_register_requires_password(client, db_cleanup):
    """REQ-4: Password is required for registration."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_nopassword@switchr.test',
        'username': 'test_nopassword'
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_register_duplicate_email(client, db_cleanup):
    """REQ-2: Email must be unique."""
    client.post('/api/auth/register', json={
        'email': 'test_duplicate@switchr.test',
        'username': 'test_duplicate1',
        'password': 'Password123!'
    })
    resp = client.post('/api/auth/register', json={
        'email': 'test_duplicate@switchr.test',
        'username': 'test_duplicate2',
        'password': 'Password123!'
    })
    assert resp.status_code == 409
    assert 'error' in resp.get_json()


def test_register_duplicate_username(client, db_cleanup):
    """REQ-3: Username must be unique."""
    client.post('/api/auth/register', json={
        'email': 'test_dupuser1@switchr.test',
        'username': 'test_dupuser',
        'password': 'Password123!'
    })
    resp = client.post('/api/auth/register', json={
        'email': 'test_dupuser2@switchr.test',
        'username': 'test_dupuser',
        'password': 'Password123!'
    })
    assert resp.status_code == 409
    assert 'error' in resp.get_json()


def test_register_new_account_pending(client, db_cleanup):
    """REQ-5: New account status is set to pending after registration."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_pending@switchr.test',
        'username': 'test_pending',
        'password': 'Password123!'
    })
    assert resp.status_code == 201
    assert resp.get_json()['user']['status'] == 'pending'


def test_register_returns_token(client, db_cleanup):
    """REQ-5: Registration returns a valid auth token."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_token@switchr.test',
        'username': 'test_token',
        'password': 'Password123!'
    })
    assert resp.status_code == 201
    assert 'token' in resp.get_json()
    assert resp.get_json()['token'] is not None


# ============ LOGIN TESTS ============

def test_login_success(client, db_cleanup):
    """REQ-8, REQ-9, REQ-10: User can log in with valid credentials."""
    client.post('/api/auth/register', json={
        'email': 'test_login@switchr.test',
        'username': 'test_login',
        'password': 'Password123!'
    })

    resp = client.post('/api/auth/login', json={
        'email': 'test_login@switchr.test',
        'password': 'Password123!'
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert 'token' in data
    assert data['user']['email'] == 'test_login@switchr.test'


def test_login_wrong_password(client, db_cleanup):
    """REQ-10: Login fails with wrong password."""
    client.post('/api/auth/register', json={
        'email': 'test_wrongpass@switchr.test',
        'username': 'test_wrongpass',
        'password': 'Password123!'
    })

    resp = client.post('/api/auth/login', json={
        'email': 'test_wrongpass@switchr.test',
        'password': 'WrongPassword!'
    })

    assert resp.status_code == 401
    assert 'error' in resp.get_json()


def test_login_nonexistent_user(client, db_cleanup):
    """REQ-10: Login fails for email that does not exist."""
    resp = client.post('/api/auth/login', json={
        'email': 'test_ghost@switchr.test',
        'password': 'Password123!'
    })
    assert resp.status_code == 401
    assert 'error' in resp.get_json()


def test_login_requires_email(client, db_cleanup):
    """REQ-9: Email is required to log in."""
    resp = client.post('/api/auth/login', json={
        'password': 'Password123!'
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_login_requires_password(client, db_cleanup):
    """REQ-9: Password is required to log in."""
    resp = client.post('/api/auth/login', json={
        'email': 'test_login@switchr.test'
    })
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ============ AUTHENTICATED USER TESTS ============

def test_get_current_user_with_token(client, db_cleanup):
    """REQ-14: Authenticated user can retrieve their profile info."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_me@switchr.test',
        'username': 'test_me',
        'password': 'Password123!'
    })
    token = resp.get_json()['token']

    resp = client.get('/api/auth/me',
        headers={'Authorization': f'Bearer {token}'})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['user']['email'] == 'test_me@switchr.test'


def test_get_current_user_requires_auth(client, db_cleanup):
    """REQ-13: Cannot access profile without a valid token."""
    resp = client.get('/api/auth/me')
    assert resp.status_code == 401
