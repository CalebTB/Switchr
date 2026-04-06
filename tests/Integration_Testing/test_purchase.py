"""
test_purchase.py
Switchr - Sprint 3 Test Cases
Tests for cart and checkout/purchase flow.
Covers.REQ-91
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
    cur.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE buyer_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test'))")
    cur.execute("DELETE FROM transactions WHERE buyer_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM orders WHERE buyer_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM cart WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM listings WHERE title LIKE 'TEST_%'")
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
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE email='test_seller@switchr.test'")
    conn.close()
    return token


@pytest.fixture
def buyer_token(client, db_cleanup):
    """Register and approve a test buyer with balance, return auth token."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_buyer@switchr.test',
        'username': 'test_buyer',
        'password': 'Password123!',
        'role': 'user'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved', balance=2000.00 WHERE email='test_buyer@switchr.test'")
    conn.close()
    return token


@pytest.fixture
def active_listing(client, seller_token):
    """Create and approve a test listing, return listing data."""
    resp = client.post('/api/listings', data={
        'title': 'TEST_iPhone for Purchase',
        'description': 'Test listing for purchase tests',
        'category': 'Phones',
        'price': 500.00,
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


def checkout_payload():
    """Return a standard checkout payload."""
    return {
        'firstName': 'John',
        'lastName': 'Doe',
        'address': '123 Test St',
        'city': 'Starkville',
        'state': 'MS',
        'zip': '39759',
        'billSameAsShip': True,
        'cardNumber': '4111111111111111',
        'cardName': 'John Doe',
        'cardExpiry': '12/26',
        'cardCvv': '123'
    }


# ============ CART TESTS ============

def test_add_to_cart_requires_auth(client, active_listing, db_cleanup):
    """REQ-83: Must be logged in to add to cart."""
    resp = client.post('/api/cart', json={'listing_id': active_listing['id']})
    assert resp.status_code == 401


def test_add_to_cart_success(client, buyer_token, active_listing, db_cleanup):
    """REQ-82, REQ-83: Logged in buyer can add a listing to cart."""
    resp = client.post('/api/cart',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 201
    assert resp.get_json()['message'] == 'Added to cart'


def test_cannot_add_own_listing_to_cart(client, seller_token, active_listing, db_cleanup):
    """REQ-91: Seller cannot add their own listing to cart."""
    resp = client.post('/api/cart',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {seller_token}'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


# ============ CHECKOUT TESTS ============

def test_checkout_requires_auth(client, db_cleanup):
    """REQ-83: Checkout requires authentication."""
    resp = client.post('/api/checkout', json=checkout_payload())
    assert resp.status_code == 401


def test_checkout_empty_cart(client, buyer_token, db_cleanup):
    """REQ-82: Cannot checkout with empty cart."""
    resp = client.post('/api/checkout',
        json=checkout_payload(),
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_checkout_success(client, buyer_token, active_listing, db_cleanup):
    """REQ-82, REQ-84, REQ-85, REQ-86, REQ-87: Full checkout flow completes successfully."""
    # Add to cart
    client.post('/api/cart',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {buyer_token}'})

    # Checkout
    resp = client.post('/api/checkout',
        json=checkout_payload(),
        headers={'Authorization': f'Bearer {buyer_token}'})

    assert resp.status_code == 201
    data = resp.get_json()
    assert 'order_id' in data
    assert 'total' in data


def test_checkout_marks_listing_sold(client, buyer_token, active_listing, db_cleanup):
    """REQ-88: Listing is marked SOLD after purchase."""
    listing_id = active_listing['id']

    client.post('/api/cart',
        json={'listing_id': listing_id},
        headers={'Authorization': f'Bearer {buyer_token}'})

    client.post('/api/checkout',
        json=checkout_payload(),
        headers={'Authorization': f'Bearer {buyer_token}'})

    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT status FROM listings WHERE id=%s', (listing_id,))
    row = cur.fetchone()
    conn.close()

    assert row[0] == 'SOLD'


def test_checkout_removes_listing_from_browse(client, buyer_token, active_listing, db_cleanup):
    """REQ-89: Sold listing no longer appears in browse results."""
    listing_id = active_listing['id']

    client.post('/api/cart',
        json={'listing_id': listing_id},
        headers={'Authorization': f'Bearer {buyer_token}'})

    client.post('/api/checkout',
        json=checkout_payload(),
        headers={'Authorization': f'Bearer {buyer_token}'})

    resp = client.get('/api/listings/browse')
    listings = resp.get_json()['listings']
    ids = [l['id'] for l in listings]
    assert listing_id not in ids


def test_checkout_records_transaction(client, buyer_token, active_listing, db_cleanup):
    """REQ-90: Transaction is recorded after purchase."""
    client.post('/api/cart',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {buyer_token}'})

    resp = client.post('/api/checkout',
        json=checkout_payload(),
        headers={'Authorization': f'Bearer {buyer_token}'})

    transaction_ids = resp.get_json().get('transaction_ids', [])
    assert len(transaction_ids) > 0


def test_checkout_clears_cart(client, buyer_token, active_listing, db_cleanup):
    """REQ-82: Cart is cleared after successful checkout."""
    client.post('/api/cart',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {buyer_token}'})

    client.post('/api/checkout',
        json=checkout_payload(),
        headers={'Authorization': f'Bearer {buyer_token}'})

    resp = client.get('/api/cart',
        headers={'Authorization': f'Bearer {buyer_token}'})

    cart_items = resp.get_json().get('cart', [])
    assert len(cart_items) == 0


def test_checkout_insufficient_balance(client, active_listing, db_cleanup, client_obj=None):
    """REQ-86: Checkout fails if buyer has insufficient balance."""
    # Register a broke buyer
    resp = client.post('/api/auth/register', json={
        'email': 'test_broke@switchr.test',
        'username': 'test_broke',
        'password': 'Password123!',
        'role': 'user'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved', balance=1.00 WHERE email='test_broke@switchr.test'")
    conn.close()

    client.post('/api/cart',
        json={'listing_id': active_listing['id']},
        headers={'Authorization': f'Bearer {token}'})

    resp = client.post('/api/checkout',
        json=checkout_payload(),
        headers={'Authorization': f'Bearer {token}'})

    assert resp.status_code == 400
    assert 'Insufficient balance' in resp.get_json()['error']