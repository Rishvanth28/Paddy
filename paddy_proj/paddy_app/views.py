from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from .models import *
from django.db import IntegrityError
from datetime import date
from django.core.paginator import Paginator
from django.utils import timezone
from .decorators import role_required
from .helpers import *
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
import razorpay
from django.conf import settings
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt


RAZORPAY_KEY_ID = "rzp_test_zOexMQY9CNEGzd"
RAZORPAY_SECRET = "Gmtv3UfGPIavIeneKQjkZTcu"

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))

def login_view(request):
    if request.session.get("user_id") and request.session.get("role"):
        role = request.session["role"]
        if role == "superadmin":
            return redirect("superadmin_dashboard")
        elif role == "admin":
            return redirect("admin_dashboard")
        elif role == "customer":
            return redirect("customer_dashboard")

    if request.method == "POST":
        phone_number = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")

        if not phone_number or not password or not role:
            messages.error(request, "All fields are required.")
            return redirect("login")

        if role == "superadmin":
            try:
                user = AdminTable.objects.get(phone_number=phone_number)
                if user.admin_id > 1000000:
                    messages.error(request, "Unauthorized access.")
                    return redirect("login")
                if check_password(password, user.password):
                    request.session["user_id"] = user.admin_id
                    request.session["role"] = "superadmin"
                    return redirect("superadmin_dashboard")
            except AdminTable.DoesNotExist:
                messages.error(request, "Super Admin not found.")

        elif role == "admin":
            try:
                user = AdminTable.objects.get(phone_number=phone_number)
                if user.admin_id == 1000000:
                    messages.error(request, "Unauthorized access.")
                    return redirect("login")
                if check_password(password, user.password):
                    request.session["user_id"] = user.admin_id
                    request.session["role"] = "admin"
                    sub = Subscription.objects.filter(admin_id=user, subscription_type="admin").order_by("-end_date").first()
                    if sub and sub.end_date and sub.end_date >= now().date():
                        return redirect("admin_dashboard")
                    else:
                        return redirect("admin_subscription_payment")
            except AdminTable.DoesNotExist:
                messages.error(request, "Admin not found.")

        elif role == "customer":
            try:
                user = CustomerTable.objects.get(phone_number=phone_number)
                if check_password(password, user.password):
                    request.session["user_id"] = user.customer_id
                    request.session["role"] = "customer"

                    # Subscription check
                    sub = Subscription.objects.filter(customer_id=user, subscription_type="customer").order_by("-end_date").first()
                    
                    if sub:
                        if sub.end_date and sub.end_date >= now().date():
                            return redirect("customer_dashboard")
                        else:
                            return redirect("customer_subscription_payment")
                    else:
                        # Free trial logic
                        Subscription.objects.create(
                            customer_id=user,
                            subscription_type="customer",
                            subscription_status=1,
                            payment_amount=0,
                            start_date=now().date(),
                            end_date=now().date() + timedelta(days=30)
                        )
                        return redirect("customer_dashboard")
            except CustomerTable.DoesNotExist:
                messages.error(request, "Customer not found.")

        else:
            messages.error(request, "Invalid role selected.")

    return render(request, "login.html")


@role_required(["superadmin"])
def superadmin_dashboard(request):
    return render(request, "superadmin_dashboard.html")

@role_required(["admin"])
def admin_dashboard(request):
    return render(request, "admin_dashboard.html")

def upgrade_plan(request):
    return render(request, "upgrade_plan.html")

@role_required(["customer"])
def customer_dashboard(request):
    return render(request, "customer_dashboard.html")

def validate_gst(gst):
    gst_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(gst_pattern, gst))

@role_required(["superadmin"])
def onboard(request):
    return render(request, "onboard.html")

@role_required(["superadmin"])
def create_admin(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone_number = request.POST.get("phone_number")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Check for existing email or phone number
        if AdminTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for an admin!")
            return redirect("onboard")

        if AdminTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for an admin!")
            return redirect("onboard")

        try:
            AdminTable.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                password=password,
                user_count=50
            )
            messages.success(request, "Admin created successfully!")
            return redirect("onboard")
        except IntegrityError:
            messages.error(request, "Failed to create admin. Please try again.")
            messages.warning(request, "This email is already registered.")
            messages.info(request, "Please fill all required fields.")
            
    return render(request, "onboard.html")

@role_required(["superadmin", "admin"])
def create_customer(request):
    role = request.session.get("role")
    is_superadmin = role == "superadmin"

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone_number = request.POST.get("phone_number")
        email = request.POST.get("email")
        password = request.POST.get("password")
        company_name = request.POST.get("company_name")
        gst = request.POST.get("gst")
        address = request.POST.get("address")

        admin_id = request.session.get("user_id")
        if not admin_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login")

        try:
            admin = AdminTable.objects.get(admin_id=admin_id)
        except AdminTable.DoesNotExist:
            messages.error(request, "Admin not found. Please log in again.")
            return redirect("login")

        current_customer_count = CustomerTable.objects.filter(admin=admin).count()
        if current_customer_count >= admin.user_count:
            messages.error(request, "Customer limit reached for your account!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        if CustomerTable.objects.filter(email=email).exists():
            messages.error(request, "Email already exists for a customer!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        if CustomerTable.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "Phone number already registered for a customer!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        if gst and not validate_gst(gst):
            messages.error(request, "Invalid GST number format!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        try:
            customer = CustomerTable.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                password=make_password(password),
                company_name=company_name,
                GST=gst if gst else None,
                address=address,
                admin=admin,
            )

            # ✅ Create default 1-month free subscription for customer
            Subscription.objects.create(
                customer_id=customer,
                subscription_type="customer",
                subscription_status=1,
                payment_amount=0,
                start_date=now().date(),
                end_date=now().date() + timedelta(days=30)
            )

            messages.success(request, "Customer created successfully!")
            return redirect("onboard" if is_superadmin else "customer_onboard")

        except IntegrityError:
            messages.error(request, "Failed to create customer. Please try again.")

    return render(request, "onboard.html" if is_superadmin else "customer_onboard.html")


@role_required(["superadmin", "admin"])
def place_order(request):
    role = request.session.get("role")  # adjust based on how role is stored in session
    is_superadmin = role == "superadmin"

    admin_id = request.session.get("user_id")
    if not admin_id:
        return redirect("login")

    customers = CustomerTable.objects.filter(admin__admin_id=admin_id)

    if request.method == "POST":
        if str(request.POST.get("product_category_id")) != "3":
            customer_id = request.POST.get("customer")
            product_category_id = request.POST.get("product_category_id")
            quantity = request.POST.get("quantity")
            price_per_unit = request.POST.get("price_per_unit")
            lorry_number = request.POST.get("vehicle_number")
            driver_name = request.POST.get("driver_name")
            driver_ph_no = request.POST.get("driver_ph_no")
            delivery_date = request.POST.get("delivery_date")

            try:
                customer = CustomerTable.objects.get(customer_id=customer_id)
                gst = customer.GST

                quantity = float(quantity) if quantity else 0
                price_per_unit = float(price_per_unit) if price_per_unit else 0
                overall_amount = quantity * price_per_unit

                Orders.objects.create(
                    customer=customer,
                    admin=AdminTable.objects.get(admin_id=admin_id),
                    payment_status=0,
                    delivery_status=0,
                    product_category_id=product_category_id,
                    quantity=quantity,
                    price_per_unit=price_per_unit,
                    overall_amount=overall_amount,
                    GST=gst,
                    lorry_number=lorry_number,
                    driver_name=driver_name,
                    delivery_date=delivery_date,
                    driver_ph_no=driver_ph_no,
                    order_date=date.today()
                )

                return redirect("place_order" if is_superadmin else "admin_place_order")

            except Exception as e:
                print("Error placing order:", e)
        else:
            try:
                # Extract order-level data
                customer_id = request.POST.get('customer')
                # payment_terms = request.POST.get('payment_terms')
                lorry_number = request.POST.get("vehicle_number")
                driver_name = request.POST.get("driver_name")
                driver_ph_no = request.POST.get("driver_ph_no")
                delivery_date = request.POST.get("delivery_date")   
                product_category_id = request.POST.get("product_category_id")
                
                customer = CustomerTable.objects.get(customer_id=customer_id)
                gst = customer.GST
                # Create order
                order = Orders.objects.create(
                        customer=customer,
                        admin = AdminTable.objects.get(admin_id=admin_id),
                        #payment_terms=payment_terms,
                        payment_status=0,
                        quantity = 0,
                        product_category_id=product_category_id,
                        GST=gst,
                        lorry_number=lorry_number,
                        driver_name=driver_name,
                        delivery_date=delivery_date,
                        delivery_status=0,
                        driver_ph_no=driver_ph_no,
                        order_date=date.today()
                    )
                
                # Process each order item
                product_names = request.POST.getlist('product_name[]')
                batch_numbers = request.POST.getlist('batch_number[]')
                expiry_dates = request.POST.getlist('expiry_date[]')
                quantities = request.POST.getlist('quantity[]')
                prices = request.POST.getlist('price_per_unit[]')
                units = request.POST.getlist('unit[]')
                totals = request.POST.getlist('total_amount[]')
                
                # Create order items
                order_items = []
                for i in range(len(product_names)):
                    # Skip empty rows
                    if not product_names[i].strip():
                        continue
                        
                    item = OrderItems(
                        order=order,
                        product_name=product_names[i],
                        batch_number=batch_numbers[i],
                        expiry_date=expiry_dates[i],
                        quantity=int(float(quantities[i])),
                        price_per_unit=float(prices[i]),
                        total_amount=float(totals[i]),
                        unit=units[i]
                    )
                    order_items.append(item)
                order.overall_amount = sum(float(totals[i]) for i in range(len(totals)) if totals[i].strip())
                order.save()
                # Bulk create items
                OrderItems.objects.bulk_create(order_items)
                
                messages.success(request, 'Order saved successfully!')
                return redirect('place_order' if is_superadmin else 'admin_place_order')

            
            except Exception as e:
                messages.error(request, f'Error saving order: {str(e)}')
                return redirect('place_order' if is_superadmin else 'admin_place_order')

    return render(request, "place_order.html" if is_superadmin else "admin_place_order.html", {"customers": customers})

@role_required(["customer"])
def customer_orders(request):
    customer_id = request.session.get("user_id")
    if not customer_id:
        return redirect('login')
    
    # Check if it's an AJAX request asking for JSON data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Fetch all orders for this customer
        orders = Orders.objects.filter(customer__customer_id=customer_id).order_by('-order_date')
        
        # Convert to JSON serializable format
        orders_data = [{
            'order_id': order.order_id,
            'order_date': order.order_date.strftime('%Y-%m-%d'),
            'delivery_date': order.delivery_date.strftime('%Y-%m-%d') if order.delivery_date else None,
            'overall_amount': order.overall_amount,
            'paid_amount': order.paid_amount,
            'payment_status': order.payment_status,
            'delivery_status': order.delivery_status,
            'quantity': order.quantity,
            'price_per_unit': float(order.price_per_unit),
            'GST': order.GST,
            'lorry_number': order.lorry_number,
            'driver_name': order.driver_name,
            'driver_ph_no': order.driver_ph_no,
            'product_category_id': order.product_category_id
        } for order in orders]
        
        return JsonResponse({'orders': orders_data})
    
    # For regular page load, just render the template (JS will fetch data)
    return render(request, 'customer_order.html')

@role_required(["customer"])
def payment(request):
    id = request.POST.get('order_id')
    order = Orders.objects.get(pk=id)
    # Assuming you have a related model for order items/products
    # If not, you'll need to create one to store multiple products per order
    if order.product_category_id == 3:
        order_items = OrderItems.objects.filter(order=order)
        order_items = [{'quantity':item.quantity,'price_per_unit':item.price_per_unit,
                        'total_amount':item.total_amount,'product_name':item.product_name} for item in order_items]
    else:
        order_items = [{'quantity':order.quantity,'price_per_unit':order.price_per_unit,
                        'total_amount':order.overall_amount,'product_name':'Paddy' if order.product_category_id == 2 else 'Rice'}]
    context = {
        'order': order,
        'order_name': 'Paddy' if order.product_category_id == 2 else 'Rice' if order.product_category_id == 1 else 'Fertilizer',
        'order_items': order_items,
        'customer': order.customer,
        'total_amount': order.overall_amount,
        'payment_terms': order.payment_deadline,
        'invoice_date': order.order_date,
        'total_items': sum(item['quantity'] for item in order_items),
        'invoice_number': f"UFs {order.order_id}",
        'amount_in_words': number_to_words_indian(order.overall_amount),
        'business_year': "urakadai "+str(order.order_date.year),
    }
    return render(request, 'payment.html',context)

def customer_delivery_validation(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        delivery_status = request.POST.get('delivery_status')

        try:
            order = Orders.objects.get(order_id=order_id)
            order.delivery_status = delivery_status
            order.save()
            messages.success(request, "Delivery status updated successfully.")
            return redirect('customer_orders')
        except Orders.DoesNotExist:
            return redirect('customer_orders')

@role_required(["admin"])
def customer_onboard_view(request):
    return render(request, "customer_onboard.html")

@role_required(["admin"])
def admin_add_subscription(request):
    user_id = request.session.get("user_id")
    admin = AdminTable.objects.get(admin_id=user_id)
    user_count = admin.user_count
    existing_subscription = Subscription.objects.filter(admin_id=user_id, subscription_type=1).first()
    print(existing_subscription)
    if request.method == "POST":
        if request.POST.get("submission_type") == '0': 
            try:
                Subscription.objects.create(
                    admin_id=admin,
                    subscription_type=1, # 1 is for admin user addition
                    additional_users=50, # 50 is the default value for admin user addition
                )
                messages.success(request, "Subscription Request added successfully!")
            except Exception:
                messages.error(request, "Failed to add subscription. Please try again.")
    return render(request, "admin_add_subscription.html", {"user_count": user_count,
                                                        "added_count":user_count+50,
                                                        "existing_subscription": 1 if existing_subscription else 0,
                                                        "payment_amount": existing_subscription.payment_amount if existing_subscription else 0,
                                                        "subscription_status": existing_subscription.subscription_status if existing_subscription else 0,
                                                        })

@role_required(["superadmin"])
def superadmin_subscription(request):
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    subscriptions_queryset = Subscription.objects.filter(subscription_type='1').order_by('-sid')
    
    # Apply status filter if provided
    if status_filter != '':
        subscriptions_queryset = subscriptions_queryset.filter(subscription_status=status_filter)
    
    # Pagination
    paginator = Paginator(subscriptions_queryset, 10)  # 10 items per page
    page_number = request.GET.get('page', 1)
    subscriptions = paginator.get_page(page_number)
    
    context = {
        'subscriptions': subscriptions,
    }
    
    return render(request, 'superadmin_subscription.html', context)

@role_required(["superadmin"])
def superadmin_subscription_review(request):
    if request.method == 'POST':
        subscription_id = request.POST.get('subscription_id')
        subscription_status = request.POST.get('subscription_status')
        payment_amount = request.POST.get('payment_amount')
        try:
            subscription = Subscription.objects.get(sid=subscription_id)
            
            # Update subscription
            subscription.subscription_status = subscription_status
            
            if subscription_status == '1':  # If approved
                subscription.payment_amount = payment_amount
                messages.success(request, f"Subscription request #{subscription_id} has been approved.")
            elif subscription_status == '2':  # If rejected
                messages.info(request, f"Subscription request #{subscription_id} has been rejected.")
            
            subscription.save()
            
        except Subscription.DoesNotExist:
            messages.error(request, "Subscription request not found.")
        
        return redirect('superadmin_subscription')
    
    # If not POST, redirect to the list view
    return redirect('superadmin_subscription')

@role_required(["customer"])
def upgrade_to_admin(request):
    customer_id = request.session.get('user_id')
    customer = CustomerTable.objects.get(customer_id=customer_id)

    # Check if already admin
    if AdminTable.objects.filter(email=customer.email).exists():
        messages.info(request, "You are already an admin! Access denied.")
        return render(request, 'upgrade_to_admin.html', {'customer': customer})

    if request.method == 'POST':
        # Create new admin
        new_admin = AdminTable(
            first_name=customer.first_name,
            last_name=customer.last_name,
            phone_number=customer.phone_number,
            email=customer.email,
            password=customer.password,  # already hashed
            user_count=0,
        )
        new_admin.save()

        messages.success(request, "You have been upgraded to admin successfully!")
        return render(request, 'upgrade_to_admin.html', {'customer': customer})

    return render(request, 'upgrade_to_admin.html', {'customer': customer})

@role_required(["admin"])
def upgrade_to_customer(request):
    admin_id = request.session.get('user_id')
    admin = AdminTable.objects.get(admin_id=admin_id)

    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        gst = request.POST.get('GST')
        address = request.POST.get('address')

        # check if already in CustomerTable
        if CustomerTable.objects.filter(email=admin.email).exists():
            messages.info(request, "You are already a customer!")
            return redirect('admin_dashboard')

        # check if customer is already admin also
        if AdminTable.objects.filter(email=admin.email).exists():
            messages.warning(request, "You are already registered as admin!")

        new_customer = CustomerTable(
            first_name=admin.first_name,
            last_name=admin.last_name,
            phone_number=admin.phone_number,
            email=admin.email,
            password=admin.password,  # already hashed
            admin=admin,  # setting admin foreign key if needed
            company_name=company_name,
            GST=gst,
            address=address,
        )
        new_customer.save()
        messages.success(request, "You have been upgraded to customer successfully!")
        return redirect('admin_dashboard')

    return render(request, 'upgrade_to_customer.html', {'admin': admin})

def upgrade_success(request):
    return render(request, 'upgrade_success.html')

@role_required(["customer"])
def customer_dashboard(request):
    return render(request, 'customer_dashboard.html')

@role_required(["superadmin"])
def view_admins(request):
    admins = AdminTable.objects.exclude(admin_id=1000000)
    return render(request, 'view_admins.html', {'admins': admins})

@role_required(["superadmin"])
def delete_admin(request, admin_id):
    if request.method == "POST":
        admin = get_object_or_404(AdminTable, admin_id=admin_id)

        # Prevent deletion of primary superadmin
        if admin.admin_id == 1000000:
            messages.error(request, "Superadmin cannot be deleted.")
            return redirect("view_admins")

        admin.delete()
        messages.success(request, f"Admin {admin.first_name} {admin.last_name} deleted successfully.")
        return redirect("view_admins")
    else:
        messages.error(request, "Invalid request method.")
        return redirect("view_admins")

@role_required(["superadmin", "admin"])
def view_customers_under_admin(request, admin_id):
    try:
        admin = AdminTable.objects.get(admin_id=admin_id)
    except AdminTable.DoesNotExist:
        messages.error(request, "Admin not found.")
        return redirect('view_admins')

    customers = CustomerTable.objects.filter(admin__admin_id=admin_id)
    return render(request, 'admin_customers.html', {
        'admin': admin,
        'customers': customers
    })

@role_required(["superadmin", "admin"])
def delete_customer(request, customer_id):
    if request.method == "POST":
        try:
            customer = CustomerTable.objects.get(customer_id=customer_id)
            customer.delete()
            messages.success(request, "Customer deleted successfully.")
        except CustomerTable.DoesNotExist:
            messages.error(request, "Customer not found.")
    return redirect(request.META.get("HTTP_REFERER", "view_admins"))
    
def logout_view(request):
    request.session.flush()  # Clears session data
    messages.success(request, "Logged out successfully.")
    return redirect("login")

@role_required(["superadmin", "admin"])
def customers_under_admin(request):
    admin_id = request.session.get("user_id")  # session must store admin_id during login
    role = request.session.get("role")  # adjust based on how role is stored in session
    is_superadmin = role == "superadmin"
    if not admin_id:
        return redirect('admin_login')  # redirect if not logged in

    # Fetch customers for the current admin
    customers = CustomerTable.objects.filter(admin_id=admin_id)

    return render(request, "customers_list.html" if is_superadmin else "admin_customer_list.html", {"customers": customers})

def admin_login_submit(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            admin = AdminTable.objects.get(email=email)
            if admin.check_password(password):
                request.session['user_id'] = admin.admin_id
                return redirect('customers_under_admin')
        except AdminTable.DoesNotExist:
            pass
    return render(request, 'login.html', {'error': 'Invalid credentials'})

def demo(request):
    return render(request, 'demo.html')

def admin_subscription_payment(request):
    if request.method == "POST":
        plan = request.POST.get("plan")
        admin_id = request.session.get("user_id")

        if not admin_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login")

        amount = 200 if plan == "1month" else 350
        duration = 30 if plan == "1month" else 60

        order_data = {
            "amount": amount * 100,  # In paise
            "currency": "INR",
            "payment_capture": "1"
        }

        razorpay_order = client.order.create(data=order_data)

        # Save session details
        request.session["subscription_amount"] = amount
        request.session["subscription_days"] = duration
        request.session["razorpay_order_id"] = razorpay_order["id"]
        request.session["subscription_type"] = "admin"
        request.session["subscription_for"] = "admin"
        request.session["admin_id"] = admin_id

        return render(request, "admin_subscription_payment.html", {
            "order_id": razorpay_order["id"],
            "amount": amount * 100,
            "key_id": RAZORPAY_KEY_ID
        })

    return render(request, "admin_select_subscription_plan.html")

def customer_subscription_payment(request):
    if request.method == "POST":
        plan = request.POST.get("plan")
        customer_id = request.session.get("user_id")

        if not customer_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login")

        amount = 100 if plan == "1month" else 180
        duration = 30 if plan == "1month" else 60

        order_data = {
            "amount": amount * 100,  # In paise
            "currency": "INR",
            "payment_capture": "1"
        }

        razorpay_order = client.order.create(data=order_data)

        # Save session details
        request.session["subscription_amount"] = amount
        request.session["subscription_days"] = duration
        request.session["razorpay_order_id"] = razorpay_order["id"]
        request.session["subscription_type"] = "customer"
        request.session["subscription_for"] = "customer"
        request.session["admin_id"] = customer_id

        return render(request, "customer_subscription_payment.html", {
            "order_id": razorpay_order["id"],
            "amount": amount * 100,
            "key_id": RAZORPAY_KEY_ID
        })

    return render(request, "customer_select_subscription_plan.html")


@csrf_exempt
def customer_payment_success(request):
    if request.method == "POST":
        try:
            import json
            import traceback

            data = json.loads(request.body)
            print("💡 Incoming Razorpay Data:", data)

            customer_id = request.session.get("user_id")
            amount = request.session.get("subscription_amount")
            days = request.session.get("subscription_days")

            print("💡 Session Values - customer_id:", customer_id, "amount:", amount, "days:", days)

            # Validate session values
            if not all([customer_id, amount, days]):
                print("⚠️ Missing session data.")
                return JsonResponse({"success": False, "message": "Session data missing or expired. Please log in again."})

            # Try to find existing subscription
            existing_subscription = Subscription.objects.filter(
                customer_id=customer_id,
                subscription_type="customer"
            ).order_by("-end_date").first()

            if existing_subscription:
                # Extend existing subscription
                existing_subscription.start_date = now().date()
                existing_subscription.end_date = (existing_subscription.end_date or now().date()) + timedelta(days=int(days))
                existing_subscription.payment_amount += int(amount)
                existing_subscription.subscription_status = 1
                existing_subscription.save()

                print("✅ Existing subscription updated.")
                return JsonResponse({"success": True, "message": "Subscription extended successfully."})

            # Create new subscription
            Subscription.objects.create(
                customer_id_id=customer_id,
                subscription_type="customer",
                payment_amount=int(amount),
                start_date=now().date(),
                end_date=now().date() + timedelta(days=int(days)),
                subscription_status=1
            )

            print("✅ New subscription created.")
            return JsonResponse({"success": True, "message": "Subscription created successfully."})

        except Exception as e:
            print("🔴 Error during payment success:")
            traceback.print_exc()
            return JsonResponse({"success": False, "message": f"Error: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request. Expected POST method."})


@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        try:
            # Parse the incoming JSON data
            import json
            data = json.loads(request.body)

            admin_id = request.session.get("user_id")
            amount = request.session.get("subscription_amount")
            days = request.session.get("subscription_days")

            # Ensure that necessary session data is present
            if not all([admin_id, amount, days]):
                return JsonResponse({"success": False, "message": "Session data missing or expired. Please log in again."})

            # Check if the admin already has a subscription and update the subscription if it exists
            existing_subscription = Subscription.objects.filter(admin_id=admin_id, subscription_type="admin").order_by("-end_date").first()

            if existing_subscription:
                # Extend the existing subscription by the specified number of days
                existing_subscription.start_date = now().date()
                existing_subscription.end_date = existing_subscription.end_date + timedelta(days=int(days))
                existing_subscription.payment_amount += amount  # Add the new payment amount to the existing one
                existing_subscription.save()
                return JsonResponse({"success": True, "message": "Subscription extended successfully."})

            # If no existing subscription, create a new one
            Subscription.objects.create(
                admin_id_id=admin_id,
                subscription_type="admin",
                payment_amount=amount,
                start_date=now().date(),
                end_date=now().date() + timedelta(days=int(days)),
                subscription_status=1
            )

            return JsonResponse({"success": True, "message": "Subscription created successfully."})

        except Exception as e:
            print("Error during payment success:", e)
            return JsonResponse({"success": False, "message": "Error processing subscription. Please try again."})

    # Handle invalid request type
    return JsonResponse({"success": False, "message": "Invalid request. Expected POST method."})


def swap_role(request):
    current_role = request.session.get("role")
    user_id = request.session.get("user_id")

    if current_role == "admin":
        try:
            admin = AdminTable.objects.get(admin_id=user_id)
            customer = CustomerTable.objects.get(phone_number=admin.phone_number)

            # Logout admin
            request.session.flush()

            # Login as customer
            request.session["user_id"] = customer.customer_id
            request.session["role"] = "customer"
            messages.success(request, "Switched to Customer account.")
            return redirect("customer_dashboard")

        except CustomerTable.DoesNotExist:
            messages.warning(request, "You don’t have a Customer account linked. Please subscribe or contact support.")
            return redirect("admin_dashboard")

    elif current_role == "customer":
        try:
            customer = CustomerTable.objects.get(customer_id=user_id)
            admin = AdminTable.objects.get(phone_number=customer.phone_number)

            # Logout customer
            request.session.flush()

            # Login as admin
            request.session["user_id"] = admin.admin_id
            request.session["role"] = "admin"
            messages.success(request, "Switched to Admin account.")
            return redirect("admin_dashboard")

        except AdminTable.DoesNotExist:
            messages.warning(request, "You don’t have an Admin account linked. Please subscribe or contact support.")
            return redirect("customer_dashboard")

    messages.error(request, "Invalid session. Please log in again.")
    return redirect("login")



def view_admin_subscribers(request):
    admin_subscriptions = Subscription.objects.filter(subscription_type="admin").select_related('admin_id').order_by('-start_date')
    return render(request, "admin_subscribers.html", {"subscriptions": admin_subscriptions})

def view_customer_subscribers(request):
    customer_subscriptions = Subscription.objects.filter(subscription_type="customer").select_related('customer_id').order_by('-start_date')
    return render(request, "customer_subscribers.html", {"subscriptions": customer_subscriptions})