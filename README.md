# Paddy - Rice Mill Management System

![Paddy Project Logo](paddy_proj/paddy_app/static/media/logo.png)

Paddy is a comprehensive Django-based application designed for managing rice mill operations. It provides a complete solution for customer management, order processing, inventory tracking, and payment handling with Razorpay integration.

## Features

### Multi-Role User System
- **Superadmin**: System-wide administration and oversight
- **Admin**: Managing customers, orders, and business operations
- **Customer**: Placing orders, tracking deliveries, and making payments

### Order Management
- Create and manage orders for rice, paddy, and other products
- Multi-product order support
- Order status tracking (payment and delivery)
- Booking fee payment system

### Payment Integration
- Seamless Razorpay payment gateway integration
- Partial payment support
- Payment verification and receipt generation
- Subscription management for service access

### Customer Management
- Customer onboarding with GST validation
- Customer account management
- Customer order history and tracking

### Subscription System
- Tiered subscription model for admins and customers
- Admin user count increase requests
- Subscription status monitoring

### Additional Features
- Role switching between admin/customer accounts
- Delivery status validation
- Invoice generation
- Admin and customer dashboards

## Tech Stack

- **Backend**: Django 5.2
- **Database**: PostgreSQL (via psycopg2)
- **Payment Gateway**: Razorpay
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Custom user authentication system

## System Requirements

- Python 3.10+
- PostgreSQL 13+
- Internet connection for Razorpay API integration

## Installation and Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/paddy.git
   cd paddy
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Create a `.env` file in the root directory
   - Add the following variables:
     ```
     SECRET_KEY=your_secret_key
     DEBUG=True
     DATABASE_URL=postgres://user:password@localhost:5432/paddy
     RAZORPAY_KEY_ID=your_razorpay_key_id
     RAZORPAY_SECRET=your_razorpay_secret
     ```

5. Run database migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superadmin account:
   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server:
   ```bash
   python manage.py runserver
   ```

8. Access the application at `http://localhost:8000`

## User Roles and Workflows

### Superadmin
- Create and manage admin accounts
- Approve admin subscription increase requests
- View system-wide statistics and reports

### Admin
- Create and manage customer accounts
- Place orders on behalf of customers
- Track order status and payment
- Request user count increases

### Customer
- View order history and status
- Make payments (full or partial)
- Confirm delivery status
- Upgrade to admin role

## Database Models

### Core Models
- **AdminTable**: Admin user accounts
- **CustomerTable**: Customer accounts linked to admins
- **Orders**: Order details including payment and delivery status
- **OrderItems**: Individual items within an order
- **Payments**: Payment records for orders
- **Subscription**: Subscription records for admins and customers
- **UserIncreaseSubscription**: Admin requests for increased user limits

## Payment System

The application integrates with Razorpay for secure payment processing:

1. **Order Booking Fee**: Small initial payment to confirm order placement
2. **Full Payment**: Complete payment for the entire order
3. **Partial Payment**: Flexible payment options for customers
4. **Subscription Payments**: For admin and customer account access

## Deployment

For production deployment:

1. Set `DEBUG=False` in your environment variables
2. Configure a production-ready database
3. Set up a proper web server (Nginx, Apache, etc.)
4. Use WSGI server like Gunicorn:
   ```bash
   gunicorn paddy_proj.wsgi:application
   ```

## Development

### Running Tests
```bash
python manage.py test paddy_app
```

### Code Style
The project follows PEP 8 style guidelines. You can use flake8 for linting:
```bash
flake8 paddy_proj
```

## License

[MIT License](LICENSE)

## Contributors

- Your Name (@yourusername)
- Other Contributors

## Support

For support, please open an issue on the GitHub repository or contact us at support@example.com.
