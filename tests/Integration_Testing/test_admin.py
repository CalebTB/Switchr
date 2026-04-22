"""
test_admin.py
Switchr - Sprint 3 Integration Test Cases
Tests for admin user management and listing moderation.
Covers.REQ-138
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
    cur.execute("DELETE FROM listings WHERE title LIKE 'TEST_%'")
    cur.execute("DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM users WHERE email LIKE 'test_%@switchr.test'")
    conn.close()


@pytest.fixture
def admin_token(client, db_cleanup):
    """Register and set up an admin user, return token."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_admin@switchr.test',
        'username': 'test_admin',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved', role='admin' WHERE email='test_admin@switchr.test'")
    conn.close()
    # Re-login to get token with admin role
    resp = client.post('/api/auth/login', json={
        'email': 'test_admin@switchr.test',
        'password': 'Password123!'
    })
    return resp.get_json().get('token')


@pytest.fixture
def regular_token(client, db_cleanup):
    """Register a regular user, return token."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_regular@switchr.test',
        'username': 'test_regular',
        'password': 'Password123!'
    })
    return resp.get_json().get('token')


@pytest.fixture
def pending_user_id(client, db_cleanup):
    """Register a pending user, return their id."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_pending@switchr.test',
        'username': 'test_pending',
        'password': 'Password123!'
    })
    return resp.get_json()['user']['id']


@pytest.fixture
def seller_token(client, db_cleanup):
    """Register and approve a seller, return token."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_seller@switchr.test',
        'username': 'test_seller',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE email='test_seller@switchr.test'")
    conn.close()
    return token


def create_pending_listing(client, seller_token, title='TEST_Admin Listing'):
    """Helper to create a listing in PENDING_APPROVAL status."""
    resp = client.post('/api/listings', data={
        'title': title,
        'description': 'Test listing for admin tests',
        'category': 'Phones',
        'price': 500.00,
        'condition': 'GOOD',
        'listingType': 'SALE'
    }, headers={'Authorization': f'Bearer {seller_token}'},
       content_type='multipart/form-data')
    return resp.get_json()['listing']


# ============ ADMIN ACCESS TESTS ============

def test_admin_stats_requires_auth(client, db_cleanup):
    """Admin dashboard requires authentication."""
    resp = client.get('/api/admin/stats')
    assert resp.status_code == 401


def test_admin_stats_requires_admin_role(client, regular_token, db_cleanup):
    """Regular users cannot access admin dashboard."""
    resp = client.get('/api/admin/stats',
        headers={'Authorization': f'Bearer {regular_token}'})
    assert resp.status_code == 403


def test_admin_stats_success(client, admin_token, db_cleanup):
    """Admin can view platform stats."""
    resp = client.get('/api/admin/stats',
        headers={'Authorization': f'Bearer {admin_token}'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'total_users' in data
    assert 'active_listings' in data
    assert 'pending_approvals' in data


# ============ ADMIN USER MANAGEMENT TESTS ============

def test_admin_get_users(client, admin_token, db_cleanup):
    """Admin can view all users."""
    resp = client.get('/api/admin/users',
        headers={'Authorization': f'Bearer {admin_token}'})
    assert resp.status_code == 200
    assert 'users' in resp.get_json()


def test_admin_get_users_requires_admin(client, regular_token, db_cleanup):
    """Regular users cannot view all users."""
    resp = client.get('/api/admin/users',
        headers={'Authorization': f'Bearer {regular_token}'})
    assert resp.status_code == 403


def test_admin_approve_user(client, admin_token, pending_user_id, db_cleanup):
    """Admin can approve a pending user."""
    resp = client.put(f'/api/admin/users/{pending_user_id}/approve',
        headers={'Authorization': f'Bearer {admin_token}'})
    assert resp.status_code == 200
    assert resp.get_json()['user']['status'] == 'approved'


def test_admin_deny_user(client, admin_token, pending_user_id, db_cleanup):
    """Admin can deny a pending user."""
    resp = client.put(f'/api/admin/users/{pending_user_id}/deny',
        json={'reason': 'Test denial reason'},
        headers={'Authorization': f'Bearer {admin_token}'})
    assert resp.status_code == 200
    assert resp.get_json()['user']['status'] == 'denied'


def test_admin_deny_user_with_reason(client, admin_token, pending_user_id, db_cleanup):
    """Denying a user requires a reason."""
    resp = client.put(f'/api/admin/users/{pending_user_id}/deny',
        json={'reason': 'Violation of terms'},
        headers={'Authorization': f'Bearer {admin_token}'})
    assert resp.status_code == 200
    assert resp.get_json()['user']['status'] == 'denied'


# ============ ADMIN LISTING MANAGEMENT TESTS ============

def test_admin_get_listings(client, admin_token, db_cleanup):
    """Admin can view all listings."""
    resp = client.get('/api/admin/listings',
        headers={'Authorization': f'Bearer {admin_token}'})
    assert resp.status_code == 200
    assert 'listings' in resp.get_json()


def test_admin_approve_listing(client, admin_token, seller_token, db_cleanup):
    """Admin can approve a pending listing."""
    listing = create_pending_listing(client, seller_token)
    resp = client.put(f'/api/admin/listings/{listing["id"]}/approve',
        headers={'Authorization': f'Bearer {admin_token}'})
    assert resp.status_code == 200
    assert resp.get_json()['listing']['status'] == 'ACTIVE'


def test_admin_deny_listing(client, admin_token, seller_token, db_cleanup):
    """Admin can deny a pending listing."""
    listing = create_pending_listing(client, seller_token, 'TEST_Deny Listing')
    resp = client.put(f'/api/admin/listings/{listing["id"]}/deny',
        json={'reason': 'Prohibited item'},
        headers={'Authorization': f'Bearer {admin_token}'})
    assert resp.status_code == 200
    assert resp.get_json()['listing']['status'] == 'DENIED'


def test_admin_deny_user_with_reason(client, admin_token, pending_user_id, db_cleanup):
    """Admin can deny a user with a reason."""
    resp = client.put(f'/api/admin/users/{pending_user_id}/deny',
        json={'reason': 'Violation of terms'},
        headers={'Authorization': f'Bearer {admin_token}'})
    assert resp.status_code == 200
    assert resp.get_json()['user']['status'] == 'denied'
    assert resp.get_json()['user']['denial_reason'] == 'Violation of terms'


def test_admin_get_listings_requires_admin(client, regular_token, db_cleanup):
    """Regular users cannot access admin listings."""
    resp = client.get('/api/admin/listings',
        headers={'Authorization': f'Bearer {regular_token}'})
    assert resp.status_code == 403
