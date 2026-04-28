"""
test_auction.py
Switchr - Sprint 4 Integration Test Cases
Tests for auction feature - bidding, countdown, and settlement.
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
    yield
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM bids WHERE listing_id IN (SELECT id FROM listings WHERE title LIKE 'TEST_AUC_%')")
    cur.execute("DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_auc_%@switchr.test')")
    cur.execute("DELETE FROM listings WHERE title LIKE 'TEST_AUC_%'")
    cur.execute("DELETE FROM users WHERE email LIKE 'test_auc_%@switchr.test'")
    conn.close()


@pytest.fixture
def seller_token(client, db_cleanup):
    resp = client.post('/api/auth/register', json={
        'email': 'test_auc_seller@switchr.test',
        'username': 'test_auc_seller',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved', role='seller' WHERE email='test_auc_seller@switchr.test'")
    conn.close()
    return token


@pytest.fixture
def buyer_token(client, db_cleanup):
    resp = client.post('/api/auth/register', json={
        'email': 'test_auc_buyer@switchr.test',
        'username': 'test_auc_buyer',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE email='test_auc_buyer@switchr.test'")
    conn.close()
    return token


@pytest.fixture
def buyer2_token(client, db_cleanup):
    resp = client.post('/api/auth/register', json={
        'email': 'test_auc_buyer2@switchr.test',
        'username': 'test_auc_buyer2',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE email='test_auc_buyer2@switchr.test'")
    conn.close()
    return token


@pytest.fixture
def active_auction(client, seller_token):
    """Create and approve an auction listing."""
    resp = client.post('/api/listings', data={
        'title': 'TEST_AUC_iPhone',
        'description': 'Test auction listing',
        'category': 'Phones',
        'starting_price': 100.00,
        'condition': 'GOOD',
        'listingType': 'AUCTION',
        'auction_duration_days': 3
    }, headers={'Authorization': f'Bearer {seller_token}'},
       content_type='multipart/form-data')
    data = resp.get_json()
    assert 'listing' in data, f"Failed to create auction listing: {data}"
    listing = data['listing']
    conn = get_db()
    cur = conn.cursor()
    # Approve and set auction end time to future
    cur.execute("""
        UPDATE listings 
        SET status='ACTIVE', 
            auction_end_time = CURRENT_TIMESTAMP + INTERVAL '72 hours'
        WHERE id=%s
    """, (listing['id'],))
    conn.close()
    return listing


# ============ AUCTION TESTS ============

def test_get_auctions_success(client):
    """Anyone can view active auctions."""
    resp = client.get('/api/auctions')
    assert resp.status_code == 200
    assert 'auctions' in resp.get_json()


def test_place_bid_requires_auth(client, active_auction, db_cleanup):
    """Unauthenticated user cannot place a bid."""
    resp = client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 150.00})
    assert resp.status_code == 401


def test_place_bid_success(client, buyer_token, active_auction, db_cleanup):
    """Buyer can place a bid higher than the current price."""
    resp = client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 150.00},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['message'] == 'Bid placed'
    assert data['current_price'] == 150.00


def test_bid_must_exceed_current_price(client, buyer_token, active_auction, db_cleanup):
    """Bid equal to or below current price should be rejected."""
    # Bid at exactly current price
    resp = client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 100.00},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()

    # Bid below current price
    resp2 = client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 50.00},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp2.status_code == 400


def test_cannot_bid_on_own_auction(client, seller_token, active_auction, db_cleanup):
    """Seller cannot bid on their own auction listing."""
    resp = client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 150.00},
        headers={'Authorization': f'Bearer {seller_token}'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_cannot_bid_on_non_auction_listing(client, buyer_token, seller_token, db_cleanup):
    """Bidding on a non-auction listing should be rejected."""
    # Create a regular SALE listing
    resp = client.post('/api/listings', data={
        'title': 'TEST_AUC_SaleListing',
        'description': 'Regular sale listing',
        'category': 'Phones',
        'price': 200.00,
        'condition': 'GOOD',
        'listingType': 'SALE'
    }, headers={'Authorization': f'Bearer {seller_token}'},
       content_type='multipart/form-data')
    listing_id = resp.get_json()['listing']['id']

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE listings SET status='ACTIVE' WHERE id=%s", (listing_id,))
    conn.close()

    resp2 = client.post(f'/api/listings/{listing_id}/bid',
        json={'amount': 250.00},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp2.status_code == 400
    assert 'Not an auction' in resp2.get_json().get('error', '')


def test_bid_invalid_amount(client, buyer_token, active_auction, db_cleanup):
    """Invalid bid amount should be rejected."""
    resp = client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 'notanumber'},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 400


def test_get_bids_for_listing(client, buyer_token, active_auction, db_cleanup):
    """Can retrieve bid history for an auction listing."""
    # Place a bid first
    client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 150.00},
        headers={'Authorization': f'Bearer {buyer_token}'})

    resp = client.get(f'/api/listings/{active_auction["id"]}/bids')
    assert resp.status_code == 200
    bids = resp.get_json()['bids']
    assert len(bids) >= 1
    assert bids[0]['amount'] == 150.00


def test_get_bids_empty_for_new_auction(client, active_auction, db_cleanup):
    """New auction with no bids returns empty list."""
    resp = client.get(f'/api/listings/{active_auction["id"]}/bids')
    assert resp.status_code == 200
    assert resp.get_json()['bids'] == []


def test_outbid_notification_sent(client, buyer_token, buyer2_token, active_auction, db_cleanup):
    """Previous bidder receives notification when outbid."""
    # First buyer places bid
    client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 150.00},
        headers={'Authorization': f'Bearer {buyer_token}'})

    # Second buyer outbids
    client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 200.00},
        headers={'Authorization': f'Bearer {buyer2_token}'})

    # Check first buyer got outbid notification
    resp = client.get('/api/notifications',
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 200
    notifications = resp.get_json().get('notifications', [])
    outbid_notifs = [n for n in notifications if 'outbid' in n['message'].lower()]
    assert len(outbid_notifs) >= 1


def test_bid_on_nonexistent_auction(client, buyer_token, db_cleanup):
    """Bidding on a nonexistent listing returns 404."""
    resp = client.post('/api/listings/99999/bid',
        json={'amount': 150.00},
        headers={'Authorization': f'Bearer {buyer_token}'})
    assert resp.status_code == 404


def test_multiple_bids_increase_price(client, buyer_token, buyer2_token, active_auction, db_cleanup):
    """Each valid bid increases the current price of the auction."""
    client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 150.00},
        headers={'Authorization': f'Bearer {buyer_token}'})

    client.post(f'/api/listings/{active_auction["id"]}/bid',
        json={'amount': 200.00},
        headers={'Authorization': f'Bearer {buyer2_token}'})

    resp = client.get(f'/api/listings/{active_auction["id"]}/bids')
    bids = resp.get_json()['bids']
    amounts = [b['amount'] for b in bids]
    assert 200.00 in amounts
    assert 150.00 in amounts
