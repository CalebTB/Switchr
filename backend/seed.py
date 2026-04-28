"""
Switchr - Demo Seed Script

Wipes the database and populates it for the live demo.

Logged-into accounts:
  Admin: admin@switchr.com / Admin123!
  Demo:  demo@switchr.com  / Password123!

Silent ghost users (never logged into during the demo, exist only as the
counterparty for demo's seeded sales/purchases/reviews/offers/bids):
  taylor@switchr.com
  jordan@switchr.com

The third demoable account is registered live during the demo so the
register -> admin approval -> first purchase flow can be shown end-to-end.
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
    # Order matters: children before parents
    cur.execute("DELETE FROM password_resets")
    cur.execute("DELETE FROM bids")
    cur.execute("DELETE FROM reviews")
    cur.execute("DELETE FROM trades")
    cur.execute("DELETE FROM wishlist")
    cur.execute("DELETE FROM notifications")
    cur.execute("DELETE FROM order_items")
    cur.execute("DELETE FROM orders")
    cur.execute("DELETE FROM transactions")
    cur.execute("DELETE FROM cart")
    cur.execute("DELETE FROM listings")
    cur.execute("DELETE FROM users")

    # Reset sequences
    for seq in [
        'users_id_seq', 'listings_id_seq', 'orders_id_seq', 'order_items_id_seq',
        'notifications_id_seq', 'transactions_id_seq', 'trades_id_seq',
        'reviews_id_seq', 'bids_id_seq', 'wishlist_id_seq', 'cart_id_seq',
    ]:
        try:
            cur.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1")
        except psycopg2.Error:
            pass  # sequence may not exist yet on a fresh DB

    print("Creating users...")

    cur.execute('''
        INSERT INTO users (email, username, password_hash, role, status)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    ''', ('admin@switchr.com', 'admin', hash_password('Admin123!'), 'admin', 'approved'))
    admin_id = cur.fetchone()['id']

    cur.execute('''
        INSERT INTO users (email, username, password_hash, role, status, balance)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
    ''', ('demo@switchr.com', 'demo', hash_password('Password123!'), 'user', 'approved', 1500.00))
    demo_id = cur.fetchone()['id']

    cur.execute('''
        INSERT INTO users (email, username, password_hash, role, status, balance)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
    ''', ('taylor@switchr.com', 'taylor', hash_password('NotForLogin'), 'user', 'approved', 200.00))
    taylor_id = cur.fetchone()['id']

    cur.execute('''
        INSERT INTO users (email, username, password_hash, role, status, balance)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
    ''', ('jordan@switchr.com', 'jordan', hash_password('NotForLogin'), 'user', 'approved', 200.00))
    jordan_id = cur.fetchone()['id']

    print("Creating demo's active listings...")

    def insert_listing(seller_id, title, desc, category, price, condition,
                       listing_type, status='ACTIVE', quantity=1, photos=None,
                       starting_price=None, auction_duration_days=None,
                       auction_end_offset_hours=None):
        cur.execute('''
            INSERT INTO listings (
                seller_id, title, description, category, price, condition,
                listing_type, status, quantity, photo_urls,
                starting_price, auction_duration_days,
                auction_end_time
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      CASE WHEN %s IS NOT NULL
                           THEN CURRENT_TIMESTAMP + (%s || ' hours')::INTERVAL
                           ELSE NULL END)
            RETURNING id
        ''', (
            seller_id, title, desc, category, price, condition,
            listing_type, status, quantity, photos or [],
            starting_price, auction_duration_days,
            auction_end_offset_hours, str(auction_end_offset_hours) if auction_end_offset_hours else None,
        ))
        return cur.fetchone()['id']

    iphone_id = insert_listing(
        demo_id, 'iPhone 15 Pro 256GB',
        'Natural Titanium. Battery health 100%. Includes original box, USB-C cable, and a clear case.',
        'Phones', 850.00, 'LIKE_NEW', 'SALE',
        photos=['https://images.unsplash.com/photo-1696446702183-be9605d4209e?w=400']
    )

    macbook_id = insert_listing(
        demo_id, 'MacBook Pro 14" M3',
        '16GB unified memory, 512GB SSD. Space Black. Light use, no scratches. AppleCare+ until 2026.',
        'Laptops', 1400.00, 'LIKE_NEW', 'BOTH',
        photos=['https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400']
    )

    airpods_id = insert_listing(
        demo_id, 'AirPods Pro (2nd Gen)',
        'USB-C MagSafe case. Active Noise Cancellation works perfectly. Replaced ear tips included.',
        'Headphones', 180.00, 'GOOD', 'SALE',
        photos=['https://images.unsplash.com/photo-1606841837239-c5a1a4a07af7?w=400']
    )

    ipad_id = insert_listing(
        demo_id, 'iPad Air M2 11"',
        '128GB, Blue, WiFi. Used for note-taking. Screen protector applied since day one.',
        'Tablets', 400.00, 'LIKE_NEW', 'TRADE',
        photos=['https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400']
    )

    watch_id = insert_listing(
        demo_id, 'Apple Watch Series 9 45mm',
        'GPS, Midnight Aluminum. Sport Band included. Some micro-scratches on case from daily wear.',
        'Other', 300.00, 'GOOD', 'BOTH',
        photos=['https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=400']
    )

    sony_id = insert_listing(
        demo_id, 'Sony WH-1000XM5',
        'Industry-leading noise cancellation. Black. Carry case and all original cables included.',
        'Headphones', 250.00, 'LIKE_NEW', 'SALE',
        photos=['https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=400']
    )

    mouse_id = insert_listing(
        demo_id, 'Logitech MX Master 3S',
        'Wireless ergonomic mouse. Quiet click. USB-C charging. Two available.',
        'Other', 80.00, 'LIKE_NEW', 'SALE', quantity=2,
        photos=['https://images.unsplash.com/photo-1527814050087-3793815479db?w=400']
    )

    print("Creating demo's auction (3-day duration, with seeded bids)...")

    auction_id = insert_listing(
        demo_id, 'Nintendo Switch OLED + 3 games',
        'White OLED model, dock and Joy-Cons included. Bundle: Mario Kart, Zelda TOTK, Smash Ultimate.',
        'Other', 200.00, 'LIKE_NEW', 'AUCTION',
        starting_price=200.00, auction_duration_days=3, auction_end_offset_hours=72,
        photos=['https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?w=400']
    )
    cur.execute('INSERT INTO bids (listing_id, bidder_id, amount) VALUES (%s, %s, %s)',
                (auction_id, taylor_id, 210.00))
    cur.execute('INSERT INTO bids (listing_id, bidder_id, amount) VALUES (%s, %s, %s)',
                (auction_id, jordan_id, 235.00))
    cur.execute('INSERT INTO bids (listing_id, bidder_id, amount) VALUES (%s, %s, %s)',
                (auction_id, taylor_id, 250.00))

    print("Creating demo's pending-approval listing (admin will approve live)...")

    insert_listing(
        demo_id, 'Google Pixel 8 Pro 128GB',
        'Obsidian. Selling because upgrading. Excellent camera, no scratches.',
        'Phones', 600.00, 'LIKE_NEW', 'SALE', status='PENDING_APPROVAL',
        photos=['https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400']
    )

    print("Creating demo's already-sold listings...")

    sold_iphone_id = insert_listing(
        demo_id, 'iPhone 13 Mini 128GB',
        'Blue. Replaced battery in late 2024. Minor screen scratch, otherwise great.',
        'Phones', 380.00, 'GOOD', 'SALE', status='SOLD', quantity=0,
        photos=['https://images.unsplash.com/photo-1632661674596-df8be070a5c5?w=400']
    )

    sold_pencil_id = insert_listing(
        demo_id, 'Apple Pencil 2nd Gen',
        'Works perfectly. Tip slightly worn from use, charges via MagSafe.',
        'Other', 80.00, 'GOOD', 'SALE', status='SOLD', quantity=0,
        photos=['https://images.unsplash.com/photo-1583394838336-acd977736f90?w=400']
    )

    print("Creating ghost listings (so demo has things to browse/buy/wishlist)...")

    steamdeck_id = insert_listing(
        taylor_id, 'Steam Deck OLED 512GB',
        'Excellent condition, hardly used. Carry case and dock included.',
        'Other', 480.00, 'LIKE_NEW', 'BOTH',
        photos=['https://images.unsplash.com/photo-1640955014216-75201056c829?w=400']
    )

    gameboy_id = insert_listing(
        taylor_id, 'Vintage Game Boy DMG-01',
        'Original 1989 Game Boy. Screen has typical retro lines. Comes with Tetris cartridge.',
        'Other', 120.00, 'FAIR', 'SALE',
        photos=['https://images.unsplash.com/photo-1531525645387-7f14be1bdbbd?w=400']
    )

    # Listing taylor "sold" to demo in the past (status SOLD)
    taylor_old_sale_id = insert_listing(
        taylor_id, 'Anker Soundcore Liberty 4',
        'Wireless earbuds with ANC. Charging case included.',
        'Headphones', 90.00, 'GOOD', 'SALE', status='SOLD', quantity=0,
        photos=['https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400']
    )

    gopro_id = insert_listing(
        jordan_id, 'GoPro HERO12 Black',
        '5.3K video. Two batteries, dual charger, and 64GB SD card included.',
        'Other', 300.00, 'LIKE_NEW', 'SALE',
        photos=['https://images.unsplash.com/photo-1623788858432-4a8db35b9c5e?w=400']
    )

    drone_id = insert_listing(
        jordan_id, 'DJI Mini 3 Drone',
        'Sub-249g, 4K HDR. Two batteries, ND filter pack, and shoulder bag.',
        'Other', 450.00, 'LIKE_NEW', 'TRADE',
        photos=['https://images.unsplash.com/photo-1473968512647-3e447244af8f?w=400']
    )

    # Listing jordan "sold" to demo in the past
    jordan_old_sale_id = insert_listing(
        jordan_id, 'USB-C Hub 7-in-1',
        'HDMI, SD, microSD, USB-A x2, USB-C PD, ethernet.',
        'Chargers', 35.00, 'LIKE_NEW', 'SALE', status='SOLD', quantity=0,
        photos=['https://images.unsplash.com/photo-1625948515291-69613efd103f?w=400']
    )

    print("Creating demo's past sales (taylor and jordan bought from demo)...")

    def create_completed_purchase(buyer_id, seller_id, listing_id, title, price,
                                  ship_first, ship_last, ship_city, ship_state):
        cur.execute('''
            INSERT INTO orders (
                buyer_id, subtotal, tax_rate, tax_amount, total,
                ship_first_name, ship_last_name, ship_address,
                ship_city, ship_state, ship_zip,
                bill_same_as_ship, card_last_four, status,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      CURRENT_TIMESTAMP - INTERVAL '7 days')
            RETURNING id
        ''', (
            buyer_id, price, 0.08, round(float(price) * 0.08, 2), round(float(price) * 1.08, 2),
            ship_first, ship_last, '101 Demo Street',
            ship_city, ship_state, '39759',
            True, '4242', 'COMPLETED'
        ))
        order_id = cur.fetchone()['id']

        cur.execute('''
            INSERT INTO order_items (order_id, listing_id, title, price, seller_id, created_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP - INTERVAL '7 days')
        ''', (order_id, listing_id, title, price, seller_id))

        cur.execute('''
            INSERT INTO transactions (buyer_id, seller_id, listing_id, title, price, payment_method, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'COMPLETED', CURRENT_TIMESTAMP - INTERVAL '7 days')
            RETURNING id
        ''', (buyer_id, seller_id, listing_id, title, price, 'balance'))
        return cur.fetchone()['id']

    # demo sold "iPhone 13 Mini" to taylor 7 days ago
    sale_to_taylor_txn = create_completed_purchase(
        taylor_id, demo_id, sold_iphone_id, 'iPhone 13 Mini 128GB', 380.00,
        'Taylor', 'Reed', 'Memphis', 'TN'
    )

    # demo sold "Apple Pencil" to jordan 4 days ago
    sale_to_jordan_txn = create_completed_purchase(
        jordan_id, demo_id, sold_pencil_id, 'Apple Pencil 2nd Gen', 80.00,
        'Jordan', 'Hayes', 'Atlanta', 'GA'
    )

    print("Creating demo's past purchases (demo bought from taylor and jordan)...")

    # demo bought from taylor (will be REVIEWED by demo)
    purchase_from_taylor_txn = create_completed_purchase(
        demo_id, taylor_id, taylor_old_sale_id, 'Anker Soundcore Liberty 4', 90.00,
        'Demo', 'User', 'Starkville', 'MS'
    )

    # demo bought from jordan (will be UNREVIEWED so live demo can show "Leave Review")
    purchase_from_jordan_txn = create_completed_purchase(
        demo_id, jordan_id, jordan_old_sale_id, 'USB-C Hub 7-in-1', 35.00,
        'Demo', 'User', 'Starkville', 'MS'
    )

    print("Creating reviews...")

    cur.execute('''
        INSERT INTO reviews (transaction_id, buyer_id, seller_id, rating, comment, created_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP - INTERVAL '5 days')
    ''', (sale_to_taylor_txn, taylor_id, demo_id, 5,
          'Phone arrived faster than expected and was exactly as described. Would buy from again!'))

    cur.execute('''
        INSERT INTO reviews (transaction_id, buyer_id, seller_id, rating, comment, created_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP - INTERVAL '2 days')
    ''', (sale_to_jordan_txn, jordan_id, demo_id, 4,
          'Great packaging and quick shipping. Tip wear was a bit more than I expected but still works.'))

    # demo's review of taylor's old sale
    cur.execute('''
        INSERT INTO reviews (transaction_id, buyer_id, seller_id, rating, comment, created_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP - INTERVAL '4 days')
    ''', (purchase_from_taylor_txn, demo_id, taylor_id, 5,
          'Earbuds in great shape, sound quality is excellent.'))

    print("Creating trade offers (badge will light up for demo)...")

    # jordan -> demo (incoming, PENDING — drives offers_pending count)
    cur.execute('''
        INSERT INTO trades (sender_id, receiver_id, offered_listing_id, wanted_listing_id, cash_offer, status)
        VALUES (%s, %s, %s, %s, %s, 'PENDING')
    ''', (jordan_id, demo_id, drone_id, ipad_id, 50.00))

    # demo -> taylor (outgoing, PENDING)
    cur.execute('''
        INSERT INTO trades (sender_id, receiver_id, offered_listing_id, wanted_listing_id, cash_offer, status)
        VALUES (%s, %s, %s, %s, %s, 'PENDING')
    ''', (demo_id, taylor_id, watch_id, steamdeck_id, 100.00))

    print("Creating wishlist entries for demo...")

    cur.execute('INSERT INTO wishlist (user_id, listing_id) VALUES (%s, %s)', (demo_id, gopro_id))
    cur.execute('INSERT INTO wishlist (user_id, listing_id) VALUES (%s, %s)', (demo_id, steamdeck_id))
    cur.execute('INSERT INTO wishlist (user_id, listing_id) VALUES (%s, %s)', (demo_id, gameboy_id))

    print("Creating notifications for demo (mix of read/unread)...")

    notifications = [
        (demo_id, 'Welcome to Switchr! Your seller account is approved.', 'INFO', True),
        (demo_id, 'Your listing "iPhone 13 Mini 128GB" was purchased by taylor.', 'SALE', True),
        (demo_id, 'taylor left you a 5-star review on "iPhone 13 Mini 128GB".', 'REVIEW', True),
        (demo_id, 'Your listing "Apple Pencil 2nd Gen" was purchased by jordan.', 'SALE', False),
        (demo_id, 'jordan left you a 4-star review on "Apple Pencil 2nd Gen".', 'REVIEW', False),
        (demo_id, 'jordan sent you a trade offer on "iPad Air M2 11"".', 'OFFER', False),
        (demo_id, 'Your listing "Google Pixel 8 Pro 128GB" is pending admin approval.', 'INFO', True),
        (demo_id, 'New bid on "Nintendo Switch OLED + 3 games": $250 by taylor.', 'BID', False),
    ]
    for uid, msg, typ, is_read in notifications:
        cur.execute('''
            INSERT INTO notifications (user_id, message, type, is_read)
            VALUES (%s, %s, %s, %s)
        ''', (uid, msg, typ, is_read))

    conn.close()

    print("\n" + "=" * 60)
    print("Seed complete. Demo accounts:")
    print("=" * 60)
    print("  Admin: admin@switchr.com / Admin123!")
    print("  Demo:  demo@switchr.com  / Password123!")
    print()
    print("Silent ghost users (do not log in during demo):")
    print("  taylor@switchr.com, jordan@switchr.com")
    print()
    print("Demo account is ready with:")
    print("  - 7 active listings (mix of SALE/TRADE/BOTH)")
    print("  - 1 active auction with 3 seeded bids (ends in ~3 days)")
    print("  - 1 listing PENDING_APPROVAL (approve live with admin)")
    print("  - 2 past sales w/ buyer reviews + 2 past purchases (1 reviewed, 1 not)")
    print("  - 1 incoming trade offer (badge lights up)")
    print("  - 1 outgoing trade offer")
    print("  - 3 wishlist items, 8 notifications")
    print("  - $1500 balance")


if __name__ == '__main__':
    seed()
