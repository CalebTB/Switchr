"""
test_history.py
Switchr - Sprint 3 Integration Test Cases
Tests for purchase history, sales history, and transaction details.
Covers.REQ-128, REQ-90
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
    cur.execute("DELETE FROM transactions WHERE buyer_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test') OR seller_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM orders WHERE buyer_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM cart WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM listings WHERE title LIKE 'TEST_%'")
    cur.execute("DELETE FROM users WHERE email LIKE 'test_%@switchr.test'")
    conn.close()


@pytest.fixture
def seller_token(client, db_cleanup):
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
def buyer_token(client, db_cleanup):
    resp = client.post('/api/auth/register', json={
        'email': 'test_buyer@switchr.test',
        'username': 'test_buyer',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved', balance=2000.00 WHERE email='test_buyer@switchr.test'")
    conn.close()
    return token


def create_active_listing(client, seller_token, title='TEST_History Listing'):
    resp = client.post('/api/listings', data={
        'title': title,
        'description': 'Test listing for history tests',
        'category': 'Phones',
        'price': 300.00,
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
    return {
        'firstName': 'John', 'lastName': 'Doe',
        'address': '123 Test St', 'city': 'Starkville',
        'state': 'MS', 'zip': '39759',
        'billSameAsShip': True,
        'cardNumber': '4111111111111111',
        'cardName': 'John Doe',
        'cardExpiry': '12/26', 'cardCvv': '123'
    }


def complete_purchase(client, buyer_token, listing_id):
    """Helper to add to cart and checkout."""
    client.post('/api/cart',
        json={'listing_id': listing_id},
        headers={'Authorization': f'Bearer {buyer_token}'})
    return client.post('/api/checkout',
        json=checkout_payload(),
        headers={'Authorization': f'Bearer {buyer_token}'})


# ============ PURCHASE HISTORY TESTS ============

def test_purchase_history_requires_auth(client, db_cleanup):
    """REQ-124: Must be logged in to view purchase history."""
    resp = client.get('/api/transactions/purchases')
    assert resp.status_code == 401


def test_purchase_history_empty_for_new_user(client, buyer_token, db_cleanup):
    """REQ-124, REQ-125: New user has empty purchase history."""
    resp = client.get('/api/transactions/purchases',
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 200
    assert resp.get_json()['transactions'] == []


def test_purchase_history_shows_after_checkout(client, buyer_token, seller_token, db_cleanup):
    """REQ-125, REQ-90: Purchase history shows completed transactions."""
    listing = create_active_listing(client, seller_token)
    complete_purchase(client, buyer_token, listing['id'])

    resp = client.get('/api/transactions/purchases',
        headers={'Authorization': f'Bearer {buyer_token}'})

    transactions = resp.get_json()['transactions']
    assert len(transactions) > 0
    assert transactions[0]['title'] == listing['title']


def test_purchase_history_only_shows_own(client, buyer_token, seller_token, db_cleanup):
    """REQ-124: Buyer can only see their own purchases."""
    listing = create_active_listing(client, seller_token)
    complete_purchase(client, buyer_token, listing['id'])

    # Seller should not see buyer's purchases
    resp = client.get('/api/transactions/purchases',
        headers={'Authorization': f'Bearer {seller_token}'})

    transactions = resp.get_json()['transactions']
    assert len(transactions) == 0


# ============ SALES HISTORY TESTS ============

def test_sales_history_requires_auth(client, db_cleanup):
    """REQ-124: Must be logged in to view sales history."""
    resp = client.get('/api/transactions/sales')
    assert resp.status_code == 401


def test_sales_history_empty_for_new_user(client, seller_token, db_cleanup):
    """REQ-124, REQ-126: New seller has empty sales history."""
    resp = client.get('/api/transactions/sales',
        headers={'Authorization': f'Bearer {seller_token}'})
    assert resp.status_code == 200
    assert resp.get_json()['transactions'] == []


def test_sales_history_shows_after_purchase(client, buyer_token, seller_token, db_cleanup):
    """REQ-126, REQ-90: Sales history shows when buyer purchases seller's item."""
    listing = create_active_listing(client, seller_token, 'TEST_Sales History Item')
    complete_purchase(client, buyer_token, listing['id'])

    resp = client.get('/api/transactions/sales',
        headers={'Authorization': f'Bearer {seller_token}'})

    transactions = resp.get_json()['transactions']
    assert len(transactions) > 0
    assert transactions[0]['title'] == listing['title']


# ============ SINGLE TRANSACTION TESTS ============

def test_get_transaction_by_id(client, buyer_token, seller_token, db_cleanup):
    """REQ-124: Can retrieve a single transaction by ID."""
    listing = create_active_listing(client, seller_token, 'TEST_Single Txn Item')
    checkout_resp = complete_purchase(client, buyer_token, listing['id'])
    txn_id = checkout_resp.get_json()['transaction_ids'][0]

    resp = client.get(f'/api/transactions/{txn_id}',
        headers={'Authorization': f'Bearer {buyer_token}'})

    assert resp.status_code == 200
    data = resp.get_json()
    assert 'transaction' in data


def test_get_transaction_requires_auth(client, db_cleanup):
    """REQ-124: Must be logged in to view a transaction."""
    resp = client.get('/api/transactions/1')
    assert resp.status_code == 401


def test_cannot_view_other_users_transaction(client, buyer_token, seller_token, db_cleanup):
    """REQ-124: Cannot view a transaction you are not part of."""
    # Register a third user
    client.post('/api/auth/register', json={
        'email': 'test_third@switchr.test',
        'username': 'test_third',
        'password': 'Password123!'
    })
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved', balance=2000.00 WHERE email='test_third@switchr.test'")
    conn.close()
    third_resp = client.post('/api/auth/login', json={
        'email': 'test_third@switchr.test',
        'password': 'Password123!'
    })
    third_token = third_resp.get_json()['token']

    listing = create_active_listing(client, seller_token, 'TEST_Other Txn Item')
    checkout_resp = complete_purchase(client, buyer_token, listing['id'])
    txn_id = checkout_resp.get_json()['transaction_ids'][0]

    resp = client.get(f'/api/transactions/{txn_id}',
        headers={'Authorization': f'Bearer {third_token}'})

    assert resp.status_code == 404
