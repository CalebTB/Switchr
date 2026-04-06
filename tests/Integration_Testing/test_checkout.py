"""
test_checkout.py
Switchr - Regression Test Suite
Tests for the checkout/purchase flow.
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
    # Clean up in correct foreign key order
    cur.execute("DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'cotest_%@switchr.test')")
    cur.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE buyer_id IN (SELECT id FROM users WHERE email LIKE 'cotest_%@switchr.test'))")
    cur.execute("DELETE FROM transactions WHERE buyer_id IN (SELECT id FROM users WHERE email LIKE 'cotest_%@switchr.test')")
    cur.execute("DELETE FROM orders WHERE buyer_id IN (SELECT id FROM users WHERE email LIKE 'cotest_%@switchr.test')")
    cur.execute("DELETE FROM cart WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'cotest_%@switchr.test')")
    cur.execute("DELETE FROM listings WHERE title LIKE 'COTEST_%'")
    cur.execute("DELETE FROM users WHERE email LIKE 'cotest_%@switchr.test'")
    conn.close()


CHECKOUT_DATA = {
    'firstName': 'Test',
    'lastName': 'Buyer',
    'address': '123 Main St',
    'city': 'TestCity',
    'state': 'TS',
    'zip': '12345',
    'cardNumber': '4111111111111111',
    'cardName': 'Test Buyer',
    'billSameAsShip': True
}


def auth(token):
    return {'Authorization': f'Bearer {token}'}


def make_user(client, name, balance=0):
    """Register and approve a user, optionally set balance."""
    resp = client.post('/api/auth/register', json={
        'email': f'cotest_{name}@switchr.test',
        'username': f'cotest_{name}',
        'password': 'Password123!'
    })
    data = resp.get_json()
    token = data['token']
    user_id = data['user']['id']

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved', balance=%s WHERE id=%s", (balance, user_id))
    conn.close()

    return token, user_id


def make_listing(seller_token, client, title='COTEST_Item', price=50.00):
    """Create and approve a listing."""
    resp = client.post('/api/listings',
        data={
            'title': title,
            'description': 'Test item for checkout',
            'category': 'Phones',
            'price': str(price),
            'condition': 'GOOD',
            'listingType': 'SALE'
        },
        headers=auth(seller_token),
        content_type='multipart/form-data'
    )

    listing_id = resp.get_json()['listing']['id']

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE listings SET status='ACTIVE' WHERE id=%s", (listing_id,))
    conn.close()

    return listing_id


# ============ CHECKOUT TESTS ============

def test_checkout_success(client):
    """Full purchase flow: add to cart, checkout, balances update."""
    seller_token, seller_id = make_user(client, 'seller')
    buyer_token, buyer_id = make_user(client, 'buyer', balance=500.00)
    listing_id = make_listing(seller_token, client, price=100.00)

    # Add to cart
    client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(buyer_token))

    # Checkout
    resp = client.post('/api/checkout',
        json=CHECKOUT_DATA, headers=auth(buyer_token))

    assert resp.status_code == 201
    data = resp.get_json()
    assert 'order_id' in data
    assert data['total'] == 108.00  # 100 + 8% tax

    # Round-trip: buyer balance should be 500 - 108 = 392
    resp = client.get('/api/wallet/balance', headers=auth(buyer_token))
    assert resp.get_json()['balance'] == 392.00

    # Round-trip: seller should be credited the item price (no tax)
    resp = client.get('/api/wallet/balance', headers=auth(seller_token))
    assert resp.get_json()['balance'] == 100.00


def test_checkout_clears_cart(client):
    """Cart is empty after successful checkout."""
    seller_token, _ = make_user(client, 'seller')
    buyer_token, _ = make_user(client, 'buyer', balance=500.00)
    listing_id = make_listing(seller_token, client)

    client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(buyer_token))
    client.post('/api/checkout',
        json=CHECKOUT_DATA, headers=auth(buyer_token))

    resp = client.get('/api/cart', headers=auth(buyer_token))
    assert resp.get_json()['cart'] == []


def test_checkout_marks_listing_sold(client):
    """Purchased listing is marked SOLD and no longer appears in browse."""
    seller_token, _ = make_user(client, 'seller')
    buyer_token, _ = make_user(client, 'buyer', balance=500.00)
    listing_id = make_listing(seller_token, client)

    client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(buyer_token))
    client.post('/api/checkout',
        json=CHECKOUT_DATA, headers=auth(buyer_token))

    resp = client.get(f'/api/listings/browse/{listing_id}')
    assert resp.status_code == 404


def test_checkout_empty_cart(client):
    """Checkout fails when cart is empty."""
    buyer_token, _ = make_user(client, 'buyer', balance=500.00)

    resp = client.post('/api/checkout',
        json=CHECKOUT_DATA, headers=auth(buyer_token))

    assert resp.status_code == 400


def test_checkout_insufficient_balance(client):
    """Checkout fails when buyer doesn't have enough funds."""
    seller_token, _ = make_user(client, 'seller')
    buyer_token, _ = make_user(client, 'buyer', balance=10.00)
    listing_id = make_listing(seller_token, client, price=100.00)

    client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(buyer_token))

    resp = client.post('/api/checkout',
        json=CHECKOUT_DATA, headers=auth(buyer_token))

    assert resp.status_code == 400
    assert 'Insufficient balance' in resp.get_json()['error']


def test_checkout_requires_approved_account(client):
    """Pending user cannot checkout."""
    # Make seller (approved) and a pending buyer
    seller_token, _ = make_user(client, 'seller')
    resp = client.post('/api/auth/register', json={
        'email': 'cotest_pending@switchr.test',
        'username': 'cotest_pending',
        'password': 'Password123!'
    })
    pending_token = resp.get_json()['token']

    listing_id = make_listing(seller_token, client)

    client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(pending_token))

    resp = client.post('/api/checkout',
        json=CHECKOUT_DATA, headers=auth(pending_token))

    assert resp.status_code == 403


def test_checkout_creates_notifications(client):
    """Checkout creates notifications for both buyer and seller."""
    seller_token, seller_id = make_user(client, 'seller')
    buyer_token, buyer_id = make_user(client, 'buyer', balance=500.00)
    listing_id = make_listing(seller_token, client)

    client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(buyer_token))
    client.post('/api/checkout',
        json=CHECKOUT_DATA, headers=auth(buyer_token))

    # Seller gets a sale notification
    resp = client.get('/api/notifications', headers=auth(seller_token))
    seller_notifs = resp.get_json()['notifications']
    assert any('purchased' in n['message'] for n in seller_notifs)

    # Buyer gets an order confirmation notification
    resp = client.get('/api/notifications', headers=auth(buyer_token))
    buyer_notifs = resp.get_json()['notifications']
    assert any('confirmed' in n['message'] for n in buyer_notifs)


def test_checkout_requires_auth(client):
    """Cannot checkout without a token."""
    resp = client.post('/api/checkout', json=CHECKOUT_DATA)
    assert resp.status_code == 401
