"""
test_trade.py
Switchr - Sprint 3 Integration Test Cases
Tests for trade offer creation, acceptance, rejection, and cancellation.
Covers: REQ-92 to REQ-109
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
    cur.execute("DELETE FROM trades WHERE sender_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test') OR receiver_id IN (SELECT id FROM users WHERE email LIKE 'test_%@switchr.test')")
    cur.execute("DELETE FROM listings WHERE title LIKE 'TEST_%'")
    cur.execute("DELETE FROM users WHERE email LIKE 'test_%@switchr.test'")
    conn.close()


@pytest.fixture
def seller_one_token(client, db_cleanup):
    """Register and approve seller one, return token."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_seller1@switchr.test',
        'username': 'test_seller1',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved', balance=1000.00 WHERE email='test_seller1@switchr.test'")
    conn.close()
    return token


@pytest.fixture
def seller_two_token(client, db_cleanup):
    """Register and approve seller two, return token."""
    resp = client.post('/api/auth/register', json={
        'email': 'test_seller2@switchr.test',
        'username': 'test_seller2',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved', balance=1000.00 WHERE email='test_seller2@switchr.test'")
    conn.close()
    return token


def create_active_listing(client, token, title):
    """Helper to create and approve a listing, return listing data."""
    resp = client.post('/api/listings', data={
        'title': title,
        'description': 'Test listing for trade tests',
        'category': 'Phones',
        'price': 500.00,
        'condition': 'GOOD',
        'listingType': 'BOTH'
    }, headers={'Authorization': f'Bearer {token}'},
       content_type='multipart/form-data')
    listing = resp.get_json()['listing']
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE listings SET status='ACTIVE' WHERE id=%s", (listing['id'],))
    conn.close()
    return listing


# ============ CREATE TRADE TESTS ============

def test_create_trade_requires_auth(client, db_cleanup):
    """REQ-93: Must be logged in to initiate a trade."""
    resp = client.post('/api/trades', json={
        'offered_listing_id': 1,
        'wanted_listing_id': 2
    })
    assert resp.status_code == 401


def test_create_trade_success(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-92, REQ-96, REQ-98: Seller can send a trade offer for their active listing."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Trade Offer Phone')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Trade Wanted Phone')

    resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id']
    }, headers={'Authorization': f'Bearer {seller_one_token}'})

    assert resp.status_code == 201
    assert 'trade_id' in resp.get_json()


def test_create_trade_with_cash(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-97: Trader can add cash to balance an uneven trade."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Cash Trade Phone')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Cash Wanted Phone')

    resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id'],
        'cash_offer': 50.00
    }, headers={'Authorization': f'Bearer {seller_one_token}'})

    assert resp.status_code == 201


def test_cannot_trade_with_yourself(client, seller_one_token, db_cleanup):
    """REQ-108: Cannot trade with yourself."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Self Trade One')
    listing_two = create_active_listing(client, seller_one_token, 'TEST_Self Trade Two')

    resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id']
    }, headers={'Authorization': f'Bearer {seller_one_token}'})

    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_create_trade_missing_listing_ids(client, seller_one_token, db_cleanup):
    """REQ-96: Both listing IDs are required to create a trade."""
    resp = client.post('/api/trades', json={
        'offered_listing_id': 1
    }, headers={'Authorization': f'Bearer {seller_one_token}'})

    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_create_trade_insufficient_cash_balance(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-97: Cannot offer more cash than available balance."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Broke Trade Phone')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Broke Wanted Phone')

    resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id'],
        'cash_offer': 99999.00
    }, headers={'Authorization': f'Bearer {seller_one_token}'})

    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_create_trade_notifies_receiver(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-99: Receiver is notified when a trade offer is sent."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Notify Trade Phone')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Notify Wanted Phone')

    client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id']
    }, headers={'Authorization': f'Bearer {seller_one_token}'})

    resp = client.get('/api/notifications',
        headers={'Authorization': f'Bearer {seller_two_token}'})

    notifications = resp.get_json().get('notifications', [])
    types = [n['type'] for n in notifications]
    assert 'TRADE' in types


# ============ ACCEPT TRADE TESTS ============

def test_accept_trade_success(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-101, REQ-105: Receiver can accept a trade offer."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Accept Trade Phone')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Accept Wanted Phone')

    trade_resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id']
    }, headers={'Authorization': f'Bearer {seller_one_token}'})
    trade_id = trade_resp.get_json()['trade_id']

    resp = client.put(f'/api/trades/{trade_id}/accept',
        headers={'Authorization': f'Bearer {seller_two_token}'})

    assert resp.status_code == 200
    assert resp.get_json()['message'] == 'Trade accepted'


def test_accept_trade_marks_listings_traded(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-105, REQ-106: Both listings are marked TRADED after acceptance."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Traded Status One')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Traded Status Two')

    trade_resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id']
    }, headers={'Authorization': f'Bearer {seller_one_token}'})
    trade_id = trade_resp.get_json()['trade_id']

    client.put(f'/api/trades/{trade_id}/accept',
        headers={'Authorization': f'Bearer {seller_two_token}'})

    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT status FROM listings WHERE id=%s', (listing_one['id'],))
    assert cur.fetchone()[0] == 'TRADED'
    cur.execute('SELECT status FROM listings WHERE id=%s', (listing_two['id'],))
    assert cur.fetchone()[0] == 'TRADED'
    conn.close()


def test_accept_trade_notifies_sender(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-104: Sender is notified when trade is accepted."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Accept Notify One')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Accept Notify Two')

    trade_resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id']
    }, headers={'Authorization': f'Bearer {seller_one_token}'})
    trade_id = trade_resp.get_json()['trade_id']

    client.put(f'/api/trades/{trade_id}/accept',
        headers={'Authorization': f'Bearer {seller_two_token}'})

    resp = client.get('/api/notifications',
        headers={'Authorization': f'Bearer {seller_one_token}'})

    notifications = resp.get_json().get('notifications', [])
    messages = [n['message'] for n in notifications]
    assert any('accepted' in m for m in messages)


# ============ REJECT TRADE TESTS ============

def test_reject_trade_success(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-102: Receiver can reject a trade offer."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Reject Trade Phone')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Reject Wanted Phone')

    trade_resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id']
    }, headers={'Authorization': f'Bearer {seller_one_token}'})
    trade_id = trade_resp.get_json()['trade_id']

    resp = client.put(f'/api/trades/{trade_id}/reject',
        headers={'Authorization': f'Bearer {seller_two_token}'})

    assert resp.status_code == 200
    assert resp.get_json()['message'] == 'Trade rejected'


def test_reject_trade_notifies_sender(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-104: Sender is notified when trade is rejected."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Reject Notify One')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Reject Notify Two')

    trade_resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id']
    }, headers={'Authorization': f'Bearer {seller_one_token}'})
    trade_id = trade_resp.get_json()['trade_id']

    client.put(f'/api/trades/{trade_id}/reject',
        headers={'Authorization': f'Bearer {seller_two_token}'})

    resp = client.get('/api/notifications',
        headers={'Authorization': f'Bearer {seller_one_token}'})

    notifications = resp.get_json().get('notifications', [])
    messages = [n['message'] for n in notifications]
    assert any('rejected' in m for m in messages)


# ============ CANCEL TRADE TESTS ============

def test_cancel_trade_success(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-109: Sender can cancel their own pending trade offer."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Cancel Trade Phone')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Cancel Wanted Phone')

    trade_resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id']
    }, headers={'Authorization': f'Bearer {seller_one_token}'})
    trade_id = trade_resp.get_json()['trade_id']

    resp = client.put(f'/api/trades/{trade_id}/cancel',
        headers={'Authorization': f'Bearer {seller_one_token}'})

    assert resp.status_code == 200
    assert resp.get_json()['message'] == 'Trade cancelled'


def test_cancel_already_accepted_trade(client, seller_one_token, seller_two_token, db_cleanup):
    """REQ-109: Cannot cancel a trade that has already been accepted."""
    listing_one = create_active_listing(client, seller_one_token, 'TEST_Cancel Accepted One')
    listing_two = create_active_listing(client, seller_two_token, 'TEST_Cancel Accepted Two')

    trade_resp = client.post('/api/trades', json={
        'offered_listing_id': listing_one['id'],
        'wanted_listing_id': listing_two['id']
    }, headers={'Authorization': f'Bearer {seller_one_token}'})
    trade_id = trade_resp.get_json()['trade_id']

    client.put(f'/api/trades/{trade_id}/accept',
        headers={'Authorization': f'Bearer {seller_two_token}'})

    resp = client.put(f'/api/trades/{trade_id}/cancel',
        headers={'Authorization': f'Bearer {seller_one_token}'})

    assert resp.status_code == 400
    assert 'error' in resp.get_json()
