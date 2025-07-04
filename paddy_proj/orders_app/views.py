from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, date
import json
import os
import razorpay
from django.contrib import messages

# Import models from paddy_app
from paddy_app.models import (
    Orders, CustomerTable, AdminTable, OrderItems, 
    Payments, CashPaymentRequest
)
from paddy_app.decorators import role_required
from paddy_app.helpers import number_to_words_indian, create_notification

# Razorpay configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))

# Customer Orders Views
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
            'product_category_id': order.product_category_id,
            'category': order.category,  # Include category field
        } for order in orders]
        return JsonResponse({'orders': orders_data})
    
    # For regular page load, just render the template (JS will fetch data)
    return render(request, 'orders_app/customer_orders.html')

@role_required(["customer"])
def customer_delivery_validation(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        delivery_status = request.POST.get('delivery_status')

        try:
            order = Orders.objects.get(order_id=order_id)
            order.delivery_status = delivery_status
            order.save()
            
            # Create notification for admin when customer marks delivery as complete
            if delivery_status == '1':  # Assuming 1 means delivered
                product_name = "Rice" if order.product_category_id == 1 else "Paddy" if order.product_category_id == 2 else "Pesticide"
                
                # Notification for admin
                from paddy_app.helpers import create_notification
                create_notification(
                    user_type='admin',
                    user_id=order.admin.admin_id,
                    notification_type='delivery_confirmed',
                    title='Order Delivery Confirmed',
                    message=f'Customer {order.customer.first_name} {order.customer.last_name} has confirmed delivery of {product_name} order #{order.order_id}.',
                    related_order_id=order.order_id
                )
            
            messages.success(request, "Delivery status updated successfully.")
            return redirect('orders_app:customer_orders')
        except Orders.DoesNotExist:
            return redirect('orders_app:customer_orders')

# Admin Orders Views
@role_required(["admin"])
def admin_orders(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        user_id = request.session.get("user_id")
        role = request.session.get("role")

        if not user_id or not role:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        orders_query = Orders.objects.all()

        if role == 'admin':
            # Admins can only see orders associated with their customers
            try:
                admin_instance = AdminTable.objects.get(admin_id=user_id)
                customer_ids_for_admin = CustomerTable.objects.filter(admin=admin_instance).values_list('customer_id', flat=True)
                orders_query = orders_query.filter(customer__customer_id__in=customer_ids_for_admin)
            except AdminTable.DoesNotExist:
                return JsonResponse({'error': 'Admin not found'}, status=404)

        # Apply filters from query parameters
        status_filter = request.GET.get('status', 'all')
        date_from_str = request.GET.get('date_from')
        date_to_str = request.GET.get('date_to')
        category_filter = request.GET.get('category', 'all')
        search_query = request.GET.get('search', '').strip()
        sort_by = request.GET.get('sort', '-order_id') # Default sort by latest order

        # Status filter
        if status_filter == 'completed':
            orders_query = orders_query.filter(delivery_status=1)
        elif status_filter == 'ongoing':
            orders_query = orders_query.filter(delivery_status=0)
        elif status_filter == 'pending_payment':
            orders_query = orders_query.filter(payment_status=0)
        elif status_filter == 'recent':
            seven_days_ago = timezone.now().date() - timedelta(days=7)
            orders_query = orders_query.filter(order_date__gte=seven_days_ago)

        # Date range filter
        if date_from_str:
            try:
                date_from = date.fromisoformat(date_from_str)
                orders_query = orders_query.filter(order_date__gte=date_from)
            except ValueError:
                pass # Invalid date format, ignore filter
        if date_to_str:
            try:
                date_to = date.fromisoformat(date_to_str)
                orders_query = orders_query.filter(order_date__lte=date_to)
            except ValueError:
                pass # Invalid date format, ignore filter

        # Category filter
        if category_filter != 'all':
            try:
                category_id = int(category_filter)
                orders_query = orders_query.filter(product_category_id=category_id)
            except ValueError:
                pass # Invalid category ID, ignore filter

        # Search filter (order ID, customer ID, customer name)
        if search_query:
            orders_query = orders_query.filter(
                Q(order_id__icontains=search_query) |
                Q(customer__customer_id__icontains=search_query) |
                Q(customer__first_name__icontains=search_query) |
                Q(customer__last_name__icontains=search_query)
            )

        if request.GET.get('pending_cash') == 'true':
            orders_with_pending_cash = CashPaymentRequest.objects.filter(
                status=0  # Pending status
            ).values_list('order_id', flat=True)
            
            orders_query = orders_query.filter(order_id__in=orders_with_pending_cash)
                # Apply sorting
            orders_query = orders_query.order_by(sort_by)

        cash_payment_requests = []
        
        orders_data = []
        for order in orders_query:
            order_items_data = []
            if order.product_category_id == 3: # Assuming 3 is for multiple items
                for item in order.items.all():
                    order_items_data.append({
                        'product_name': item.product_name,
                        'batch_number': item.batch_number,
                        'expiry_date': str(item.expiry_date),
                        'quantity': item.quantity,
                        'price_per_unit': float(item.price_per_unit),
                        'total_amount': float(item.total_amount),
                        'unit': item.unit,
                    })
            else:
                # For single item orders, infer product name
                product_name = "Paddy" if order.product_category_id == 2 else "Rice" if order.product_category_id == 1 else "Unknown"
                order_items_data.append({
                    'product_name': product_name,
                    'quantity': order.quantity,
                    'price_per_unit': float(order.price_per_unit),
                    'total_amount': float(order.overall_amount),
                    'batch_number': 'N/A', # Not applicable for single items based on current model
                    'expiry_date': 'N/A', # Not applicable for single items based on current model
                    'unit': 'N/A', # Not applicable for single items based on current model
                })

            customer_full_name = f"{order.customer.first_name} {order.customer.last_name}" if order.customer else "N/A"
            
            for req in CashPaymentRequest.objects.filter(order=order).select_related('processed_by'):
                cash_req_data = {
                    'request_id': req.request_id,
                    'amount': float(req.amount),
                    'reference': req.reference,
                    'notes': req.notes,
                    'status': req.status,
                    'created_at': req.created_at.isoformat(),
                }
                
                if req.processed_at:
                    cash_req_data['processed_at'] = req.processed_at.isoformat()
                    
                if req.processed_by:
                    cash_req_data['processed_by_name'] = f"{req.processed_by.first_name} {req.processed_by.last_name}"
                    
                cash_payment_requests.append(cash_req_data)

            orders_data.append({
                'order_id': order.order_id,
                'customer_id': order.customer.customer_id if order.customer else None,
                'customer_full_name': customer_full_name,
                'admin_id': order.admin.admin_id if order.admin else None,
                'payment_status': order.payment_status,
                'delivery_status': order.delivery_status,
                'product_category_id': order.product_category_id,
                'category': order.category,
                'quantity': float(order.quantity),
                'price_per_unit': float(order.price_per_unit),
                'overall_amount': float(order.overall_amount),
                'GST': order.GST,
                'lorry_number': order.lorry_number,
                'driver_name': order.driver_name,
                'driver_ph_no': order.driver_ph_no,
                'order_date': str(order.order_date),
                'paid_amount': float(order.paid_amount) if order.paid_amount is not None else 0.0,
                'order_items': order_items_data,
                'category': order.category,
                'cash_payment_requests': cash_payment_requests,
            })
        return JsonResponse({'orders': orders_data})

    return render(request, "orders_app/admin_orders.html")

# Superadmin Orders Views
@role_required(["superadmin"])
def super_admin_orders(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        user_id = request.session.get("user_id")
        role = request.session.get("role")

        if not user_id or not role:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        orders_query = Orders.objects.all()

        if role == 'admin':
            # Admins can only see orders associated with their customers
            try:
                admin_instance = AdminTable.objects.get(admin_id=user_id)
                customer_ids_for_admin = CustomerTable.objects.filter(admin=admin_instance).values_list('customer_id', flat=True)
                orders_query = orders_query.filter(customer__customer_id__in=customer_ids_for_admin)
            except AdminTable.DoesNotExist:
                return JsonResponse({'error': 'Admin not found'}, status=404)

        # Apply filters from query parameters
        status_filter = request.GET.get('status', 'all')
        date_from_str = request.GET.get('date_from')
        date_to_str = request.GET.get('date_to')
        category_filter = request.GET.get('category', 'all')
        search_query = request.GET.get('search', '').strip()
        sort_by = request.GET.get('sort', '-order_id') # Default sort by latest order
        admin_filter = request.GET.get('admin', 'all')  # Get admin filter parameter

        # Filter for orders with pending cash requests
        if request.GET.get('pending_cash') == 'true':
            # Superadmin should only see orders with pending cash requests
            # where they're the admin (admin_id = 1000000)
            orders_with_pending_cash = CashPaymentRequest.objects.filter(
                status=0,  # Pending status
                order__admin__admin_id=user_id  # Only orders where the superadmin is the admin
            ).values_list('order_id', flat=True)
            
            orders_query = orders_query.filter(order_id__in=orders_with_pending_cash)

        if admin_filter != 'all':
            orders_query = orders_query.filter(admin__admin_id=admin_filter)

        # Status filter
        if status_filter == 'completed':
            orders_query = orders_query.filter(delivery_status=1)
        elif status_filter == 'ongoing':
            orders_query = orders_query.filter(delivery_status=0)
        elif status_filter == 'pending_payment':
            orders_query = orders_query.filter(payment_status=0)
        elif status_filter == 'recent':
            seven_days_ago = timezone.now().date() - timedelta(days=7)
            orders_query = orders_query.filter(order_date__gte=seven_days_ago)

        # Date range filter
        if date_from_str:
            try:
                date_from = date.fromisoformat(date_from_str)
                orders_query = orders_query.filter(order_date__gte=date_from)
            except ValueError:
                pass # Invalid date format, ignore filter
        if date_to_str:
            try:
                date_to = date.fromisoformat(date_to_str)
                orders_query = orders_query.filter(order_date__lte=date_to)
            except ValueError:
                pass # Invalid date format, ignore filter

        # Category filter
        if category_filter != 'all':
            try:
                category_id = int(category_filter)
                orders_query = orders_query.filter(product_category_id=category_id)
            except ValueError:
                pass # Invalid category ID, ignore filter

        # Search filter (order ID, customer ID, customer name)
        if search_query:
            orders_query = orders_query.filter(
                Q(order_id__icontains=search_query) |
                Q(customer__customer_id__icontains=search_query) |
                Q(customer__first_name__icontains=search_query) |
                Q(customer__last_name__icontains=search_query)
            )

        # Apply sorting
        orders_query = orders_query.order_by(sort_by)
        # Use select_related to efficiently fetch related admin and customer data
        orders_query = orders_query.select_related('admin', 'customer')
        orders_data = []
        for order in orders_query:
            order_items_data = []
            if order.product_category_id == 3: # Assuming 3 is for multiple items
                for item in order.items.all():
                    order_items_data.append({
                        'product_name': item.product_name,
                        'batch_number': item.batch_number,
                        'expiry_date': str(item.expiry_date),
                        'quantity': item.quantity,
                        'price_per_unit': float(item.price_per_unit),
                        'total_amount': float(item.total_amount),
                        'unit': item.unit,
                    })
            else:
                # For single item orders, infer product name
                product_name = "Paddy" if order.product_category_id == 2 else "Rice" if order.product_category_id == 1 else "Unknown"
                order_items_data.append({
                    'product_name': product_name,
                    'quantity': order.quantity,
                    'price_per_unit': float(order.price_per_unit),
                    'total_amount': float(order.overall_amount),
                    'batch_number': 'N/A', # Not applicable for single items based on current model
                    'expiry_date': 'N/A', # Not applicable for single items based on current model
                    'unit': 'N/A', # Not applicable for single items based on current model
                })

            customer_full_name = f"{order.customer.first_name} {order.customer.last_name}" if order.customer else "N/A"
 
            admin_name = f"{order.admin.first_name} {order.admin.last_name}" if order.admin else "N/A"
            admin_email = order.admin.email if order.admin else "N/A"
            
            # Get cash payment requests for this order
            cash_payment_requests = []
            for req in CashPaymentRequest.objects.filter(order=order).select_related('processed_by'):
                cash_req_data = {
                    'request_id': req.request_id,
                    'amount': float(req.amount),
                    'reference': req.reference,
                    'notes': req.notes,
                    'status': req.status,
                    'created_at': req.created_at.isoformat(),
                }
                
                if req.processed_at:
                    cash_req_data['processed_at'] = req.processed_at.isoformat()
                    
                if req.processed_by:
                    cash_req_data['processed_by_name'] = f"{req.processed_by.first_name} {req.processed_by.last_name}"
                    
                cash_payment_requests.append(cash_req_data)
            
            orders_data.append({
                'order_id': order.order_id,
                'customer_id': order.customer.customer_id if order.customer else None,
                'customer_full_name': customer_full_name,
                'customer_phone': order.customer.phone_number,
                'admin_id': order.admin.admin_id if order.admin else None,
                'admin_name': admin_name,  # Add admin name
                'admin_email': admin_email,  # Add admin email
                'payment_status': order.payment_status,
                'delivery_status': order.delivery_status,
                'delivery_date': order.delivery_date if order.delivery_status else None,
                'product_category_id': order.product_category_id,
                'category': order.category,
                'quantity': float(order.quantity),
                'price_per_unit': float(order.price_per_unit),
                'overall_amount': float(order.overall_amount),
                'GST': order.GST if order.GST else "-",
                'lorry_number': order.lorry_number,
                'driver_name': order.driver_name,
                'driver_ph_no': order.driver_ph_no,
                'order_date': str(order.order_date),
                'paid_amount': float(order.paid_amount) if order.paid_amount is not None else 0.0,
                'order_items': order_items_data,
                'category': order.category,
                'cash_payment_requests': cash_payment_requests,  # Add cash payment requests
            })
        return JsonResponse({'orders': orders_data})
    admins = []
    if request.session.get('role') == 'superadmin':
        # Get all admins except superadmin (admin_id=1000000)
        admin_objs = AdminTable.objects.exclude(admin_id=1000000)
        admins = [{'id': admin.admin_id, 'name': f"{admin.first_name} {admin.last_name}"} for admin in admin_objs]
    
    return render(request, "orders_app/superadmin_orders.html", {'admins': admins})

# Order Placement Views
@role_required(["admin", "superadmin"])
def place_order(request):
    role = request.session.get("role")
    is_superadmin = role == "superadmin"

    admin_id = request.session.get("user_id")
    if not admin_id:
        return redirect("login")

    customers = CustomerTable.objects.filter(admin__admin_id=admin_id)
    
    # Handle Razorpay payment verification callback
    if request.method == "POST" and request.POST.get("razorpay_payment_id"):
        payment_id = request.POST.get("razorpay_payment_id")
        order_id = request.POST.get("razorpay_order_id")
        signature = request.POST.get("razorpay_signature")
        temp_data_json = request.session.get("temp_order_data")
        
        if not temp_data_json:
            messages.error(request, "Order data not found. Please try again.")
            return redirect("orders_app:place_order" if is_superadmin else "orders_app:admin_place_order")
        
        temp_data = json.loads(temp_data_json)
        
        # Verify payment
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            
            # Create payment record for booking fee
            payment = Payments.objects.create(
                order=None,  # Will be updated after order creation
                amount=10,
                date=timezone.now().date(),
                reference=payment_id,
                proof_link=payment_id,  # Razorpay payment ID as proof
                payment_method="Razorpay"
            )
            
            # Now proceed with order creation
            if temp_data["product_category_id"] != "3":                # Regular order flow
                customer = CustomerTable.objects.get(customer_id=temp_data["customer_id"])
                gst = customer.GST

                quantity = float(temp_data["quantity"]) if temp_data["quantity"] else 0
                price_per_unit = float(temp_data["price_per_unit"]) if temp_data["price_per_unit"] else 0
                overall_amount = quantity * price_per_unit

                order = Orders.objects.create(
                    customer=customer,
                    admin=AdminTable.objects.get(admin_id=admin_id),
                    payment_status=0,
                    delivery_status=0,
                    product_category_id=temp_data["product_category_id"],
                    category=temp_data.get("category"),  # Add category field
                    quantity=quantity,
                    price_per_unit=price_per_unit,
                    overall_amount=overall_amount,
                    GST=gst,
                    lorry_number=temp_data["lorry_number"],
                    driver_name=temp_data["driver_name"],
                    delivery_date=temp_data["delivery_date"],
                    driver_ph_no=temp_data["driver_ph_no"],
                    order_date=date.today()
                )
                  # Update payment with order ID
                payment.order = order
                payment.save()
                
                # Create notifications for order placement
                product_name = "Rice" if temp_data["product_category_id"] == "1" else "Paddy"
                
                # Notification for customer
                create_notification(
                    user_type='customer',
                    user_id=customer.customer_id,
                    notification_type='order_placed',
                    title=f'New {product_name} Order Placed',
                    message=f'Your {product_name} order #{order.order_id} has been placed successfully. Quantity: {quantity}, Amount: ₹{overall_amount}',
                    related_order_id=order.order_id
                )
                
                # Notification for admin
                create_notification(
                    user_type='admin',
                    user_id=admin_id,
                    notification_type='order_placed',
                    title=f'New {product_name} Order Received',
                    message=f'New {product_name} order #{order.order_id} from {customer.first_name} {customer.last_name}. Amount: ₹{overall_amount}',
                    related_order_id=order.order_id
                )
                
                messages.success(request, "Order placed successfully after booking fee payment!")
                
            else:
                # Multiple products order flow
                customer = CustomerTable.objects.get(customer_id=temp_data["customer_id"])
                gst = customer.GST
                  # Create order
                order = Orders.objects.create(
                    customer=customer,
                    admin=AdminTable.objects.get(admin_id=admin_id),
                    payment_status=0,
                    quantity=0,
                    product_category_id=temp_data["product_category_id"],
                    category=temp_data.get("category"),  # Add category field
                    GST=gst,
                    lorry_number=temp_data["lorry_number"],
                    driver_name=temp_data["driver_name"],
                    delivery_date=temp_data["delivery_date"],
                    delivery_status=0,
                    driver_ph_no=temp_data["driver_ph_no"],
                    order_date=date.today()
                )
                
                # Update payment with order ID
                payment.order = order
                payment.save()
                
                # Process each order item
                product_names = temp_data["product_names"]
                batch_numbers = temp_data["batch_numbers"]
                expiry_dates = temp_data["expiry_dates"]
                quantities = temp_data["quantities"]
                prices = temp_data["prices"]
                units = temp_data["units"]
                totals = temp_data["totals"]
                
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
                
                # Create notifications for pesticide order
                create_notification(
                    user_type='customer',
                    user_id=customer.customer_id,
                    notification_type='order_placed',
                    title='New Pesticide Order Placed',
                    message=f'Your pesticide order #{order.order_id} with multiple items has been placed successfully. Total Amount: ₹{order.overall_amount}',
                    related_order_id=order.order_id
                )
                
                # Notification for admin
                create_notification(
                    user_type='admin',
                    user_id=admin_id,
                    notification_type='order_placed',
                    title='New Pesticide Order Received',
                    message=f'New pesticide order #{order.order_id} from {customer.first_name} {customer.last_name} with {len(order_items)} items. Total Amount: ₹{order.overall_amount}',
                    related_order_id=order.order_id
                )
                
                messages.success(request, "Order with multiple items placed successfully after booking fee payment!")
            
            # Clear temporary data
            if "temp_order_data" in request.session:
                del request.session["temp_order_data"]
                
            return redirect("orders_app:place_order" if is_superadmin else "orders_app:admin_place_order")
            
        except Exception as e:
            messages.error(request, f"Payment verification failed: {str(e)}")
            return redirect("orders_app:place_order" if is_superadmin else "orders_app:admin_place_order")
    
    # Handle AJAX request for creating Razorpay order
    elif request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Store order data temporarily
        temp_data = {}
        
        if str(request.POST.get("product_category_id")) != "3":
            # Regular order
            temp_data = {
                "customer_id": request.POST.get("customer"),
                "product_category_id": request.POST.get("product_category_id"),
                "category": request.POST.get("category"),  # Add category field
                "quantity": request.POST.get("quantity"),
                "price_per_unit": request.POST.get("price_per_unit"),
                "lorry_number": request.POST.get("vehicle_number"),
                "driver_name": request.POST.get("driver_name"),
                "driver_ph_no": request.POST.get("driver_ph_no"),
                "delivery_date": request.POST.get("delivery_date")
            }
            
        else:
            # Multiple products order
            temp_data = {
                "customer_id": request.POST.get("customer"),
                "product_category_id": request.POST.get("product_category_id"),
                "category": request.POST.get("category"),  # Add category field
                "lorry_number": request.POST.get("vehicle_number"),
                "driver_name": request.POST.get("driver_name"),
                "driver_ph_no": request.POST.get("driver_ph_no"),
                "delivery_date": request.POST.get("delivery_date"),
                "product_names": request.POST.getlist("product_name[]"),
                "batch_numbers": request.POST.getlist("batch_number[]"),
                "expiry_dates": request.POST.getlist("expiry_date[]"),
                "quantities": request.POST.getlist("quantity[]"),
                "prices": request.POST.getlist("price_per_unit[]"),
                "units": request.POST.getlist("unit[]"),
                "totals": request.POST.getlist("total_amount[]")
            }
        
        # Store data in session
        request.session["temp_order_data"] = json.dumps(temp_data)
        
        # Create Razorpay order for booking fee
        try:
            razorpay_order = client.order.create({
                "amount": 1000,  # 10 Rs in paise
                "currency": "INR",
                "payment_capture": 1,  # Auto-capture
                "notes": {
                    "purpose": "Order booking fee",
                    "admin_id": str(admin_id)
                }
            })
            
            # Return JSON response for AJAX
            return JsonResponse({
                "status": "success",
                "razorpay_key": RAZORPAY_KEY_ID,
                "order_id": razorpay_order["id"],
                "amount": 10  # In Rs
            })
            
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"Error creating payment: {str(e)}"
            })
    
    # Render the initial form
    return render(request, "orders_app/place_order.html" if is_superadmin else "orders_app/admin_place_order.html", {"customers": customers})
