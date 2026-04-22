"""
test_listings.py
Switchr - Sprint 3 Test Cases
Tests for listing creation, editing, deletion, and browsing.
Covers.REQ-27, REQ-38 to REQ-58, REQ-59 to REQ-66
"""

import pytest
import json
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
    cur.execute("DELETE FROM cart WHERE listing_id IN (SELECT id FROM listings WHERE title LIKE 'TEST_%')")
    cur.execute("DELETE FROM listings WHERE title LIKE 'TEST_%'")
    cur.execute("DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM users WHERE email LIKE 'test_%@switchr.test'")
    conn.close()


@pytest.fixture
def seller_token(client, db_cleanup):
    """Register and approve a test seller, return auth token."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_seller@switchr.test',
        'username': 'test_seller',
        'password': 'Password123!',
        'role': 'seller'
    })
    data = resp.get_json()
    token = data.get('token')

    # Approve the seller account
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE email='test_seller@switchr.test'")
    conn.close()

    return token


@pytest.fixture
def buyer_token(client, db_cleanup):
    """Register and approve a test buyer, return auth token."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_buyer@switchr.test',
        'username': 'test_buyer',
        'password': 'Password123!',
        'role': 'user'
    })
    data = resp.get_json()
    token = data.get('token')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE email='test_buyer@switchr.test'")
    conn.close()

    return token


@pytest.fixture
def active_listing(client, seller_token):
    """Create and approve a test listing, return listing data."""
    resp = client.post('/api/listings', data={
        'title': 'TEST_iPhone 13 Pro',
        'description': 'Test listing for pytest',
        'category': 'Phones',
        'price': 599.99,
        'condition': 'GOOD',
        'listingType': 'SALE'
    }, headers={'Authorization': f'Bearer {seller_token}'},
       content_type='multipart/form-data')

    listing = resp.get_json()['listing']

    # Approve the listing
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE listings SET status='ACTIVE' WHERE id=%s", (listing['id'],))
    conn.close()

    return listing


# ============ CREATE LISTING TESTS ============

def test_create_listing_success(client, seller_token, db_cleanup):
    """REQ-18, REQ-26, REQ-27: Seller can create a listing successfully."""
    resp = client.post('/api/listings', data={
        'title': 'TEST_MacBook Air M2',
        'description': 'Barely used laptop',
        'category': 'Laptops',
        'price': 899.99,
        'condition': 'LIKE_NEW',
        'listingType': 'SALE'
    }, headers={'Authorization': f'Bearer {seller_token}'},
       content_type='multipart/form-data')

    assert resp.status_code == 201
    data = resp.get_json()
    assert 'listing' in data
    assert data['listing']['title'] == 'TEST_MacBook Air M2'
    assert data['listing']['status'] == 'PENDING_APPROVAL'


def test_create_listing_requires_auth(client, db_cleanup):
    """REQ-18: Cannot create listing without authentication."""
    resp = client.post('/api/listings', data={
        'title': 'TEST_Unauthorized Listing',
        'description': 'Should fail',
        'category': 'Phones',
        'price': 100.00,
        'condition': 'GOOD',
        'listingType': 'SALE'
    }, content_type='multipart/form-data')
    assert resp.status_code == 401


def test_create_listing_title_too_long(client, seller_token, db_cleanup):
    """REQ-19: Title must be 100 characters or less."""
    resp = client.post('/api/listings', data={
        'title': 'TEST_' + 'A' * 100,
        'description': 'Test description',
        'category': 'Phones',
        'price': 100.00,
        'condition': 'GOOD',
        'listingType': 'SALE'
    }, headers={'Authorization': f'Bearer {seller_token}'},
       content_type='multipart/form-data')

    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_create_listing_missing_required_fields(client, seller_token, db_cleanup):
    """REQ-20, REQ-21, REQ-22, REQ-23, REQ-24: All fields are required."""
    resp = client.post('/api/listings', data={
        'title': 'TEST_Incomplete Listing'
        # missing description, category, price, condition, listingType
    }, headers={'Authorization': f'Bearer {seller_token}'},
       content_type='multipart/form-data')

    assert resp.status_code == 400


def test_create_listing_pending_approval(client, seller_token, db_cleanup):
    """REQ-27: New listing starts as PENDING_APPROVAL."""
    resp = client.post('/api/listings', data={
        'title': 'TEST_Pending Listing',
        'description': 'Should be pending',
        'category': 'Tablets',
        'price': 300.00,
        'condition': 'NEW',
        'listingType': 'BOTH'
    }, headers={'Authorization': f'Bearer {seller_token}'},
       content_type='multipart/form-data')

    assert resp.status_code == 201
    assert resp.get_json()['listing']['status'] == 'PENDING_APPROVAL'


# ============ GET LISTINGS TESTS ============

def test_get_seller_listings(client, seller_token, db_cleanup):
    """REQ-39: Seller can view their own listings."""
    # Create a listing first
    client.post('/api/listings', data={
        'title': 'TEST_My Listing',
        'description': 'Test',
        'category': 'Phones',
        'price': 200.00,
        'condition': 'GOOD',
        'listingType': 'SALE'
    }, headers={'Authorization': f'Bearer {seller_token}'},
       content_type='multipart/form-data')

    resp = client.get('/api/listings',
        headers={'Authorization': f'Bearer {seller_token}'})

    assert resp.status_code == 200
    data = resp.get_json()
    assert 'listings' in data
    titles = [l['title'] for l in data['listings']]
    assert 'TEST_My Listing' in titles


def test_get_listings_requires_auth(client):
    """REQ-83: Seller listings endpoint requires authentication."""
    resp = client.get('/api/listings')
    assert resp.status_code == 401


# ============ EDIT LISTING TESTS ============

def test_edit_listing_success(client, seller_token, active_listing, db_cleanup):
    """REQ-41 to REQ-48: Seller can edit their own listing."""
    listing_id = active_listing['id']

    resp = client.put(f'/api/listings/{listing_id}', json={
        'title': 'TEST_iPhone 13 Pro Updated',
        'description': 'Updated description',
        'category': 'Phones',
        'price': 549.99,
        'condition': 'FAIR',
        'listingType': 'BOTH'
    }, headers={'Authorization': f'Bearer {seller_token}'})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['listing']['price'] == '549.99'


def test_edit_listing_resubmits_for_approval(client, seller_token, active_listing, db_cleanup):
    """REQ-49: Editing title/description of ACTIVE listing sends back for approval."""
    listing_id = active_listing['id']

    resp = client.put(f'/api/listings/{listing_id}', json={
        'title': 'TEST_Changed Title Needs Approval',
        'description': 'Changed description',
        'category': 'Phones',
        'price': 599.99,
        'condition': 'GOOD',
        'listingType': 'SALE'
    }, headers={'Authorization': f'Bearer {seller_token}'})

    assert resp.status_code == 200
    assert resp.get_json()['listing']['status'] == 'PENDING_APPROVAL'


def test_edit_listing_wrong_owner(client, buyer_token, active_listing, db_cleanup):
    """REQ-57: Cannot edit a listing you don't own."""
    listing_id = active_listing['id']

    resp = client.put(f'/api/listings/{listing_id}', json={
        'title': 'TEST_Hacked Title',
        'description': 'Should fail',
        'category': 'Phones',
        'price': 1.00,
        'condition': 'POOR',
        'listingType': 'SALE'
    }, headers={'Authorization': f'Bearer {buyer_token}'})

    assert resp.status_code == 404


# ============ DELETE LISTING TESTS ============

def test_delete_listing_success(client, seller_token, active_listing, db_cleanup):
    """REQ-50, REQ-52: Seller can delete their own listing."""
    listing_id = active_listing['id']

    resp = client.delete(f'/api/listings/{listing_id}',
        headers={'Authorization': f'Bearer {seller_token}'})

    assert resp.status_code == 200
    assert 'message' in resp.get_json()


def test_delete_sets_deleted_status(client, seller_token, active_listing, db_cleanup):
    """REQ-52: Deleted listing is marked DELETED not removed from DB."""
    listing_id = active_listing['id']

    client.delete(f'/api/listings/{listing_id}',
        headers={'Authorization': f'Bearer {seller_token}'})

    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT status FROM listings WHERE id=%s', (listing_id,))
    row = cur.fetchone()
    conn.close()

    assert row is not None  # record still exists
    assert row[0] == 'DELETED'


def test_delete_listing_wrong_owner(client, buyer_token, active_listing, db_cleanup):
    """REQ-57: Cannot delete a listing you don't own."""
    listing_id = active_listing['id']

    resp = client.delete(f'/api/listings/{listing_id}',
        headers={'Authorization': f'Bearer {buyer_token}'})

    assert resp.status_code == 404


def test_delete_requires_auth(client, active_listing, db_cleanup):
    """REQ-50: Delete requires authentication."""
    listing_id = active_listing['id']

    resp = client.delete(f'/api/listings/{listing_id}')
    assert resp.status_code == 401


# ============ BROWSE LISTINGS TESTS ============

def test_browse_returns_active_only(client, active_listing, db_cleanup):
    """REQ-59, REQ-38: Browse only shows ACTIVE listings."""
    resp = client.get('/api/listings/browse')

    assert resp.status_code == 200
    listings = resp.get_json()['listings']
    for listing in listings:
        assert listing['status'] == 'ACTIVE'


def test_browse_no_auth_required(client):
    """REQ-66: Browse does not require login."""
    resp = client.get('/api/listings/browse')
    assert resp.status_code == 200


def test_browse_listing_detail(client, active_listing, db_cleanup):
    """REQ-64, REQ-65: Can view full details of a single active listing."""
    listing_id = active_listing['id']

    resp = client.get(f'/api/listings/browse/{listing_id}')

    assert resp.status_code == 200
    data = resp.get_json()
    assert 'listing' in data
    assert data['listing']['id'] == listing_id
    assert 'seller_username' in data['listing']


def test_browse_deleted_listing_not_found(client, seller_token, active_listing, db_cleanup):
    """REQ-52, REQ-89: Deleted listing does not appear in browse."""
    listing_id = active_listing['id']

    # Delete the listing
    client.delete(f'/api/listings/{listing_id}',
        headers={'Authorization': f'Bearer {seller_token}'})

    # Try to browse it
    resp = client.get(f'/api/listings/browse/{listing_id}')
    assert resp.status_code == 404