"""
test_cart.py
Switchr - Regression Test Suite
Tests for cart add, remove, and retrieval.
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
    cur.execute("DELETE FROM cart WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'carttest_%@switchr.test')")
    cur.execute("DELETE FROM listings WHERE title LIKE 'CARTTEST_%'")
    cur.execute("DELETE FROM users WHERE email LIKE 'carttest_%@switchr.test'")
    conn.close()


def auth(token):
    return {'Authorization': f'Bearer {token}'}


def make_user(client, name):
    """Register and approve a user, return token."""
    resp = client.post('/api/auth/register', json={
        'email': f'carttest_{name}@switchr.test',
        'username': f'carttest_{name}',
        'password': 'Password123!'
    })
    data = resp.get_json()
    token = data['token']
    user_id = data['user']['id']

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE id=%s", (user_id,))
    conn.close()

    return token, user_id


def make_listing(seller_token, client, title='CARTTEST_Item', price=50.00):
    """Create and approve a listing, return listing id."""
    resp = client.post('/api/listings',
        data={
            'title': title,
            'description': 'Test item',
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


# ============ GET CART TESTS ============

def test_cart_empty_for_new_user(client):
    """New user has an empty cart."""
    token, _ = make_user(client, 'buyer')
    resp = client.get('/api/cart', headers=auth(token))

    assert resp.status_code == 200
    assert resp.get_json()['cart'] == []


def test_cart_requires_auth(client):
    """Cannot view cart without a token."""
    resp = client.get('/api/cart')
    assert resp.status_code == 401


# ============ ADD TO CART TESTS ============

def test_add_to_cart_success(client):
    """Buyer can add an active listing to their cart."""
    seller_token, _ = make_user(client, 'seller')
    buyer_token, _ = make_user(client, 'buyer')
    listing_id = make_listing(seller_token, client)

    resp = client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(buyer_token))

    assert resp.status_code == 201

    # Round-trip: verify it shows up in cart
    resp = client.get('/api/cart', headers=auth(buyer_token))
    cart = resp.get_json()['cart']
    assert len(cart) == 1
    assert cart[0]['listing_id'] == listing_id


def test_add_to_cart_missing_listing_id(client):
    """Add to cart fails without a listing_id."""
    token, _ = make_user(client, 'buyer')
    resp = client.post('/api/cart', json={}, headers=auth(token))

    assert resp.status_code == 400


def test_add_to_cart_nonexistent_listing(client):
    """Cannot add a listing that doesn't exist."""
    token, _ = make_user(client, 'buyer')
    resp = client.post('/api/cart',
        json={'listing_id': 999999}, headers=auth(token))

    assert resp.status_code == 404


def test_cannot_add_own_listing(client):
    """Seller cannot add their own listing to cart."""
    seller_token, _ = make_user(client, 'seller')
    listing_id = make_listing(seller_token, client)

    resp = client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(seller_token))

    assert resp.status_code == 400


def test_add_to_cart_requires_auth(client):
    """Cannot add to cart without a token."""
    resp = client.post('/api/cart', json={'listing_id': 1})
    assert resp.status_code == 401


def test_add_duplicate_does_not_error(client):
    """Adding the same listing twice doesn't create a duplicate or error."""
    seller_token, _ = make_user(client, 'seller')
    buyer_token, _ = make_user(client, 'buyer')
    listing_id = make_listing(seller_token, client)

    client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(buyer_token))
    resp = client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(buyer_token))

    assert resp.status_code == 201

    # Should still only be one item in cart
    resp = client.get('/api/cart', headers=auth(buyer_token))
    assert len(resp.get_json()['cart']) == 1


# ============ REMOVE FROM CART TESTS ============

def test_remove_from_cart_success(client):
    """Buyer can remove an item from their cart."""
    seller_token, _ = make_user(client, 'seller')
    buyer_token, _ = make_user(client, 'buyer')
    listing_id = make_listing(seller_token, client)

    client.post('/api/cart',
        json={'listing_id': listing_id}, headers=auth(buyer_token))

    resp = client.delete(f'/api/cart/{listing_id}', headers=auth(buyer_token))
    assert resp.status_code == 200

    # Round-trip: cart should be empty
    resp = client.get('/api/cart', headers=auth(buyer_token))
    assert resp.get_json()['cart'] == []


def test_remove_from_cart_requires_auth(client):
    """Cannot remove from cart without a token."""
    resp = client.delete('/api/cart/1')
    assert resp.status_code == 401
