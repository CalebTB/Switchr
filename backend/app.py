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

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
