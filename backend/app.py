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

load_dotenv()

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'SkeletonPages')

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)

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
            status VARCHAR(20) DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.close()

# Token required decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
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

# Generate JWT token
def generate_token(user):
    payload = {
        'user_id': user['id'],
        'email': user['email'],
        'role': user['role'],
        'exp': datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


# ============ AUTH ROUTES ============

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    email = data.get('email')
    username = data.get('username')
    password = data.get('password')

    if not email or not username or not password:
        return jsonify({'error': 'Email, username, and password are required'}), 400

    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            'INSERT INTO users (email, username, password_hash) VALUES (%s, %s, %s) RETURNING id, email, username, role',
            (email, username, password_hash)
        )
        user = cur.fetchone()
        conn.close()

        token = generate_token(user)
        return jsonify({'token': token, 'user': {'id': user['id'], 'email': user['email'], 'username': user['username'], 'role': user['role']}}), 201

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
            'role': user['role']
        }
    })


@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT id, email, username, role, created_at FROM users WHERE id = %s', (request.user_id,))
    user = cur.fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user})


# ============ FRONTEND ROUTES ============

@app.route('/')
def index():
    return send_from_directory(os.path.join(FRONTEND_DIR, 'Buyer'), 'buyer.html')

@app.route('/<path:filename>')
def serve_frontend(filename):
    return send_from_directory(FRONTEND_DIR, filename)


# ============ MAIN ============
@app.route('/api/listings', methods=['POST'])
@token_required
def create_listing():
    data = request.get_json()

    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    category = data.get('category', '')
    price = data.get('price')
    condition = data.get('condition', '')
    listing_type = data.get('listingType', '')

    if not title or not description or not category or not price or not condition or not listing_type:
        return jsonify({'error': 'All fields are required'}), 400

    if len(title) > 100:
        return jsonify({'error': 'Title must be 100 characters or less'}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            '''INSERT INTO listings 
               (seller_id, title, description, category, price, condition, listing_type)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING *''',
            (request.user_id, title, description, category, float(price), condition, listing_type)
        )
        listing = cur.fetchone()
        conn.close()
        return jsonify({'message': 'Listing created successfully', 'listing': listing}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/listings', methods=['GET'])
@token_required
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
        listings = []
        for row in rows:
            d = dict(row)
            if d.get('created_at'):
                d['created_at'] = d['created_at'].strftime('%Y-%m-%d')
            if d.get('updated_at'):
                d['updated_at'] = d['updated_at'].strftime('%Y-%m-%d')
            listings.append(d)
        return jsonify({'listings': listings})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
