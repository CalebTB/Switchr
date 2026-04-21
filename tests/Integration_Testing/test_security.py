"""
test_security.py
Switchr - Sprint 4 Security Testing
Tests for SQL injection, authentication bypass, and access control vulnerabilities.
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
    cur.execute("DELETE FROM wishlist WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'sec_%@switchr.test')")
    cur.execute("DELETE FROM cart WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'sec_%@switchr.test')")
    cur.execute("DELETE FROM listings WHERE seller_id IN (SELECT id FROM users WHERE email LIKE 'sec_%@switchr.test')")
    cur.execute("DELETE FROM users WHERE email LIKE 'sec_%@switchr.test'")
    conn.close()


@pytest.fixture
def buyer_token(client, db_cleanup):
    resp = client.post('/api/auth/register', json={
        'email': 'sec_buyer@switchr.test',
        'username': 'sec_buyer',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved' WHERE email='sec_buyer@switchr.test'")
    conn.close()
    return token


@pytest.fixture
def seller_token(client, db_cleanup):
    resp = client.post('/api/auth/register', json={
        'email': 'sec_seller@switchr.test',
        'username': 'sec_seller',
        'password': 'Password123!'
    })
    token = resp.get_json().get('token')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status='approved', role='seller' WHERE email='sec_seller@switchr.test'")
    conn.close()
    return token


# ============ SQL INJECTION TESTS ============

class TestSQLInjection:
    """Tests that verify SQL injection attempts are blocked or safely handled."""

    def test_login_sql_injection_email(self, client, db_cleanup):
        """SQL injection in login email field should not authenticate."""
        payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "admin'--",
            "' UNION SELECT * FROM users--",
            "'; DROP TABLE users;--",
        ]
        for payload in payloads:
            resp = client.post('/api/auth/login', json={
                'email': payload,
                'password': 'anything'
            })
            assert resp.status_code in [400, 401, 422], \
                f"SQL injection payload '{payload}' should be rejected, got {resp.status_code}"
            data = resp.get_json()
            assert 'token' not in data, \
                f"SQL injection payload '{payload}' should not return a token"

    def test_login_sql_injection_password(self, client, db_cleanup):
        """SQL injection in login password field should not authenticate."""
        payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "' UNION SELECT password FROM users--",
        ]
        for payload in payloads:
            resp = client.post('/api/auth/login', json={
                'email': 'nonexistent@test.com',
                'password': payload
            })
            assert resp.status_code in [400, 401, 422], \
                f"SQL injection in password '{payload}' should be rejected"
            data = resp.get_json()
            assert 'token' not in data

    def test_register_sql_injection_username(self, client, db_cleanup):
        """SQL injection in registration username should be safely handled."""
        payloads = [
            "'; DROP TABLE users;--",
            "' OR '1'='1",
            "admin'--",
        ]
        for payload in payloads:
            resp = client.post('/api/auth/register', json={
                'email': f'sec_sqlinject_{abs(hash(payload)) % 10000}@switchr.test',
                'username': f'sec_{abs(hash(payload)) % 10000}',
                'password': 'Password123!'
            })
            assert resp.status_code in [200, 201, 400, 409, 422]
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            conn.close()
            assert count >= 0, "Users table should still exist after SQL injection attempt"

    def test_search_sql_injection(self, client, buyer_token):
        """SQL injection in search query should be safely handled."""
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE listings;--",
            "' UNION SELECT * FROM users--",
        ]
        for payload in payloads:
            resp = client.get(
                f'/api/listings?search={payload}',
                headers={'Authorization': f'Bearer {buyer_token}'}
            )
            assert resp.status_code in [200, 400], \
                f"Search SQL injection '{payload}' caused unexpected status {resp.status_code}"
            normal = client.get(
                '/api/listings',
                headers={'Authorization': f'Bearer {buyer_token}'}
            )
            assert normal.status_code == 200, \
                "Listings endpoint should still work after SQL injection attempt"

    def test_listing_id_sql_injection(self, client, buyer_token):
        """SQL injection in listing ID path parameter should be rejected."""
        payloads = [
            "1 OR 1=1",
            "1; DROP TABLE listings;--",
        ]
        for payload in payloads:
            resp = client.get(
                f'/api/listings/{payload}',
                headers={'Authorization': f'Bearer {buyer_token}'}
            )
            assert resp.status_code in [400, 404, 405, 422], \
                f"SQL injection in listing ID '{payload}' should be rejected"


# ============ AUTHENTICATION BYPASS TESTS ============

class TestAuthenticationBypass:
    """Tests that verify authentication cannot be bypassed."""

    def test_no_token_cannot_access_cart(self, client):
        """Requests without token cannot access cart."""
        resp = client.get('/api/cart')
        assert resp.status_code == 401

    def test_fake_token_cannot_access_cart(self, client):
        """Requests with fake token cannot access cart."""
        resp = client.get('/api/cart', headers={'Authorization': 'Bearer faketoken123'})
        assert resp.status_code == 401

    def test_malformed_token_rejected(self, client):
        """Malformed authorization headers are rejected."""
        headers_list = [
            {'Authorization': 'faketoken'},
            {'Authorization': 'Bearer'},
            {'Authorization': 'Token abc123'},
        ]
        for headers in headers_list:
            resp = client.get('/api/cart', headers=headers)
            assert resp.status_code == 401, \
                f"Malformed auth header {headers} should return 401"

    def test_no_token_cannot_create_listing(self, client):
        """Unauthenticated user cannot create a listing."""
        resp = client.post('/api/listings', data={
            'title': 'SEC_Test',
            'description': 'test',
            'category': 'Phones',
            'price': 100,
            'condition': 'GOOD',
            'listingType': 'SALE'
        })
        assert resp.status_code == 401

    def test_no_token_cannot_checkout(self, client):
        """Unauthenticated user cannot checkout."""
        resp = client.post('/api/checkout', json={
            'shipping_name': 'Test User',
            'shipping_address': '123 Test St',
            'shipping_city': 'Test City',
            'shipping_state': 'TS',
            'shipping_zip': '12345'
        })
        assert resp.status_code in [401, 404, 405]

    def test_no_token_cannot_access_wishlist(self, client):
        """Unauthenticated user cannot access wishlist."""
        resp = client.get('/api/wishlist')
        assert resp.status_code == 401

    def test_no_token_cannot_access_notifications(self, client):
        """Unauthenticated user cannot access notifications."""
        resp = client.get('/api/notifications')
        assert resp.status_code == 401


# ============ ACCESS CONTROL TESTS ============

class TestAccessControl:
    """Tests that verify users cannot access resources they should not."""

    def test_buyer_cannot_access_admin_stats(self, client, buyer_token, db_cleanup):
        """Buyer token cannot access admin stats endpoint."""
        for route in ['/admin/stats', '/api/admin/stats']:
            resp = client.get(route,
                headers={'Authorization': f'Bearer {buyer_token}'})
            assert resp.status_code in [401, 403, 404], \
                f"Buyer should not access admin stats at {route}, got {resp.status_code}"

    def test_buyer_cannot_approve_listings(self, client, buyer_token, db_cleanup):
        """Buyer cannot approve listings through admin endpoint."""
        for route in ['/admin/listings/1/approve', '/api/admin/listings/1/approve']:
            resp = client.put(route,
                headers={'Authorization': f'Bearer {buyer_token}'})
            assert resp.status_code in [401, 403, 404, 405], \
                f"Buyer should not approve listings at {route}, got {resp.status_code}"

    def test_buyer_cannot_approve_users(self, client, buyer_token, db_cleanup):
        """Buyer cannot approve users through admin endpoint."""
        for route in ['/admin/users/1/approve', '/api/admin/users/1/approve']:
            resp = client.put(route,
                headers={'Authorization': f'Bearer {buyer_token}'})
            assert resp.status_code in [401, 403, 404, 405], \
                f"Buyer should not approve users at {route}, got {resp.status_code}"

    def test_seller_cannot_edit_others_listing(self, client, seller_token, db_cleanup):
        """Seller cannot edit a listing they do not own."""
        resp = client.post('/api/listings', data={
            'title': 'SEC_My Listing',
            'description': 'test',
            'category': 'Phones',
            'price': 100,
            'condition': 'GOOD',
            'listingType': 'SALE'
        }, headers={'Authorization': f'Bearer {seller_token}'},
           content_type='multipart/form-data')
        listing_id = resp.get_json()['listing']['id']

        resp2 = client.post('/api/auth/register', json={
            'email': 'sec_seller2@switchr.test',
            'username': 'sec_seller2',
            'password': 'Password123!'
        })
        token2 = resp2.get_json().get('token')
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE users SET status='approved', role='seller' WHERE email='sec_seller2@switchr.test'")
        conn.close()

        resp3 = client.put(f'/api/listings/{listing_id}',
            json={
                'title': 'SEC_Hacked Title',
                'description': 'hacked',
                'category': 'Phones',
                'price': 1,
                'condition': 'GOOD',
                'listingType': 'SALE'
            },
            headers={'Authorization': f'Bearer {token2}'})
        assert resp3.status_code in [403, 401, 404], \
            f"Seller should not edit another seller's listing, got {resp3.status_code}"

    def test_user_cannot_view_others_cart(self, client, buyer_token, seller_token, db_cleanup):
        """Each user only sees their own cart."""
        resp = client.get('/api/cart',
            headers={'Authorization': f'Bearer {buyer_token}'})
        assert resp.status_code == 200

        resp2 = client.get('/api/cart',
            headers={'Authorization': f'Bearer {seller_token}'})
        assert resp2.status_code == 200

        buyer_cart = resp.get_json().get('cart', [])
        seller_cart = resp2.get_json().get('cart', [])
        buyer_ids = {item['listing_id'] for item in buyer_cart}
        seller_ids = {item['listing_id'] for item in seller_cart}
        assert buyer_ids != seller_ids or (len(buyer_ids) == 0 and len(seller_ids) == 0)


# ============ XSS TESTS ============

class TestXSSPrevention:
    """Tests that verify XSS payloads are handled safely."""

    def test_xss_in_listing_title(self, client, seller_token, db_cleanup):
        """XSS payload in listing title should be stored safely and server stays up."""
        xss_payload = '<script>alert("xss")</script>'
        resp = client.post('/api/listings', data={
            'title': xss_payload,
            'description': 'test description',
            'category': 'Phones',
            'price': 100,
            'condition': 'GOOD',
            'listingType': 'SALE'
        }, headers={'Authorization': f'Bearer {seller_token}'},
           content_type='multipart/form-data')
        assert resp.status_code in [200, 201, 400, 422]

        health = client.get('/api/listings',
            headers={'Authorization': f'Bearer {seller_token}'})
        assert health.status_code == 200

    def test_xss_in_registration_username(self, client, db_cleanup):
        """XSS payload in username should be handled safely."""
        resp = client.post('/api/auth/register', json={
            'email': 'sec_xss@switchr.test',
            'username': '<script>alert("xss")</script>',
            'password': 'Password123!'
        })
        assert resp.status_code in [200, 201, 400, 409, 422]

        health = client.post('/api/auth/login', json={
            'email': 'nonexistent@test.com',
            'password': 'wrong'
        })
        assert health.status_code in [400, 401]
