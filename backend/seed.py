"""
Switchr - Database Seed Script
Clears all tables and populates with sample data for development and testing.
"""

import psycopg2
import psycopg2.extras
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://admin@localhost:5432/switchr')

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def seed():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("Clearing existing data...")
    cur.execute("DELETE FROM notifications")
    cur.execute("DELETE FROM order_items")
    cur.execute("DELETE FROM orders")
    cur.execute("DELETE FROM cart")
    cur.execute("DELETE FROM listings")
    cur.execute("DELETE FROM users")

    # Reset sequences
    cur.execute("ALTER SEQUENCE users_id_seq RESTART WITH 1")
    cur.execute("ALTER SEQUENCE listings_id_seq RESTART WITH 1")
    cur.execute("ALTER SEQUENCE orders_id_seq RESTART WITH 1")
    cur.execute("ALTER SEQUENCE order_items_id_seq RESTART WITH 1")
    cur.execute("ALTER SEQUENCE notifications_id_seq RESTART WITH 1")

    print("Creating users...")

    # Admin
    cur.execute('''
        INSERT INTO users (email, username, password_hash, role, status)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    ''', ('admin@switchr.com', 'admin', hash_password('Admin123!'), 'admin', 'approved'))
    admin_id = cur.fetchone()['id']

    # Sellers
    cur.execute('''
        INSERT INTO users (email, username, password_hash, role, status)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    ''', ('seller1@switchr.com', 'techseller', hash_password('Seller123!'), 'user', 'approved'))
    seller1_id = cur.fetchone()['id']

    cur.execute('''
        INSERT INTO users (email, username, password_hash, role, status)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    ''', ('seller2@switchr.com', 'gadgetguru', hash_password('Seller123!'), 'user', 'approved'))
    seller2_id = cur.fetchone()['id']

    # Buyers
    cur.execute('''
        INSERT INTO users (email, username, password_hash, role, status)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    ''', ('buyer1@switchr.com', 'techbuyer', hash_password('Buyer123!'), 'user', 'approved'))
    buyer1_id = cur.fetchone()['id']

    cur.execute('''
        INSERT INTO users (email, username, password_hash, role, status)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    ''', ('buyer2@switchr.com', 'gadgetfan', hash_password('Buyer123!'), 'user', 'approved'))
    buyer2_id = cur.fetchone()['id']

    # Pending user (waiting for admin approval)
    cur.execute('''
        INSERT INTO users (email, username, password_hash, role, status)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    ''', ('pending@switchr.com', 'newuser', hash_password('User123!'), 'user', 'pending'))

    print("Creating listings...")

    # Active listings - seller 1
    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (seller1_id, 'iPhone 14 Pro 256GB', 'Excellent condition, barely used. Space Black. Comes with original box and charger. No scratches or dents.', 'Phones', 750.00, 'LIKE_NEW', 'BOTH', 'ACTIVE', 1))
    listing1_id = cur.fetchone()['id']

    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (seller1_id, 'MacBook Air M2 13"', '8GB RAM, 256GB SSD. Midnight color. Used for college, great condition. Charger included.', 'Laptops', 950.00, 'GOOD', 'SALE', 'ACTIVE', 1))
    listing2_id = cur.fetchone()['id']

    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (seller1_id, 'AirPods Pro 2nd Gen', 'Active Noise Cancellation, MagSafe charging case. Minor ear tip wear, works perfectly.', 'Headphones', 180.00, 'GOOD', 'SALE', 'ACTIVE', 1))

    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (seller1_id, 'iPad Air 5th Gen WiFi', '64GB, Blue. Used for drawing and note taking. Screen protector applied from day one.', 'Tablets', 420.00, 'LIKE_NEW', 'TRADE', 'ACTIVE', 1))

    # Active listings - seller 2
    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (seller2_id, 'Samsung Galaxy S23 Ultra', '256GB Phantom Black. S Pen included. Screen in perfect condition, no cracks.', 'Phones', 680.00, 'LIKE_NEW', 'BOTH', 'ACTIVE', 1))
    listing5_id = cur.fetchone()['id']

    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (seller2_id, 'Dell XPS 15 Laptop', 'Intel i7, 16GB RAM, 512GB SSD. Some scuffs on lid but screen is pristine. Windows 11.', 'Laptops', 820.00, 'GOOD', 'SALE', 'ACTIVE', 1))

    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (seller2_id, 'Sony WH-1000XM5 Headphones', 'Industry-leading noise cancellation. Comes with carry case and all accessories.', 'Headphones', 220.00, 'LIKE_NEW', 'SALE', 'ACTIVE', 1))

    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (seller2_id, 'Apple 67W USB-C Charger', 'Original Apple charger, works perfectly. Cable has slight wear near connector.', 'Chargers', 35.00, 'GOOD', 'SALE', 'ACTIVE', 2))

    # Pending approval listings
    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (seller1_id, 'Google Pixel 8 Pro', '128GB Obsidian. Amazing camera system. Selling because upgrading.', 'Phones', 600.00, 'LIKE_NEW', 'SALE', 'PENDING_APPROVAL', 1))

    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (seller2_id, 'Nintendo Switch OLED', 'White version, barely used. Comes with dock, joycons, and 3 games.', 'Other', 280.00, 'LIKE_NEW', 'BOTH', 'PENDING_APPROVAL', 1))

    # Sold listing
    cur.execute('''
        INSERT INTO listings (seller_id, title, description, category, price, condition, listing_type, status, quantity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (seller1_id, 'iPhone 13 Mini', '128GB, Blue. Screen has minor scratch but works great.', 'Phones', 380.00, 'GOOD', 'SALE', 'SOLD', 1))
    sold_listing_id = cur.fetchone()['id']

    print("Creating sample order...")

    # Sample completed order
    cur.execute('''
        INSERT INTO orders (
            buyer_id, subtotal, tax_rate, tax_amount, total,
            ship_first_name, ship_last_name, ship_address, ship_city, ship_state, ship_zip,
            bill_same_as_ship, card_last_four, card_name, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    ''', (
        buyer1_id, 380.00, 0.08, 30.40, 410.40,
        'John', 'Doe', '123 Tech Street', 'Starkville', 'MS', '39759',
        True, '4242', 'John Doe', 'COMPLETED'
    ))
    order_id = cur.fetchone()['id']

    cur.execute('''
        INSERT INTO order_items (order_id, listing_id, title, price, seller_id)
        VALUES (%s, %s, %s, %s, %s)
    ''', (order_id, sold_listing_id, 'iPhone 13 Mini', 380.00, seller1_id))

    print("Creating sample notifications...")

    cur.execute('''
        INSERT INTO notifications (user_id, message, type, is_read)
        VALUES (%s, %s, %s, %s)
    ''', (seller1_id, f'Your item "iPhone 13 Mini" was purchased by techbuyer! Order #{order_id}', 'SALE', False))

    cur.execute('''
        INSERT INTO notifications (user_id, message, type, is_read)
        VALUES (%s, %s, %s, %s)
    ''', (seller1_id, 'Your listing "Google Pixel 8 Pro" is pending admin approval.', 'INFO', True))

    cur.execute('''
        INSERT INTO notifications (user_id, message, type, is_read)
        VALUES (%s, %s, %s, %s)
    ''', (seller2_id, 'Your listing "Nintendo Switch OLED" is pending admin approval.', 'INFO', False))

    conn.close()

    print("\n Seed complete! Here's your test data:\n")
    print("USERS")
    print("  Admin:   admin@switchr.com     / Admin123!")
    print("  Seller1: seller1@switchr.com   / Seller123!  (username: techseller)")
    print("  Seller2: seller2@switchr.com   / Seller123!  (username: gadgetguru)")
    print("  Buyer1:  buyer1@switchr.com    / Buyer123!   (username: techbuyer)")
    print("  Buyer2:  buyer2@switchr.com    / Buyer123!   (username: gadgetfan)")
    print("  Pending: pending@switchr.com   / User123!    (status: pending)")
    print("\nLISTINGS")
    print("  8 ACTIVE listings (4 per seller)")
    print("  2 PENDING_APPROVAL listings")
    print("  1 SOLD listing")
    print("\nORDERS")
    print("  1 completed order (techbuyer bought iPhone 13 Mini)")
    print("\nNOTIFICATIONS")
    print("  3 sample notifications")

if __name__ == '__main__':
    confirm = input("This will DELETE all existing data. Type 'yes' to continue: ")
    if confirm.lower() == 'yes':
        seed()
    else:
        print("Cancelled.")