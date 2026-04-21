from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from functools import wraps
import psycopg2
import psycopg2.extras
import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import uuid

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

load_dotenv()

# Configurable values - override via environment variables
MAX_UPLOAD_MB = int(os.getenv('MAX_UPLOAD_MB', '16'))
TAX_RATE = float(os.getenv('TAX_RATE', '0.08'))
JWT_EXPIRY_HOURS = int(os.getenv('JWT_EXPIRY_HOURS', '24'))
NOTIFICATIONS_PER_PAGE = int(os.getenv('NOTIFICATIONS_PER_PAGE', '20'))

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/switchr')

# Database connection
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

# Initialize database tables
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'user',
            status VARCHAR(20) DEFAULT 'pending',
            denial_reason TEXT,
            balance NUMERIC(10, 2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id SERIAL PRIMARY KEY,
            seller_id INTEGER REFERENCES users(id),
            title VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            category VARCHAR(50) NOT NULL,
            price NUMERIC(10, 2) NOT NULL,
            condition VARCHAR(20) NOT NULL,
            listing_type VARCHAR(10) NOT NULL,
            status VARCHAR(20) DEFAULT 'PENDING_APPROVAL',
            denial_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            listing_id INTEGER REFERENCES listings(id),
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, listing_id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            buyer_id INTEGER REFERENCES users(id),
            seller_id INTEGER REFERENCES users(id),
            listing_id INTEGER REFERENCES listings(id),
            title VARCHAR(100) NOT NULL,
            price NUMERIC(10, 2) NOT NULL,
            payment_method VARCHAR(50) DEFAULT 'card',
            status VARCHAR(20) DEFAULT 'COMPLETED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            buyer_id INTEGER REFERENCES users(id),
            subtotal NUMERIC(10,2) NOT NULL,
            tax_rate NUMERIC(5,4) DEFAULT 0.08,
            tax_amount NUMERIC(10,2) NOT NULL,
            total NUMERIC(10,2) NOT NULL,
            ship_first_name VARCHAR(100),
            ship_last_name VARCHAR(100),
            ship_address VARCHAR(255),
            ship_city VARCHAR(100),
            ship_state VARCHAR(50),
            ship_zip VARCHAR(20),
            bill_same_as_ship BOOLEAN DEFAULT TRUE,
            bill_first_name VARCHAR(100),
            bill_last_name VARCHAR(100),
            bill_address VARCHAR(255),
            bill_city VARCHAR(100),
            bill_state VARCHAR(50),
            bill_zip VARCHAR(20),
            card_last_four VARCHAR(4),
            card_name VARCHAR(100),
            status VARCHAR(20) DEFAULT 'COMPLETED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER REFERENCES orders(id),
            listing_id INTEGER REFERENCES listings(id),
            title VARCHAR(100) NOT NULL,
            price NUMERIC(10,2) NOT NULL,
            seller_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            message TEXT NOT NULL,
            type VARCHAR(50) DEFAULT 'INFO',
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            sender_id INTEGER REFERENCES users(id),
            receiver_id INTEGER REFERENCES users(id),
            offered_listing_id INTEGER REFERENCES listings(id),
            wanted_listing_id INTEGER REFERENCES listings(id),
            cash_offer NUMERIC(10, 2) DEFAULT 0.00,
            status VARCHAR(20) DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Add columns if tables already exist without them
    cur.execute('''
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'denial_reason'
            ) THEN
                ALTER TABLE listings ADD COLUMN denial_reason TEXT;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'status'
            ) THEN
                ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'denial_reason'
            ) THEN
                ALTER TABLE users ADD COLUMN denial_reason TEXT;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'balance'
            ) THEN
                ALTER TABLE users ADD COLUMN balance NUMERIC(10,2) DEFAULT 0.00;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'photo_urls'
            ) THEN
                ALTER TABLE listings ADD COLUMN photo_urls TEXT[] DEFAULT '{}';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'quantity'
            ) THEN
                ALTER TABLE listings ADD COLUMN quantity INTEGER DEFAULT 1;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'starting_price'
            ) THEN
                ALTER TABLE listings ADD COLUMN starting_price NUMERIC(10,2);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'auction_duration_days'
            ) THEN
                ALTER TABLE listings ADD COLUMN auction_duration_days INTEGER;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'auction_end_time'
            ) THEN
                ALTER TABLE listings ADD COLUMN auction_end_time TIMESTAMP;
            END IF;
        END $$;
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bids (
            id SERIAL PRIMARY KEY,
            listing_id INTEGER REFERENCES listings(id),
            bidder_id INTEGER REFERENCES users(id),
            amount NUMERIC(10, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        ALTER TABLE listings ALTER COLUMN status SET DEFAULT 'PENDING_APPROVAL'
    ''')
    conn.close()

# Token required decorator - just checks valid login
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = payload['user_id']
            request.user_email = payload['email']
            request.user_role = payload['role']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated

# Approved user required - must be logged in AND account approved by admin
def approved_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = payload['user_id']
            request.user_email = payload['email']
            request.user_role = payload['role']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        # Check account approval status from DB
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT status FROM users WHERE id = %s', (request.user_id,))
        user = cur.fetchone()
        conn.close()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user['status'] != 'approved':
            return jsonify({'error': 'Account not yet approved by admin'}), 403

        return f(*args, **kwargs)
    return decorated

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = payload['user_id']
            request.user_email = payload['email']
            request.user_role = payload['role']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        if request.user_role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        return f(*args, **kwargs)
    return decorated

# Generate JWT token
def generate_token(user):
    payload = {
        'user_id': user['id'],
        'email': user['email'],
        'role': user['role'],
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

# Helper to format listing dates for JSON
def format_listing(row):
    d = dict(row)
    if d.get('created_at'):
        d['created_at'] = d['created_at'].strftime('%Y-%m-%d')
    if d.get('updated_at'):
        d['updated_at'] = d['updated_at'].strftime('%Y-%m-%d')
    if d.get('auction_end_time'):
        d['auction_end_time'] = d['auction_end_time'].strftime('%Y-%m-%dT%H:%M:%SZ')
    return d
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============ AUTH ROUTES ============

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    email = data.get('email')
    username = data.get('username')
    password = data.get('password')

    if not email or not username or not password:
        return jsonify({'error': 'Email, username, and password are required'}), 400

    role = 'user'  # unified role - all users can buy, sell, and trade

    status = 'pending'  # new accounts require admin approval

    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            'INSERT INTO users (email, username, password_hash, role, status) VALUES (%s, %s, %s, %s, %s) RETURNING id, email, username, role, status',
            (email, username, password_hash, role, status)
        )
        user = cur.fetchone()
        conn.close()

        token = generate_token(user)
        return jsonify({
            'token': token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'username': user['username'],
                'role': user['role'],
                'status': user['status']
            }
        }), 201

    except psycopg2.errors.UniqueViolation:
        return jsonify({'error': 'Email or username already exists'}), 409


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM users WHERE email = %s', (email,))
    user = cur.fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = generate_token(user)
    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'username': user['username'],
            'role': user['role'],
            'status': user['status'],
            'denial_reason': user.get('denial_reason')
        }
    })


@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT id, email, username, role, status, denial_reason, balance, created_at FROM users WHERE id = %s', (request.user_id,))
    user = cur.fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user})


# ============ LISTING ROUTES ============

# Create listing - requires approved account
@app.route('/api/listings', methods=['POST'])
@approved_required
def create_listing():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '')
    price = request.form.get('price')
    condition = request.form.get('condition', '')
    listing_type = request.form.get('listingType', '')
    quantity = request.form.get('quantity', 1)

    starting_price = None
    auction_duration_days = None
    if listing_type == 'AUCTION':
        try:
            starting_price = float(request.form.get('starting_price', 0))
            auction_duration_days = int(request.form.get('auction_duration_days', 3))
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid auction fields'}), 400
        if starting_price <= 0:
            return jsonify({'error': 'Starting price must be positive'}), 400
        if auction_duration_days not in (1, 3, 7):
            return jsonify({'error': 'Auction duration must be 1, 3, or 7 days'}), 400
        price = starting_price

    if not title or not description or not category or not price or not condition or not listing_type:
        return jsonify({'error': 'All fields are required'}), 400

    if len(title) > 100:
        return jsonify({'error': 'Title must be 100 characters or less'}), 400

    # Handle photo uploads
    photo_urls = []
    files = request.files.getlist('photos')
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_urls.append(f"/uploads/{filename}")

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''INSERT INTO listings
            (seller_id, title, description, category, price, condition, listing_type, status, photo_urls, quantity, starting_price, auction_duration_days)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING_APPROVAL', %s, %s, %s, %s)
            RETURNING *''',
            (request.user_id, title, description, category, float(price),
            condition, listing_type, photo_urls, int(quantity), starting_price, auction_duration_days)
        )
        listing = cur.fetchone()
        conn.close()
        return jsonify({'message': 'Listing submitted for approval', 'listing': format_listing(listing)}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get seller's own listings - requires approved account
@app.route('/api/listings', methods=['GET'])
@approved_required
def get_seller_listings():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            'SELECT * FROM listings WHERE seller_id = %s ORDER BY created_at DESC',
            (request.user_id,)
        )
        rows = cur.fetchall()
        conn.close()
        listings = [format_listing(row) for row in rows]
        return jsonify({'listings': listings})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Edit a listing - seller can edit their own listing
@app.route('/api/listings/<int:listing_id>', methods=['PUT'])
@approved_required
def edit_listing(listing_id):
    data = request.get_json()

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get the existing listing and verify ownership
        cur.execute('SELECT * FROM listings WHERE id = %s AND seller_id = %s', (listing_id, request.user_id))
        listing = cur.fetchone()

        if not listing:
            conn.close()
            return jsonify({'error': 'Listing not found'}), 404

        title = data.get('title', listing['title']).strip()
        description = data.get('description', listing['description']).strip()
        category = data.get('category', listing['category'])
        price = data.get('price', float(listing['price']))
        condition = data.get('condition', listing['condition'])
        listing_type = data.get('listingType', listing['listing_type'])

        if len(title) > 100:
            conn.close()
            return jsonify({'error': 'Title must be 100 characters or less'}), 400

        # If listing is ACTIVE and title or description changed, needs re-approval
        new_status = listing['status']
        if listing['status'] == 'ACTIVE':
            if title != listing['title'] or description != listing['description']:
                new_status = 'PENDING_APPROVAL'

        # If listing is PENDING_APPROVAL or DENIED, stays PENDING_APPROVAL (free edits)
        if listing['status'] in ('PENDING_APPROVAL', 'DENIED'):
            new_status = 'PENDING_APPROVAL'

        cur.execute(
            '''UPDATE listings
               SET title = %s, description = %s, category = %s, price = %s,
                   condition = %s, listing_type = %s, status = %s,
                   denial_reason = NULL, updated_at = CURRENT_TIMESTAMP
               WHERE id = %s
               RETURNING *''',
            (title, description, category, float(price), condition, listing_type, new_status, listing_id)
        )
        updated = cur.fetchone()
        conn.close()

        msg = 'Listing updated'
        if new_status == 'PENDING_APPROVAL' and listing['status'] == 'ACTIVE':
            msg = 'Listing updated and sent back for approval'

        return jsonify({'message': msg, 'listing': format_listing(updated)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get a single listing by ID (for edit form)
@app.route('/api/listings/<int:listing_id>', methods=['GET'])
@approved_required
def get_listing(listing_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM listings WHERE id = %s AND seller_id = %s', (listing_id, request.user_id))
        listing = cur.fetchone()
        conn.close()

        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        return jsonify({'listing': format_listing(listing)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Public route - buyers browse only ACTIVE (approved) listings
@app.route('/api/listings/browse', methods=['GET'])
def browse_listings():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''SELECT l.*, u.username as seller_username
               FROM listings l
               JOIN users u ON l.seller_id = u.id
               WHERE l.status = 'ACTIVE'
               ORDER BY l.created_at DESC'''
        )
        rows = cur.fetchall()
        conn.close()
        listings = [format_listing(row) for row in rows]
        return jsonify({'listings': listings})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ ADMIN ROUTES ============

# Get platform stats
@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute('SELECT COUNT(*) as count FROM users')
        total_users = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM users WHERE status = 'pending'")
        pending_users = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM listings WHERE status = 'ACTIVE'")
        active_listings = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM listings WHERE status = 'PENDING_APPROVAL'")
        pending_approvals = cur.fetchone()['count']

        cur.execute('SELECT COUNT(*) as count FROM listings')
        total_listings = cur.fetchone()['count']

        conn.close()

        return jsonify({
            'total_users': total_users,
            'pending_users': pending_users,
            'active_listings': active_listings,
            'pending_approvals': pending_approvals,
            'total_listings': total_listings
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get all users (admin oversight)
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    status_filter = request.args.get('status', '')
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if status_filter:
            cur.execute(
                'SELECT id, email, username, role, status, denial_reason, created_at FROM users WHERE status = %s ORDER BY created_at DESC',
                (status_filter,)
            )
        else:
            cur.execute('SELECT id, email, username, role, status, denial_reason, created_at FROM users ORDER BY created_at DESC')

        rows = cur.fetchall()
        conn.close()

        users = []
        for row in rows:
            d = dict(row)
            if d.get('created_at'):
                d['created_at'] = d['created_at'].strftime('%Y-%m-%d')
            users.append(d)

        return jsonify({'users': users})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Approve a user
@app.route('/api/admin/users/<int:user_id>/approve', methods=['PUT'])
@admin_required
def approve_user(user_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''UPDATE users
               SET status = 'approved', denial_reason = NULL
               WHERE id = %s
               RETURNING id, email, username, role, status''',
            (user_id,)
        )
        user = cur.fetchone()
        conn.close()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'message': 'User approved', 'user': dict(user)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Deny a user
@app.route('/api/admin/users/<int:user_id>/deny', methods=['PUT'])
@admin_required
def deny_user(user_id):
    data = request.get_json() or {}
    reason = data.get('reason', '').strip()

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''UPDATE users
               SET status = 'denied', denial_reason = %s
               WHERE id = %s
               RETURNING id, email, username, role, status, denial_reason''',
            (reason or None, user_id)
        )
        user = cur.fetchone()
        conn.close()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'message': 'User denied', 'user': dict(user)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get all listings (admin oversight)
@app.route('/api/admin/listings', methods=['GET'])
@admin_required
def admin_get_listings():
    status_filter = request.args.get('status', '')
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if status_filter:
            cur.execute(
                '''SELECT l.*, u.username as seller_username
                   FROM listings l
                   JOIN users u ON l.seller_id = u.id
                   WHERE l.status = %s
                   ORDER BY l.created_at DESC''',
                (status_filter,)
            )
        else:
            cur.execute(
                '''SELECT l.*, u.username as seller_username
                   FROM listings l
                   JOIN users u ON l.seller_id = u.id
                   ORDER BY l.created_at DESC'''
            )

        rows = cur.fetchall()
        conn.close()
        listings = [format_listing(row) for row in rows]
        return jsonify({'listings': listings})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Approve a listing
@app.route('/api/admin/listings/<int:listing_id>/approve', methods=['PUT'])
@admin_required
def approve_listing(listing_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM listings WHERE id = %s', (listing_id,))
        existing = cur.fetchone()
        if not existing:
            conn.close()
            return jsonify({'error': 'Listing not found'}), 404

        if existing['listing_type'] == 'AUCTION' and not existing.get('auction_end_time'):
            duration_days = existing.get('auction_duration_days') or 3
            duration_hours = duration_days * 24
            cur.execute(
                '''UPDATE listings
                   SET status = 'ACTIVE', denial_reason = NULL,
                       auction_end_time = CURRENT_TIMESTAMP + (%s || ' hours')::INTERVAL,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s RETURNING *''',
                (str(duration_hours), listing_id)
            )
        else:
            cur.execute(
                '''UPDATE listings
                   SET status = 'ACTIVE', denial_reason = NULL, updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s RETURNING *''',
                (listing_id,)
            )
        listing = cur.fetchone()
        conn.close()

        return jsonify({'message': 'Listing approved', 'listing': format_listing(listing)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Deny a listing
@app.route('/api/admin/listings/<int:listing_id>/deny', methods=['PUT'])
@admin_required
def deny_listing(listing_id):
    data = request.get_json()
    reason = data.get('reason', '').strip()

    if not reason:
        return jsonify({'error': 'Denial reason is required'}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''UPDATE listings
               SET status = 'DENIED', denial_reason = %s, updated_at = CURRENT_TIMESTAMP
               WHERE id = %s
               RETURNING *''',
            (reason, listing_id)
        )
        listing = cur.fetchone()
        conn.close()

        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        return jsonify({'message': 'Listing denied', 'listing': format_listing(listing)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Delist a listing - marks as DELETED, does not remove from database
@app.route('/api/listings/<int:listing_id>', methods=['DELETE'])
@approved_required
def delete_listing(listing_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM listings WHERE id = %s AND seller_id = %s', (listing_id, request.user_id))
        listing = cur.fetchone()

        if not listing:
            conn.close()
            return jsonify({'error': 'Listing not found'}), 404

        cur.execute(
            '''UPDATE listings SET status = 'DELETED', updated_at = CURRENT_TIMESTAMP
               WHERE id = %s RETURNING *''',
            (listing_id,)
        )
        conn.close()
        return jsonify({'message': 'Listing removed successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Public route - get single active listing by ID for buyers
@app.route('/api/listings/browse/<int:listing_id>', methods=['GET'])
def get_browse_listing(listing_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        settle_auction(cur, listing_id)
        cur.execute(
            '''SELECT l.*, u.username as seller_username
               FROM listings l
               JOIN users u ON l.seller_id = u.id
               WHERE l.id = %s AND l.status = 'ACTIVE' ''',
            (listing_id,)
        )
        listing = cur.fetchone()
        conn.close()

        if not listing:
            return jsonify({'error': 'Listing not found'}), 404

        return jsonify({'listing': format_listing(listing)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ CART ROUTES ============

@app.route('/api/cart', methods=['GET'])
@token_required
def get_cart():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''SELECT c.id, c.added_at, l.id as listing_id, l.title, l.price,
               l.condition, l.listing_type, l.category, u.username as seller_username
               FROM cart c
               JOIN listings l ON c.listing_id = l.id
               JOIN users u ON l.seller_id = u.id
               WHERE c.user_id = %s AND l.status = 'ACTIVE'
               ORDER BY c.added_at DESC''',
            (request.user_id,)
        )
        rows = cur.fetchall()
        conn.close()
        items = []
        for row in rows:
            d = dict(row)
            if d.get('added_at'):
                d['added_at'] = d['added_at'].strftime('%Y-%m-%d')
            items.append(d)
        return jsonify({'cart': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cart', methods=['POST'])
@token_required
def add_to_cart():
    data = request.get_json()
    listing_id = data.get('listing_id')

    if not listing_id:
        return jsonify({'error': 'listing_id is required'}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check listing exists and is active
        cur.execute('SELECT * FROM listings WHERE id = %s AND status = %s', (listing_id, 'ACTIVE'))
        listing = cur.fetchone()

        if not listing:
            conn.close()
            return jsonify({'error': 'Listing not found or not available'}), 404

        # Cannot add your own listing to cart
        if listing['seller_id'] == request.user_id:
            conn.close()
            return jsonify({'error': 'You cannot add your own listing to cart'}), 400

        cur.execute(
            'INSERT INTO cart (user_id, listing_id) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING *',
            (request.user_id, listing_id)
        )
        conn.close()
        return jsonify({'message': 'Added to cart'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cart/<int:listing_id>', methods=['DELETE'])
@token_required
def remove_from_cart(listing_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'DELETE FROM cart WHERE user_id = %s AND listing_id = %s',
            (request.user_id, listing_id)
        )
        conn.close()
        return jsonify({'message': 'Removed from cart'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ WALLET ROUTES ============

# Add funds to account
@app.route('/api/wallet/add', methods=['POST'])
@token_required
def add_funds():
    data = request.get_json()
    amount = data.get('amount')

    if not amount or float(amount) <= 0:
        return jsonify({'error': 'Amount must be greater than 0'}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            'UPDATE users SET balance = balance + %s WHERE id = %s RETURNING balance',
            (float(amount), request.user_id)
        )
        result = cur.fetchone()
        conn.close()

        return jsonify({'message': 'Funds added', 'balance': float(result['balance'])})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get current balance
@app.route('/api/wallet/balance', methods=['GET'])
@token_required
def get_balance():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT balance FROM users WHERE id = %s', (request.user_id,))
        result = cur.fetchone()
        conn.close()

        return jsonify({'balance': float(result['balance'])})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
            SELECT * FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        ''', (request.user_id, NOTIFICATIONS_PER_PAGE))
        rows = cur.fetchall()
        conn.close()
        notifs = []
        for row in rows:
            d = dict(row)
            if d.get('created_at'):
                d['created_at'] = d['created_at'].strftime('%Y-%m-%d %H:%M')
            notifs.append(d)
        return jsonify({'notifications': notifs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ TRANSACTION ROUTES ============

# Checkout - buy items in cart, create order, transactions, balance transfer
@app.route('/api/checkout', methods=['POST'])
@approved_required
def checkout():
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get cart items
        cur.execute('''
            SELECT c.listing_id, l.title, l.price, l.seller_id, l.status
            FROM cart c
            JOIN listings l ON c.listing_id = l.id
            WHERE c.user_id = %s
        ''', (request.user_id,))
        cart_items = cur.fetchall()

        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400

        # Check all listings still active
        for item in cart_items:
            if item['status'] != 'ACTIVE':
                return jsonify({'error': 'Listing "' + item['title'] + '" is no longer available'}), 400

        # Calculate totals
        subtotal = sum(float(item['price']) for item in cart_items)
        tax_amount = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax_amount, 2)

        # Check buyer has enough balance
        cur.execute('SELECT balance FROM users WHERE id = %s', (request.user_id,))
        buyer = cur.fetchone()

        if float(buyer['balance']) < total:
            return jsonify({'error': 'Insufficient balance. You need $' + '{:.2f}'.format(total) + ' but have $' + '{:.2f}'.format(float(buyer['balance']))}), 400

        # Deduct from buyer
        cur.execute(
            'UPDATE users SET balance = balance - %s WHERE id = %s',
            (total, request.user_id)
        )

        # Billing address
        bill_same = data.get('billSameAsShip', True)
        card_num = data.get('cardNumber', '').replace(' ', '')
        card_last_four = card_num[-4:] if len(card_num) >= 4 else '0000'

        # Create order
        cur.execute('''
            INSERT INTO orders (
                buyer_id, subtotal, tax_rate, tax_amount, total,
                ship_first_name, ship_last_name, ship_address,
                ship_city, ship_state, ship_zip,
                bill_same_as_ship,
                bill_first_name, bill_last_name, bill_address,
                bill_city, bill_state, bill_zip,
                card_last_four, card_name, status
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, 'COMPLETED'
            ) RETURNING id
        ''', (
            request.user_id, subtotal, TAX_RATE, tax_amount, total,
            data.get('firstName'), data.get('lastName'), data.get('address'),
            data.get('city'), data.get('state'), data.get('zip'),
            bill_same,
            data.get('firstName') if bill_same else data.get('billFirstName'),
            data.get('lastName') if bill_same else data.get('billLastName'),
            data.get('address') if bill_same else data.get('billAddress'),
            data.get('city') if bill_same else data.get('billCity'),
            data.get('state') if bill_same else data.get('billState'),
            data.get('zip') if bill_same else data.get('billZip'),
            card_last_four, data.get('cardName')
        ))
        order = cur.fetchone()
        order_id = order['id']

        transaction_ids = []
        seller_ids = set()

        for item in cart_items:
            # Create order item
            cur.execute('''
                INSERT INTO order_items (order_id, listing_id, title, price, seller_id)
                VALUES (%s, %s, %s, %s, %s)
            ''', (order_id, item['listing_id'], item['title'], item['price'], item['seller_id']))

            # Create transaction record
            cur.execute(
                '''INSERT INTO transactions (buyer_id, seller_id, listing_id, title, price, payment_method)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id''',
                (request.user_id, item['seller_id'], item['listing_id'],
                 item['title'], float(item['price']), 'balance')
            )
            txn = cur.fetchone()
            transaction_ids.append(txn['id'])

            # Mark listing as SOLD
            cur.execute("UPDATE listings SET quantity = quantity - 1 WHERE id=%s", (item['listing_id'],))
            cur.execute("UPDATE listings SET status='SOLD', updated_at = CURRENT_TIMESTAMP WHERE id=%s AND quantity <= 0", (item['listing_id'],))

            # Credit seller
            cur.execute(
                'UPDATE users SET balance = balance + %s WHERE id = %s',
                (float(item['price']), item['seller_id'])
            )

            seller_ids.add(item['seller_id'])

        # Notify each seller
        cur.execute('SELECT username FROM users WHERE id = %s', (request.user_id,))
        buyer_info = cur.fetchone()
        buyer_username = buyer_info['username']
        for seller_id in seller_ids:
            cur.execute('''
                INSERT INTO notifications (user_id, message, type)
                VALUES (%s, %s, 'SALE')
            ''', (seller_id, 'Your item was purchased by ' + buyer_username + '! Order #' + str(order_id)))

        # Notify buyer that order was confirmed
        cur.execute('''
            INSERT INTO notifications (user_id, message, type)
            VALUES (%s, %s, 'PURCHASE')
        ''', (request.user_id, 'Your order #' + str(order_id) + ' has been confirmed! Total paid: $' + str(total)))

        # Clear cart
        cur.execute("DELETE FROM cart WHERE user_id=%s", (request.user_id,))

        return jsonify({
            'message': 'Order placed successfully',
            'order_id': order_id,
            'total': total,
            'transaction_ids': transaction_ids
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# Get buyer's purchase history (invoices)
@app.route('/api/transactions/purchases', methods=['GET'])
@token_required
def get_purchases():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''SELECT t.*, u.username as seller_username
               FROM transactions t
               JOIN users u ON t.seller_id = u.id
               WHERE t.buyer_id = %s
               ORDER BY t.created_at DESC''',
            (request.user_id,)
        )
        rows = cur.fetchall()
        conn.close()

        transactions = []
        for row in rows:
            d = dict(row)
            if d.get('created_at'):
                d['created_at'] = d['created_at'].strftime('%Y-%m-%d %H:%M')
            transactions.append(d)

        return jsonify({'transactions': transactions})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get seller's sales history (invoices)
@app.route('/api/transactions/sales', methods=['GET'])
@token_required
def get_sales():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''SELECT t.*, u.username as buyer_username
               FROM transactions t
               JOIN users u ON t.buyer_id = u.id
               WHERE t.seller_id = %s
               ORDER BY t.created_at DESC''',
            (request.user_id,)
        )
        rows = cur.fetchall()
        conn.close()

        transactions = []
        for row in rows:
            d = dict(row)
            if d.get('created_at'):
                d['created_at'] = d['created_at'].strftime('%Y-%m-%d %H:%M')
            transactions.append(d)

        return jsonify({'transactions': transactions})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get a single transaction/invoice by ID
@app.route('/api/transactions/<int:txn_id>', methods=['GET'])
@token_required
def get_transaction(txn_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''SELECT t.*,
                      buyer.username as buyer_username, buyer.email as buyer_email,
                      seller.username as seller_username, seller.email as seller_email
               FROM transactions t
               JOIN users buyer ON t.buyer_id = buyer.id
               JOIN users seller ON t.seller_id = seller.id
               WHERE t.id = %s AND (t.buyer_id = %s OR t.seller_id = %s)''',
            (txn_id, request.user_id, request.user_id)
        )
        txn = cur.fetchone()
        conn.close()

        if not txn:
            return jsonify({'error': 'Transaction not found'}), 404

        d = dict(txn)
        if d.get('created_at'):
            d['created_at'] = d['created_at'].strftime('%Y-%m-%d %H:%M')

        return jsonify({'transaction': d})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ TRADE ROUTES ============

# Send a trade offer
@app.route('/api/trades', methods=['POST'])
@approved_required
def create_trade():
    data = request.get_json()
    offered_listing_id = data.get('offered_listing_id')
    wanted_listing_id = data.get('wanted_listing_id')
    cash_offer = float(data.get('cash_offer', 0))

    if not offered_listing_id or not wanted_listing_id:
        return jsonify({'error': 'Both offered and wanted listing IDs are required'}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Verify sender owns the offered listing and it's ACTIVE
        cur.execute('SELECT * FROM listings WHERE id = %s AND seller_id = %s AND status = %s',
                    (offered_listing_id, request.user_id, 'ACTIVE'))
        offered = cur.fetchone()
        if not offered:
            conn.close()
            return jsonify({'error': 'Your offered listing is not available'}), 400

        # Verify wanted listing exists and is ACTIVE
        cur.execute('SELECT * FROM listings WHERE id = %s AND status = %s', (wanted_listing_id, 'ACTIVE'))
        wanted = cur.fetchone()
        if not wanted:
            conn.close()
            return jsonify({'error': 'The listing you want is not available'}), 400

        # Can't trade with yourself
        if wanted['seller_id'] == request.user_id:
            conn.close()
            return jsonify({'error': 'You cannot trade with yourself'}), 400

        # Check balance if cash is offered
        if cash_offer > 0:
            cur.execute('SELECT balance FROM users WHERE id = %s', (request.user_id,))
            sender = cur.fetchone()
            if float(sender['balance']) < cash_offer:
                conn.close()
                return jsonify({'error': 'Insufficient balance for cash portion'}), 400

        # Create trade
        cur.execute(
            '''INSERT INTO trades (sender_id, receiver_id, offered_listing_id, wanted_listing_id, cash_offer)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id''',
            (request.user_id, wanted['seller_id'], offered_listing_id, wanted_listing_id, cash_offer)
        )
        trade = cur.fetchone()

        # Notify the receiver
        cur.execute('SELECT username FROM users WHERE id = %s', (request.user_id,))
        sender_info = cur.fetchone()
        msg = sender_info['username'] + ' wants to trade "' + offered['title'] + '" for your "' + wanted['title'] + '"'
        if cash_offer > 0:
            msg += ' + $' + '{:.2f}'.format(cash_offer) + ' cash'
        cur.execute(
            "INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, 'TRADE')",
            (wanted['seller_id'], msg)
        )

        conn.close()
        return jsonify({'message': 'Trade offer sent', 'trade_id': trade['id']}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get my trade offers (incoming and outgoing)
@app.route('/api/trades', methods=['GET'])
@token_required
def get_trades():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Incoming trades (I'm the receiver)
        cur.execute('''
            SELECT t.*,
                   sender.username as sender_username,
                   ol.title as offered_title, ol.price as offered_price, ol.condition as offered_condition,
                   wl.title as wanted_title, wl.price as wanted_price
            FROM trades t
            JOIN users sender ON t.sender_id = sender.id
            JOIN listings ol ON t.offered_listing_id = ol.id
            JOIN listings wl ON t.wanted_listing_id = wl.id
            WHERE t.receiver_id = %s
            ORDER BY t.created_at DESC
        ''', (request.user_id,))
        incoming = cur.fetchall()

        # Outgoing trades (I'm the sender)
        cur.execute('''
            SELECT t.*,
                   receiver.username as receiver_username,
                   ol.title as offered_title, ol.price as offered_price, ol.condition as offered_condition,
                   wl.title as wanted_title, wl.price as wanted_price
            FROM trades t
            JOIN users receiver ON t.receiver_id = receiver.id
            JOIN listings ol ON t.offered_listing_id = ol.id
            JOIN listings wl ON t.wanted_listing_id = wl.id
            WHERE t.sender_id = %s
            ORDER BY t.created_at DESC
        ''', (request.user_id,))
        outgoing = cur.fetchall()

        conn.close()

        def fmt(rows):
            result = []
            for row in rows:
                d = dict(row)
                if d.get('created_at'):
                    d['created_at'] = d['created_at'].strftime('%Y-%m-%d %H:%M')
                if d.get('updated_at'):
                    d['updated_at'] = d['updated_at'].strftime('%Y-%m-%d %H:%M')
                result.append(d)
            return result

        return jsonify({'incoming': fmt(incoming), 'outgoing': fmt(outgoing)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Accept a trade
@app.route('/api/trades/<int:trade_id>/accept', methods=['PUT'])
@approved_required
def accept_trade(trade_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('SELECT * FROM trades WHERE id = %s AND receiver_id = %s', (trade_id, request.user_id))
        trade = cur.fetchone()

        if not trade:
            return jsonify({'error': 'Trade not found'}), 404
        if trade['status'] != 'PENDING':
            return jsonify({'error': 'Trade is no longer pending'}), 400

        # Verify both listings still ACTIVE
        cur.execute('SELECT * FROM listings WHERE id = %s AND status = %s', (trade['offered_listing_id'], 'ACTIVE'))
        offered = cur.fetchone()
        cur.execute('SELECT * FROM listings WHERE id = %s AND status = %s', (trade['wanted_listing_id'], 'ACTIVE'))
        wanted = cur.fetchone()

        if not offered or not wanted:
            return jsonify({'error': 'One or both listings are no longer available'}), 400

        cash = float(trade['cash_offer'])

        # Handle cash portion if any
        if cash > 0:
            cur.execute('SELECT balance FROM users WHERE id = %s', (trade['sender_id'],))
            sender_bal = cur.fetchone()
            if float(sender_bal['balance']) < cash:
                return jsonify({'error': 'Sender has insufficient balance for cash portion'}), 400
            cur.execute('UPDATE users SET balance = balance - %s WHERE id = %s', (cash, trade['sender_id']))
            cur.execute('UPDATE users SET balance = balance + %s WHERE id = %s', (cash, trade['receiver_id']))

        # Swap ownership: offered listing goes to receiver, wanted listing goes to sender
        cur.execute('UPDATE listings SET seller_id = %s, status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s',
                    (trade['receiver_id'], 'TRADED', trade['offered_listing_id']))
        cur.execute('UPDATE listings SET seller_id = %s, status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s',
                    (trade['sender_id'], 'TRADED', trade['wanted_listing_id']))

        # Mark trade as accepted
        cur.execute("UPDATE trades SET status = 'ACCEPTED', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (trade_id,))

        # Notify sender
        cur.execute('SELECT username FROM users WHERE id = %s', (request.user_id,))
        receiver_info = cur.fetchone()
        cur.execute(
            "INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, 'TRADE')",
            (trade['sender_id'], receiver_info['username'] + ' accepted your trade offer! Trade #' + str(trade_id))
        )

        return jsonify({'message': 'Trade accepted'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# Reject a trade
@app.route('/api/trades/<int:trade_id>/reject', methods=['PUT'])
@token_required
def reject_trade(trade_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('SELECT * FROM trades WHERE id = %s AND receiver_id = %s', (trade_id, request.user_id))
        trade = cur.fetchone()

        if not trade:
            return jsonify({'error': 'Trade not found'}), 404
        if trade['status'] != 'PENDING':
            return jsonify({'error': 'Trade is no longer pending'}), 400

        cur.execute("UPDATE trades SET status = 'REJECTED', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (trade_id,))

        # Notify sender
        cur.execute('SELECT username FROM users WHERE id = %s', (request.user_id,))
        receiver_info = cur.fetchone()
        cur.execute(
            "INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, 'TRADE')",
            (trade['sender_id'], receiver_info['username'] + ' rejected your trade offer. Trade #' + str(trade_id))
        )

        return jsonify({'message': 'Trade rejected'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# Cancel a trade (sender cancels their own outgoing trade)
@app.route('/api/trades/<int:trade_id>/cancel', methods=['PUT'])
@token_required
def cancel_trade(trade_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('SELECT * FROM trades WHERE id = %s AND sender_id = %s', (trade_id, request.user_id))
        trade = cur.fetchone()

        if not trade:
            return jsonify({'error': 'Trade not found'}), 404
        if trade['status'] != 'PENDING':
            return jsonify({'error': 'Trade is no longer pending'}), 400

        cur.execute("UPDATE trades SET status = 'CANCELLED', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (trade_id,))

        return jsonify({'message': 'Trade cancelled'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# Get sender's own active listings (for trade offer modal)
@app.route('/api/listings/mine', methods=['GET'])
@token_required
def get_my_listings():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, title, price, condition, listing_type FROM listings WHERE seller_id = %s AND status = 'ACTIVE' ORDER BY title",
            (request.user_id,)
        )
        rows = cur.fetchall()
        conn.close()
        return jsonify({'listings': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Return a purchase - buyer initiates, refunds balance
@app.route('/api/transactions/<int:txn_id>/return', methods=['PUT'])
@token_required
def return_transaction(txn_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get the transaction, must belong to buyer
        cur.execute('SELECT * FROM transactions WHERE id = %s AND buyer_id = %s', (txn_id, request.user_id))
        txn = cur.fetchone()

        if not txn:
            return jsonify({'error': 'Transaction not found'}), 404

        if txn['status'] == 'RETURNED':
            return jsonify({'error': 'This item has already been returned'}), 400

        price = float(txn['price'])

        # Refund buyer
        cur.execute('UPDATE users SET balance = balance + %s WHERE id = %s', (price, txn['buyer_id']))

        # Deduct from seller
        cur.execute('UPDATE users SET balance = balance - %s WHERE id = %s', (price, txn['seller_id']))

        # Mark transaction as RETURNED
        cur.execute("UPDATE transactions SET status = 'RETURNED' WHERE id = %s", (txn_id,))

        # Set listing back to ACTIVE
        cur.execute("UPDATE listings SET status = 'ACTIVE', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (txn['listing_id'],))

        # Notify seller
        cur.execute('SELECT username FROM users WHERE id = %s', (request.user_id,))
        buyer = cur.fetchone()
        cur.execute('''
            INSERT INTO notifications (user_id, message, type)
            VALUES (%s, %s, 'RETURN')
        ''', (txn['seller_id'], buyer['username'] + ' returned "' + txn['title'] + '". $' + '{:.2f}'.format(price) + ' has been deducted from your balance.'))

        return jsonify({'message': 'Return processed. $' + '{:.2f}'.format(price) + ' refunded to your balance.'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ============ AUCTION ROUTES ============

def settle_auction(cur, listing_id):
    """Settle an auction if it has ended. Idempotent. Caller manages connection."""
    cur.execute('SELECT * FROM listings WHERE id = %s', (listing_id,))
    listing = cur.fetchone()
    if not listing or listing['listing_type'] != 'AUCTION':
        return
    if listing['status'] != 'ACTIVE':
        return
    if not listing['auction_end_time'] or datetime.utcnow() < listing['auction_end_time']:
        return

    cur.execute(
        '''SELECT b.bidder_id, b.amount, u.username
           FROM bids b JOIN users u ON u.id = b.bidder_id
           WHERE b.listing_id = %s
           ORDER BY b.amount DESC, b.created_at ASC LIMIT 1''',
        (listing_id,)
    )
    winner = cur.fetchone()

    if winner:
        cur.execute("UPDATE listings SET status = 'SOLD', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (listing_id,))
        cur.execute(
            '''INSERT INTO transactions (buyer_id, seller_id, listing_id, title, price, status)
               VALUES (%s, %s, %s, %s, %s, 'COMPLETED')''',
            (winner['bidder_id'], listing['seller_id'], listing_id, listing['title'], float(winner['amount']))
        )
        win_msg = 'You won the auction for "' + listing['title'] + '" at $' + '{:.2f}'.format(float(winner['amount']))
        sell_msg = 'Your auction "' + listing['title'] + '" sold to ' + winner['username'] + ' for $' + '{:.2f}'.format(float(winner['amount']))
        cur.execute("INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, 'INFO')", (winner['bidder_id'], win_msg))
        cur.execute("INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, 'INFO')", (listing['seller_id'], sell_msg))
    else:
        cur.execute("UPDATE listings SET status = 'ENDED', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (listing_id,))
        cur.execute(
            "INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, 'INFO')",
            (listing['seller_id'], 'Your auction "' + listing['title'] + '" ended with no bids')
        )


@app.route('/api/auctions', methods=['GET'])
def list_auctions():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Lazy settle any expired auctions
        cur.execute(
            '''SELECT id FROM listings
               WHERE listing_type = 'AUCTION' AND status = 'ACTIVE'
                 AND auction_end_time IS NOT NULL AND auction_end_time <= CURRENT_TIMESTAMP'''
        )
        for row in cur.fetchall():
            settle_auction(cur, row['id'])

        cur.execute(
            '''SELECT l.*, u.username as seller_username
               FROM listings l JOIN users u ON l.seller_id = u.id
               WHERE l.listing_type = 'AUCTION' AND l.status = 'ACTIVE'
                 AND l.auction_end_time > CURRENT_TIMESTAMP
               ORDER BY l.auction_end_time ASC'''
        )
        rows = cur.fetchall()
        conn.close()
        return jsonify({'auctions': [format_listing(r) for r in rows]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/listings/<int:listing_id>/bid', methods=['POST'])
@approved_required
def place_bid(listing_id):
    data = request.get_json() or {}
    try:
        amount = float(data.get('amount', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid amount'}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute('SELECT * FROM listings WHERE id = %s', (listing_id,))
        listing = cur.fetchone()
        if not listing:
            conn.close()
            return jsonify({'error': 'Listing not found'}), 404
        if listing['listing_type'] != 'AUCTION':
            conn.close()
            return jsonify({'error': 'Not an auction'}), 400
        if listing['status'] != 'ACTIVE':
            conn.close()
            return jsonify({'error': 'Auction not active'}), 400
        if listing['seller_id'] == request.user_id:
            conn.close()
            return jsonify({'error': 'Cannot bid on your own listing'}), 400
        if not listing['auction_end_time'] or datetime.utcnow() >= listing['auction_end_time']:
            settle_auction(cur, listing_id)
            conn.close()
            return jsonify({'error': 'Auction has ended'}), 400
        if amount <= float(listing['price']):
            conn.close()
            return jsonify({'error': 'Bid must exceed current price of $' + '{:.2f}'.format(float(listing['price']))}), 400

        cur.execute(
            'SELECT bidder_id FROM bids WHERE listing_id = %s ORDER BY amount DESC LIMIT 1',
            (listing_id,)
        )
        prev = cur.fetchone()

        cur.execute(
            'INSERT INTO bids (listing_id, bidder_id, amount) VALUES (%s, %s, %s)',
            (listing_id, request.user_id, amount)
        )
        cur.execute('UPDATE listings SET price = %s WHERE id = %s', (amount, listing_id))

        if prev and prev['bidder_id'] != request.user_id:
            cur.execute(
                "INSERT INTO notifications (user_id, message, type) VALUES (%s, %s, 'INFO')",
                (prev['bidder_id'], 'You were outbid on "' + listing['title'] + '"')
            )

        conn.close()
        return jsonify({'message': 'Bid placed', 'current_price': amount}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/listings/<int:listing_id>/bids', methods=['GET'])
def get_bids(listing_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''SELECT b.amount, b.created_at, u.username
               FROM bids b JOIN users u ON u.id = b.bidder_id
               WHERE b.listing_id = %s
               ORDER BY b.created_at DESC''',
            (listing_id,)
        )
        rows = cur.fetchall()
        conn.close()
        bids = []
        for r in rows:
            d = dict(r)
            if d.get('created_at'):
                d['created_at'] = d['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            d['amount'] = float(d['amount'])
            bids.append(d)
        return jsonify({'bids': bids})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ FRONTEND ROUTES ============

@app.route('/')
def index():
    return send_from_directory(os.path.join(FRONTEND_DIR, 'pages', 'buyer'), 'browse.html')

@app.route('/<path:filename>')
def serve_frontend(filename):
    return send_from_directory(FRONTEND_DIR, filename)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ============ MAIN ============
if __name__ == '__main__':
    init_db()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=(os.getenv('RENDER') is None))
