from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, date
import json
from django.contrib import messages

# Import models from paddy_app
from paddy_app.models import (
    Orders, CustomerTable, AdminTable, OrderItems, 
    Payments, CashPaymentRequest
)
from paddy_app.decorators import role_required
from paddy_app.helpers import number_to_words_indian, create_notification

# Customer Lookup by Phone Number
@role_required(["admin", "superadmin"])
def get_customer_by_phone(request):
    """API endpoint to search customers by phone number (supports partial matches)"""
    if request.method == 'GET':
        phone_number = request.GET.get('phone_number', '').strip()
        
        if not phone_number:
            return JsonResponse({'success': False, 'message': 'Phone number is required'}, status=400)
        
        try:
            # Search for customers with phone numbers starting with the input
            customers = CustomerTable.objects.filter(phone_number__startswith=phone_number)[:10]  # Limit to 10 results
            
            if customers.exists():
                customer_list = [{
                    'customer_id': customer.customer_id,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name,
                    'phone_number': customer.phone_number,
                    'email': customer.email,
                    'company_name': customer.company_name,
                    'gst': customer.GST,
                    'address': customer.address,
                } for customer in customers]
                
                return JsonResponse({
                    'success': True,
                    'customers': customer_list
                })
            else:
                return JsonResponse({'success': False, 'message': 'No customers found', 'customers': []})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

# Customer Orders Views
@role_required(["customer"])
def customer_orders(request):
    customer_id = request.session.get("user_id")
    if not customer_id:
        return redirect('login_app:login')
    
    # Check if it's an AJAX request asking for JSON data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Fetch all orders for this customer
        orders = Orders.objects.filter(customer__customer_id=customer_id).order_by('-order_date')
        
        # Convert to JSON serializable format
        orders_data = []
        for order in orders:
            # Get order items data
            order_items_data = []
            if order.product_category_id == 3:  # Pesticide orders have multiple items
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
                # For single item orders (rice or paddy)
                product_name = "Paddy" if order.product_category_id == 2 else "Rice" if order.product_category_id == 1 else "Unknown"
                order_items_data.append({
                    'product_name': product_name,
                    'category': order.category,
                    'quantity': order.quantity,
                    'price_per_unit': float(order.price_per_unit),
                    'total_amount': float(order.overall_amount),
                    'batch_number': 'N/A',
                    'expiry_date': 'N/A',
                    'unit': 'N/A',
                })
            
            orders_data.append({
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
                'category': order.category,
                'order_items': order_items_data,  # Include order items
            })
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
            # Admins should see orders they placed, regardless of which admin the customer belongs to
            try:
                admin_instance = AdminTable.objects.get(admin_id=user_id)
                orders_query = orders_query.filter(admin=admin_instance)
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
        
        orders_data = []
        for order in orders_query:
            # Initialize cash payment requests for this specific order
            cash_payment_requests = []
            
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
                    'category': order.category,  # Add category from order
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
                    'transaction_date': str(req.transaction_date) if getattr(req, 'transaction_date', None) else None,
                    'transaction_id': getattr(req, 'transaction_id', None),
                    'screenshot_url': req.screenshot.url if getattr(req, 'screenshot', None) else None,
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
                'customer_phone': order.customer.phone_number if order.customer else None,
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
                'delivery_date': order.delivery_date.strftime('%Y-%m-%d') if order.delivery_date else None,
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
                    'category': order.category,  # Add category from order
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
                    'transaction_date': str(req.transaction_date) if getattr(req, 'transaction_date', None) else None,
                    'transaction_id': getattr(req, 'transaction_id', None),
                    'screenshot_url': req.screenshot.url if getattr(req, 'screenshot', None) else None,
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
                'customer_phone': order.customer.phone_number if order.customer else None,
                'admin_id': order.admin.admin_id if order.admin else None,
                'admin_name': admin_name,  # Add admin name
                'admin_email': admin_email,  # Add admin email
                'payment_status': order.payment_status,
                'delivery_status': order.delivery_status,
                'delivery_date': order.delivery_date.strftime('%Y-%m-%d') if order.delivery_date else None,
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
        return redirect("login_app:login")

    # Allow placing orders to any customer (platform-wide)
    customers = CustomerTable.objects.all()
    
    # Handle order submission - create order and redirect to dashboard
    if request.method == "POST":
        # Prevent duplicate submissions using session token
        form_token = request.POST.get('form_token')
        session_token = request.session.get('last_order_token')
        
        if form_token and form_token == session_token:
            # Duplicate submission detected
            messages.warning(request, "Order already submitted. Redirecting to orders page.")
            if is_superadmin:
                return redirect('orders_app:super_admin_orders')
            else:
                return redirect('orders_app:admin_orders')
        
        # Store the token to prevent duplicate submissions
        if form_token:
            request.session['last_order_token'] = form_token
        
        # For non-superadmin users, check product access before processing order
        if not is_superadmin:
            from paddy_app.models import Subscription
            product_access = Subscription.get_admin_product_access(admin_id)
            
            product_category_id = request.POST.get("product_category_id")
            if product_category_id == "1" and not product_access["rice"]:
                messages.error(request, "You don't have access to place Rice orders. Please subscribe to Rice access first.")
                return redirect('payment_app:admin_product_subscription')
            elif product_category_id == "2" and not product_access["paddy"]:
                messages.error(request, "You don't have access to place Paddy orders. Please subscribe to Paddy access first.")
                return redirect('payment_app:admin_product_subscription')
            elif product_category_id == "3" and not product_access["pesticide"]:
                messages.error(request, "You don't have access to place Pesticide orders. Please subscribe to Pesticide access first.")
                return redirect('payment_app:admin_product_subscription')
        
        # Process order data
        if str(request.POST.get("product_category_id")) != "3":
            # Regular order (Rice/Paddy)
            customer_id = request.POST.get("customer")
            product_category_id = request.POST.get("product_category_id")
            quantity = float(request.POST.get("quantity")) if request.POST.get("quantity") else 0
            price_per_unit = float(request.POST.get("price_per_unit")) if request.POST.get("price_per_unit") else 0
            overall_amount = quantity * price_per_unit
            
            customer = CustomerTable.objects.get(customer_id=customer_id)
            gst = customer.GST

            order = Orders.objects.create(
                customer=customer,
                admin=AdminTable.objects.get(admin_id=admin_id),
                payment_status=0,
                delivery_status=0,
                product_category_id=product_category_id,
                category=request.POST.get("category"),
                quantity=quantity,
                price_per_unit=price_per_unit,
                overall_amount=overall_amount,
                GST=gst,
                lorry_number=request.POST.get("vehicle_number"),
                driver_name=request.POST.get("driver_name"),
                delivery_date=request.POST.get("delivery_date"),
                driver_ph_no=request.POST.get("driver_ph_no"),
                order_date=date.today()
            )
            
            # Create notifications for order placement
            product_name = "Rice" if product_category_id == "1" else "Paddy"
            
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
                
        else:
            # Multiple products order (Pesticides)
            customer_id = request.POST.get("customer")
            customer = CustomerTable.objects.get(customer_id=customer_id)
            gst = customer.GST
            
            # Create order
            order = Orders.objects.create(
                customer=customer,
                admin=AdminTable.objects.get(admin_id=admin_id),
                payment_status=0,
                quantity=0,
                product_category_id=request.POST.get("product_category_id"),
                category=request.POST.get("category"),
                GST=gst,
                lorry_number=request.POST.get("vehicle_number"),
                driver_name=request.POST.get("driver_name"),
                delivery_date=request.POST.get("delivery_date"),
                delivery_status=0,
                driver_ph_no=request.POST.get("driver_ph_no"),
                order_date=date.today()
            )
            
            # Process each order item
            product_names = request.POST.getlist("product_name[]")
            batch_numbers = request.POST.getlist("batch_number[]")
            expiry_dates = request.POST.getlist("expiry_date[]")
            quantities = request.POST.getlist("quantity[]")
            prices = request.POST.getlist("price_per_unit[]")
            units = request.POST.getlist("unit[]")
            totals = request.POST.getlist("total_amount[]")
            
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
        
        messages.success(request, f"Order #{order.order_id} placed successfully!")
        
        # Clear the form token to prevent reuse
        if 'last_order_token' in request.session:
            del request.session['last_order_token']
        
        # Redirect back to appropriate orders page based on role
        if is_superadmin:
            return redirect('orders_app:super_admin_orders')
        else:
            return redirect('orders_app:admin_orders')
    
    # Render the initial form
    context = {"customers": customers}
    
    # For admin users, check product access
    if not is_superadmin:
        from paddy_app.models import Subscription
        context["product_access"] = Subscription.get_admin_product_access(admin_id)
    
    return render(request, "orders_app/place_order.html" if is_superadmin else "orders_app/admin_place_order.html", context)
