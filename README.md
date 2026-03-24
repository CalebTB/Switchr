# Switchr - E-Commerce Platform

## Project Overview

**Switchr** is a marketplace we're building for our CSE 4214 project. We designed it so users can buy, sell, or trade used electronics directly with each other. The main idea came from wanting to create a simple platform where people could exchange tech items without going through big retailers. You can trade phones, laptops, tablets, headphones, chargers, basically any consumer electronics you want to swap.

Instead of just buying and selling with cash, users can trade items back and forth. If the values aren't equal, they can add some simulated cash to balance it out. It's like swapping with your friends, but online.

## Why We Built It

We wanted to tackle a real problem: a lot of people have perfectly good electronics they don't use anymore, but there's no easy way to swap them with someone else who needs them. Existing marketplaces charge fees or require shipping. With Switchr, we're cutting out the middleman and letting people trade directly.

### Key Features
- **Direct Trading System**: Users can swap items of equal or similar value without cash, or add cash to balance the deal
- **Cost Savings**: Reduced reliance on traditional retail channels through peer-to-peer exchanges
- **Wide Product Range**: Support for phones, laptops, tablets, headphones, chargers, and similar devices

## What Switchr Does

When you use Switchr, you can:
- Create an account as a buyer, seller, or trader (or all three)
- List items you want to sell or trade with photos and descriptions
- Browse what others are selling using filters and search
- Make offers to buy items or propose trades
- Negotiate deals by messaging the other person
- Track your history of what you've bought, sold, or traded
- Report sketchy listings if something doesn't look right

If you're an admin, you get special powers to approve accounts, remove bad listings, and keep the platform safe.

---

## Project Information

**Course**: CSE 4214/6214  
**Instructor**: Charan Gudla  
**Teaching Assistant**: Tiran Judy  

**Team Members**:
- Beulah Ajah (bia19@msstate.edu)
- Maxwell Merget (mlm1603@msstate.edu)
- Caleb Byers (ctb388@msstate.edu)

**Team Roles**:
- Beulah Ajah - Buyer/Seller pages, checkout backend, integration testing
- Maxwell Merget - Documentation, test plan, RTM
- Caleb Byers - Auth, admin, trading functionality, unit testing

---

## Live Deployment

The app auto-deploys on every push to main.  
**Live URL**: [https://switchr.onrender.com](https://switchr.onrender.com)

---

## How to Run Locally

### Prerequisites
- Python 3.9+
- PostgreSQL
- pip

### 1. Clone the repository
```bash
git clone https://github.com/CalebTB/Switchr.git
cd Switchr
```

### 2. Set up the virtual environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create the environment file
Create a `.env` file inside the `backend/` folder:
```
SECRET_KEY=switchrproject
DATABASE_URL=postgresql://<your_pg_username>@localhost:5432/switchr
```
Replace `<your_pg_username>` with your local PostgreSQL username.

### 4. Create the database
```bash
psql postgres -c "CREATE DATABASE switchr;"
```

### 5. Run the app
```bash
python app.py
```
Flask will initialize all database tables automatically on startup.

### 6. Open in browser
```
http://localhost:5000
```

---

## Seed the Database

To clear all existing data and load sample data for testing:

```bash
cd backend
source venv/bin/activate
python seed.py
```

Type `yes` when prompted. This creates 6 users, 11 listings, 1 completed order, and 3 notifications.

**Test credentials after seeding:**

| Role | Email | Password | Username |
|------|-------|----------|----------|
| Admin | admin@switchr.com | Admin123! | admin |
| Seller | seller1@switchr.com | Seller123! | techseller |
| Seller | seller2@switchr.com | Seller123! | gadgetguru |
| Buyer | buyer1@switchr.com | Buyer123! | techbuyer |
| Buyer | buyer2@switchr.com | Buyer123! | gadgetfan |
| Pending | pending@switchr.com | User123! | newuser |

---

## Run Tests

```bash
cd Switchr
source backend/venv/bin/activate
python -m pytest tests/Integration_Testing/test_listings.py -v
```

Expected result: 18 passed

---

## System Architecture

### Platform Type
- **Web-based application** accessible through modern web browsers (Chrome, Firefox, Edge, Safari)
- **Client-Server Architecture**: Users interact via web interface; logic and data storage occur on the server side
- **No native mobile app** in Version 1.0

### Technology Stack
- **Backend**: Python / Flask
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Auth**: JWT tokens
- **Deployment**: Render

---

## Core Functionality

### Who Uses It?

**Buyers** - People looking to find electronics without breaking the bank. They can browse listings, search for specific items, and make purchase or trade offers.

**Sellers** - People who have electronics they want to get rid of. They list items with descriptions and photos, then respond to offers from buyers.

**Traders** - Users who actively engage in item-for-item exchanges using value comparison tools and simulated cash adjustments.

**Admins** - Platform oversight. They approve new accounts, remove sketchy listings, and handle reports from users.

### User Roles

**Buyers**
- Browse listings and initiate purchases or trades
- Require basic web literacy and familiarity with online marketplaces
- Can become sellers by listing items of their own

**Sellers**
- List electronics for sale or trade
- Provide accurate item descriptions, conditions, and images
- Receive and manage multiple offers

**Traders**
- Actively engage in item-for-item exchanges
- Use value comparison tools to propose fair trades
- Negotiate with simulated cash adjustments

**Administrators**
- Oversee system operation and content integrity
- Review user activity and manage reported listings
- Enforce platform rules and maintain safety standards

---

## Features Implemented (Sprint 3)

- User registration, login, logout with JWT auth
- Admin approval flow for users and listings
- Seller home - view, filter, search own listings
- Create listing with photo upload and quantity
- Edit listing with re-approval on content changes
- Delete/delist listing (soft delete, record preserved)
- Buyer browse with search and filters
- Listing detail page with stock indicator
- Add to cart, view cart, remove from cart
- Checkout with shipping info, billing address, simulated payment
- Orders and order items saved to database on checkout
- Seller notified when item is purchased
- Quantity decrements on purchase, listing marked SOLD at zero stock

## Features In Progress

- Photo display on listing detail and browse pages
- Trade offer flow
- Item comparison feature
- Returns and refund flow
- Transaction history view
- Unit tests
- Integration tests

---

## Features Breakdown

**Account**
- Sign up with email and password
- Log in and log out
- Edit your profile
- Forgot password recovery

**Listing Management**
- Create listings with photos and descriptions
- Edit your listings anytime
- Delete listings when done
- See all your active listings in one place

**Shopping and Trading**
- Browse all active listings
- Search by keywords
- Filter by category, condition, price, listing type
- Click into any listing to see full details
- Make purchase offers
- Propose trades with items from your own inventory
- See all your offers (incoming and outgoing)
- Accept, reject, or counter offers

**History and Records**
- Track everything you've bought, sold, and traded
- See all past and current transactions

**Safety**
- Report suspicious listings or users
- Admin dashboard to manage the platform
- Moderation queue for handling reports

---

## Nonfunctional Requirements

### Performance
- Every page loads in 3 seconds or less on typical home internet
- Search results and trade matches appear in 2 seconds or less
- System handles at least 100 concurrent users without noticeable slowdowns

### Security
- Passwords: minimum 8 characters with letters, numbers, and symbols, stored using strong hashing
- Account lockout after 3 failed login attempts for 10 minutes
- Private pages only visible to logged-in owner or admin
- All data transmitted via HTTPS
- Email verification required before listing items or sending trade offers

### Safety
- System saves completed information automatically
- Failed connections preserve pending trade offers on server
- Admin review prevents illegal or harmful items from appearing publicly
- Contact information only shared after both sides agree to trade

### Quality Attributes
- **Usability**: Familiar marketplace interface with clear buttons and helpful error messages
- **Reliability**: 99% uptime with no data loss from crashes
- **Maintainability**: Organized code structure for easy future updates
- **Portability**: Works consistently across Chrome, Firefox, Edge, and Safari on all platforms

---

## Development Timeline

The project is developed in **four sprints**, each lasting **2-4 weeks**, following agile paradigms with deliverables submitted to GitHub.

### Project Versions
- **Version 1.0**: Implements core functionality as specified in the SRS
- **Version 2.0**: Future enhancements based on TA feedback (1-2 new requirements)

---

## What's NOT Included (Version 1.0)

- Physical shipping or delivery handling
- Real payment processing through banks or cards (payments are simulated)
- Mobile app version
- Integration with real banking systems or third-party payment processors

---

## Testing

- Integration tests cover all listing API endpoints (create, edit, delete, browse)
- Unit tests cover individual backend functions (in progress)
- Tests located in `tests/Integration_Testing/` and `tests/Unit_Testing/`
- Requirements traceability matrix available in `RTM_Switchr.xlsx`

---

## Contributing

All project deliverables are stored in the GitHub repository. Follow submission guidelines provided at the start of each sprint.

---

## Legal and Compliance

- Users must be at least 18 years old to create an account
- Platform includes terms of service and privacy notice
- No illegal items (stolen goods, weapons, etc.) are permitted
- Platform is not responsible for individual user transactions

---

## Contact and Support

- **Instructor**: Charan Gudla
- **Teaching Assistant**: Tiran Judy

---

**Last Updated**: March 2026  
**Version**: Sprint 3