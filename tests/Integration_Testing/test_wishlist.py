"""
test_wishlist.py
Switchr - Sprint 4 Integration Test Cases
Tests for wishlist feature - save listings for later.
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
    cur.execute("DELETE FROM wishlist WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM listings WHERE title LIKE 'TEST_%'")
    cur.execute("DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM users WHERE email LIKE 'test_%@switchr.test'")
    conn.close()


@pytest.fixture
def buyer_token(client, db_cleanup):
    """Register and approve a test buyer, return token."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_buyer@switchr.test',
        'username': 'test_buyer',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE email='test_buyer@switchr.test'")
    conn.close()
    return token


@pytest.fixture
def seller_token(client, db_cleanup):
    """Register and approve a test seller, return token."""
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


@pytest.fixture
def active_listing(client, seller_token):
    """Create and approve a test listing, return listing data."""
    resp = client.post('/api/listings', data={
        'title': 'TEST_Wishlist Item',
        'description': 'Test listing for wishlist tests',
        'category': 'Phones',
        'price': 400.00,
        'condition': 'GOOD',
        'listingType': 'SALE'
    }, headers={'Authorization': f'Bearer {seller_token}'},
       content_type='multipart/form-data')
    listing = resp.get_json()['listing']
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE listings SET status='ACTIVE' WHERE id=%s", (listing['id'],))
    conn.close()
    return listing


# ============ WISHLIST TESTS ============

def test_add_to_wishlist_requires_auth(client, active_listing, db_cleanup):
    """Unauthenticated user cannot add to wishlist."""
    resp = client.post('/api/wishlist', json={'listing_id': active_listing['id']})
    assert resp.status_code == 401


def test_add_to_wishlist_success(client, buyer_token, active_listing, db_cleanup):
    """Buyer can add an active listing to their wishlist."""
    resp = client.post('/api/wishlist',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 201
    assert resp.get_json()['message'] == 'Added to wishlist'


def test_add_to_wishlist_missing_listing_id(client, buyer_token, db_cleanup):
    """Adding to wishlist without listing_id returns 400."""
    resp = client.post('/api/wishlist',
        json={},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_add_nonexistent_listing_to_wishlist(client, buyer_token, db_cleanup):
    """Adding a nonexistent listing to wishlist returns 404."""
    resp = client.post('/api/wishlist',
        json={'listing_id': 99999},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 404


def test_add_to_wishlist_no_duplicate(client, buyer_token, active_listing, db_cleanup):
    """Adding the same listing twice does not create a duplicate."""
    client.post('/api/wishlist',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {buyer_token}'})
    resp = client.post('/api/wishlist',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 201

    resp = client.get('/api/wishlist',
        headers={'Authorization': f'Bearer {buyer_token}'})
    items = resp.get_json()['wishlist']
    ids = [item['listing_id'] for item in items]
    assert ids.count(active_listing['id']) == 1


def test_get_wishlist_requires_auth(client, db_cleanup):
    """Unauthenticated user cannot view wishlist."""
    resp = client.get('/api/wishlist')
    assert resp.status_code == 401


def test_get_wishlist_empty_for_new_user(client, buyer_token, db_cleanup):
    """New user has empty wishlist."""
    resp = client.get('/api/wishlist',
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 200
    assert resp.get_json()['wishlist'] == []


def test_get_wishlist_shows_saved_items(client, buyer_token, active_listing, db_cleanup):
    """Wishlist shows items that were added."""
    client.post('/api/wishlist',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {buyer_token}'})

    resp = client.get('/api/wishlist',
        headers={'Authorization': f'Bearer {buyer_token}'})
    items = resp.get_json()['wishlist']
    assert len(items) == 1
    assert items[0]['listing_id'] == active_listing['id']
    assert items[0]['title'] == active_listing['title']


def test_remove_from_wishlist_success(client, buyer_token, active_listing, db_cleanup):
    """Buyer can remove a listing from their wishlist."""
    client.post('/api/wishlist',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {buyer_token}'})

    resp = client.delete(f'/api/wishlist/{active_listing["id"]}',
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 200
    assert resp.get_json()['message'] == 'Removed from wishlist'


def test_remove_from_wishlist_requires_auth(client, active_listing, db_cleanup):
    """Unauthenticated user cannot remove from wishlist."""
    resp = client.delete(f'/api/wishlist/{active_listing["id"]}')
    assert resp.status_code == 401


def test_wishlist_only_shows_own_items(client, buyer_token, seller_token, active_listing, db_cleanup):
    """Buyer only sees their own wishlist items."""
    client.post('/api/wishlist',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {buyer_token}'})

    resp = client.get('/api/wishlist',
        headers={'Authorization': f'Bearer {seller_token}'})
    items = resp.get_json()['wishlist']
    assert len(items) == 0
