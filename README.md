# Switchr - E-Commerce Platform

## Project Overview

**Switchr** is a marketplace we're building for our CSE 4214 project. We designed it so users can buy, sell, or trade used electronics directly with each other. The main idea came from wanting to create a simple platform where people could exchange tech items without going through big retailers. You can trade phones, laptops, tablets, headphones, chargers, basically any consumer electronics you want to swap.

Also, instead of just buying and selling with cash, users can trade items back and forth. If the values aren't equal, they can add some simulated cash to balance it out. It's like swapping with your friends, but online.

## Why We Built It
We wanted to tackle a real problem: a lot of people have perfectly good electronics they don't use anymore, but there's no easy way to swap them with someone else who needs them. Existing marketplaces charge fees or require shipping. With Switchr, we're cutting out the middleman and letting people trade directly

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
If you're an admin, you get special powers to approve accounts, remove bad listings, and keep the platform safe

## Project Information

**Course**: CSE 4214/6214  
**Instructor**: Charan Gudla  
**Teaching Assistant**: Tiran Judy  

**Team Members**:
- Beulah Ajah (bia19@msstate.edu)
- Maxwell Merget (mlm1603@msstate.edu)
- Caleb Byers (ctb388@msstate.edu)

**Team Roles for Switchr**

- Beulah Ajah – Documentation Lead (SRS drafting, README maintenance)
- Maxwell Merget – Project Coordination and Task Tracking
- Caleb Byers – Requirements Analysis and User Stories Support


## System Objectives

Switchr is designed to:
- Enable users with different roles (Buyer, Seller, Admin) to securely login and perform distinct actions
- Allow buyers to search, compare, and purchase or trade products from different sellers
- Enable sellers to add products and receive simulated payments
- Provide admins with oversight capabilities to approve/block accounts and manage platform integrity


## System Architecture

### Platform Type
- **Web-based application** accessible through modern web browsers (Chrome, Firefox, Edge, Safari)
- **Client-Server Architecture**: Users interact via web interface; logic and data storage occur on the server side
- **No native mobile app** in Version 1.0

### Technology Stack
- **Any language and frameworks** can be used to achieve the objectives
- **Web technologies** to ensure broad browser compatibility
- **HTTPS** for secure data transmission between browser and server


## Core Functionality

### Who Uses It?

Buyers - People looking to find electronics without breaking the bank. They can browse listings, search for specific items, and make purchase or trade offers.

Sellers - People who have electronics they want to get rid of. They list items with descriptions and photos, then respond to offers from buyers.

Traders - The people who really get into swapping. They use our tools to compare item values and propose fair trades, sometimes throwing in some cash to even things out.

Admins - Our team keeping the platform clean and safe. They approve new accounts, remove sketchy listings, and handle reports from users

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

### Key Features
- User account registration, login, and profile management
- Listing creation, editing, and deletion
- Advanced browsing and filtering capabilities
- Purchase and trading systems
- Offer management and negotiation
- Transaction history tracking
- Comprehensive admin dashboard
- User reporting system for safety

## Features Breakdown

**Account Stuff**
- Sign up with email and password
- Log in/out
- Edit your profile
- Forgot password recovery

**Listing Management**
- Create listings with photos and descriptions**
- Edit your listings anytime
- Delete listings when you're done
- See all your active listings in one place

**Shopping & Trading**
- Browse all active listings
- Search by keywords
- Filter by category, condition, price, listing type
- Click into any listing to see full details
- Make purchase offers
- Propose trades with items from your own inventory
- See all your offers (incoming and outgoing)
- Accept, reject, or counter offers

**History & Records**

- Track everything you've bought, sold, and traded
- See all your past and current transactions

**Keeping It Safe**
- Report suspicious listings or users
- Admin dashboard to manage the platform
- Moderation queue for handling reports

## Nonfunctional Requirements

### Performance
- Every page loads in 3 seconds or less on typical home internet
- Search results and trade matches appear in 2 seconds or less
- System handles at least 100 concurrent users without noticeable slowdowns

### Security
- Passwords: minimum 8 characters with letters, numbers, and symbols using strong hashing
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


## Development Timeline

The project will be developed in **four sprints**, each lasting **2-4 weeks**. Development follows **agile paradigms** with deliverables submitted to GitHub.

### Project Versions
- **Version 1.0**: Implements core functionality as specified in this SRS
- **Version 2.0**: Future enhancements based on TA feedback (1-2 new requirements)



## What's NOT Included (Version 1.0)

- Physical shipping or delivery handling
- Real payment processing through banks or cards (payments are simulated)
- Mobile app version
- Integration with real banking systems or third-party payment processors


## Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Edge, or Safari)
- Internet connectivity
- No specialized hardware required


## Testing

Testing should focus on:
- All features outlined in Section 3 of the SRS
- Quality expectations defined in Section 4
- Compatibility across all supported browsers


## Contributing

All project deliverables should be stored in the GitHub repository. Follow submission guidelines provided at the start of each sprint.


## Legal & Compliance

- Users must be at least 18 years old to create an account
- Platform includes terms of service and privacy notice
- No illegal items (stolen goods, weapons, etc.) are permitted
- Platform is not responsible for individual user transactions


## Contact & Support

For questions or issues, contact instructor or teaching assistant:
- **Instructor**: Charan Gudla
- **Teaching Assistant**: Tiran Judy



**Last Updated**: February 2026  
**Version**: 1.0
