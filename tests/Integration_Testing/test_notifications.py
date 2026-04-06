"""
test_notifications.py
Switchr - Regression Test Suite
Tests for the notifications endpoint.
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
    cur.execute("DELETE FROM notifications WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'notiftest_%@switchr.test')")
    cur.execute("DELETE FROM users WHERE email LIKE 'notiftest_%@switchr.test'")
    conn.close()


@pytest.fixture
def user_with_token(client):
    """Register a user, return (token, user_id)."""
    resp = client.post('/api/auth/register', json={
        'email': 'notiftest_user@switchr.test',
        'username': 'notiftest_user',
        'password': 'Password123!'
    })
    data = resp.get_json()
    return data['token'], data['user']['id']


def auth(token):
    return {'Authorization': f'Bearer {token}'}


# ============ GET NOTIFICATIONS TESTS ============

def test_notifications_empty_for_new_user(client, user_with_token):
    """New user has no notifications."""
    token, _ = user_with_token
    resp = client.get('/api/notifications', headers=auth(token))

    assert resp.status_code == 200
    assert resp.get_json()['notifications'] == []


def test_notifications_requires_auth(client):
    """Cannot fetch notifications without a token."""
    resp = client.get('/api/notifications')
    assert resp.status_code == 401


def test_notifications_returns_inserted_data(client, user_with_token):
    """Notifications inserted into the DB show up in the API response."""
    token, user_id = user_with_token

    # Insert a notification directly
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
        (user_id, 'Your item was purchased!')
    )
    conn.close()

    resp = client.get('/api/notifications', headers=auth(token))

    assert resp.status_code == 200
    notifs = resp.get_json()['notifications']
    assert len(notifs) == 1
    assert notifs[0]['message'] == 'Your item was purchased!'
    assert notifs[0]['is_read'] is False


def test_notifications_ordered_newest_first(client, user_with_token):
    """Notifications come back in newest-first order."""
    token, user_id = user_with_token

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (user_id, 'First'))
    cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (user_id, 'Second'))
    cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (user_id, 'Third'))
    conn.close()

    resp = client.get('/api/notifications', headers=auth(token))
    messages = [n['message'] for n in resp.get_json()['notifications']]

    assert messages == ['Third', 'Second', 'First']


def test_notifications_limited_to_20(client, user_with_token):
    """API returns at most 20 notifications."""
    token, user_id = user_with_token

    conn = get_db()
    cur = conn.cursor()
    for i in range(25):
        cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
            (user_id, f'Notification {i}'))
    conn.close()

    resp = client.get('/api/notifications', headers=auth(token))
    notifs = resp.get_json()['notifications']

    assert len(notifs) == 20


def test_notifications_only_returns_own(client, user_with_token):
    """User cannot see another user's notifications."""
    token, user_id = user_with_token

    # Create a second user
    resp2 = client.post('/api/auth/register', json={
        'email': 'notiftest_other@switchr.test',
        'username': 'notiftest_other',
        'password': 'Password123!'
    })
    other_id = resp2.get_json()['user']['id']

    # Insert notification for the other user
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
        (other_id, 'Secret notification'))
    conn.close()

    # First user should see nothing
    resp = client.get('/api/notifications', headers=auth(token))
    assert resp.get_json()['notifications'] == []
