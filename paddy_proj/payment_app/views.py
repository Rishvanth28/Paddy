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
from django.utils.timezone import now

# Import models from paddy_app
from paddy_app.models import (
    Orders, CustomerTable, AdminTable, OrderItems, 
    Payments, CashPaymentRequest, Subscription, UserIncreaseSubscription
)
from paddy_app.decorators import role_required
from paddy_app.helpers import number_to_words_indian, create_notification

# Razorpay configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))

# Order Payment Views
def payment(request):
    """Order payment view for displaying payment details and invoice"""
    id = request.POST.get('order_id')
    order = Orders.objects.get(pk=id)
    # Assuming you have a related model for order items/products
    # If not, you'll need to create one to store multiple products per order
    if order.product_category_id == 3:
        order_items = OrderItems.objects.filter(order=order)
        order_items = [{'quantity':item.quantity,'price_per_unit':item.price_per_unit,
                        'total_amount':item.total_amount,'product_name':item.product_name,'unit':item.unit} for item in order_items]
    else:
        order_items = [{'quantity':order.quantity,'price_per_unit':order.price_per_unit,
                        'total_amount':order.overall_amount,'product_name':'Paddy' if order.product_category_id == 2 else 'Rice'}]
    total_amount = order.overall_amount
    
    # Calculate balance due
    paid_amount = order.paid_amount or 0
    balance_due = total_amount - paid_amount
    
    # Determine payment status
    if paid_amount == 0:
        payment_status = 0  # Pending
    elif paid_amount < total_amount:
        payment_status = 1  # Partially Paid
    else:
        payment_status = 2  # Fully Paid
    
    # Calculate payment deadline date
    payment_deadline = order.order_date + timezone.timedelta(days=order.payment_deadline)
    
    context = {
        'order': order,
        'order_name': 'Paddy' if order.product_category_id == 2 else 'Rice' if order.product_category_id == 1 else 'Fertilizer',
        'order_items': order_items,
        'customer': order.customer,
        'total_amount': order.overall_amount,
        'payment_terms': order.payment_deadline,
        'balance_due': balance_due,
        'payment_status': payment_status,
        'invoice_date': order.order_date,
        'total_items': sum(item['quantity'] for item in order_items),
        'invoice_number': f"UFs {order.order_id}",
        'payment_terms': order.payment_deadline,
        'payment_deadline': payment_deadline,
        'amount_in_words': number_to_words_indian(order.overall_amount),
        'business_year': "urakadai "+str(order.order_date.year),
    }
    return render(request, 'payment_app/payment.html', context)

# Partial Payment Functions
@require_POST
@csrf_exempt
def create_partial_payment_order(request):
    """API endpoint to create a Razorpay order for partial payment"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        amount = float(data.get('amount'))
        
        # Get the order
        order = get_object_or_404(Orders, order_id=order_id)
        
        # Validate amount
        paid_amount = order.paid_amount or 0
        balance_due = order.overall_amount - paid_amount
        
        if amount <= 0 or amount > balance_due:
            return JsonResponse({
                'success': False, 
                'message': 'Invalid payment amount'
            })
        # Create Razorpay order (amount in paise)
        razorpay_amount = int(amount * 100)
        order_data = {
            'amount': razorpay_amount,
            'currency': 'INR',
            'receipt': f'receipt_{order_id}_{timezone.now().timestamp()}',
            'payment_capture': "1",  
            'notes': {
                'order_id': order_id
            }
        }
        
        razorpay_order = client.order.create(data=order_data)
        
        # Store order details in session
        request.session['partial_payment_order_id'] = razorpay_order['id']
        request.session['partial_payment_amount'] = amount
        request.session['partial_payment_for_order'] = order_id
        
        return JsonResponse({
            'success': True,
            'key_id': RAZORPAY_KEY_ID,
            'amount': razorpay_amount,
            'razorpay_order_id': razorpay_order['id']
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@require_POST
@csrf_exempt
def verify_partial_payment(request):
    """API endpoint to verify and process partial payment for customer orders"""
    try:
        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data provided.'}, status=400)
        
        # Extract payment data
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        application_order_id = data.get('order_id')
        amount_paid_this_transaction = data.get('amount')

        # Validate required fields
        if not razorpay_payment_id:
            return JsonResponse({'success': False, 'message': 'Missing razorpay_payment_id.'}, status=400)
        if not razorpay_order_id:
            return JsonResponse({'success': False, 'message': 'Missing razorpay_order_id.'}, status=400)
        if not razorpay_signature:
            return JsonResponse({'success': False, 'message': 'Missing razorpay_signature.'}, status=400)
        if not application_order_id:
            return JsonResponse({'success': False, 'message': 'Missing order_id.'}, status=400)
        if not amount_paid_this_transaction:
            return JsonResponse({'success': False, 'message': 'Missing payment amount.'}, status=400)

        # Convert amount to float
        try:
            amount_paid_this_transaction = float(amount_paid_this_transaction)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'Invalid payment amount format.'}, status=400)

        if amount_paid_this_transaction <= 0:
            return JsonResponse({'success': False, 'message': 'Payment amount must be greater than zero.'}, status=400)

        # Get the order
        try:
            order = Orders.objects.get(order_id=application_order_id)
        except Orders.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Order {application_order_id} not found.'}, status=404)

        # Validate payment amount against order balance
        current_paid_amount = order.paid_amount or 0
        balance_due = order.overall_amount - current_paid_amount
        
        if amount_paid_this_transaction > balance_due:
            return JsonResponse({
                'success': False, 
                'message': f'Payment amount (₹{amount_paid_this_transaction}) exceeds balance due (₹{balance_due}).'
            }, status=400)

        # Verify payment signature with Razorpay
        params_dict = {
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_signature': razorpay_signature
        }
        
        try:
            client.utility.verify_payment_signature(params_dict)
        except Exception as signature_error:
            return JsonResponse({
                'success': False, 
                'message': f'Payment signature verification failed: {str(signature_error)}'
            }, status=400)

        # Create Payment Record
        try:
            payment_record = Payments.objects.create(
                order=order,
                amount=amount_paid_this_transaction,
                date=timezone.now().date(),
                reference=f"partial_payment_{application_order_id}_{razorpay_payment_id[:10]}",
                proof_link=razorpay_payment_id,
                payment_method="Razorpay"
            )
        except Exception as payment_error:
            return JsonResponse({
                'success': False, 
                'message': f'Failed to create payment record: {str(payment_error)}'
            }, status=500)

        # Update Order paid_amount and payment_status
        try:
            new_paid_amount = current_paid_amount + amount_paid_this_transaction
            order.paid_amount = new_paid_amount
            
            # Update payment status based on new paid amount
            if new_paid_amount >= order.overall_amount:
                order.payment_status = 2  # Fully paid
                status_text = "fully paid"
            else:
                order.payment_status = 1  # Partially paid
                status_text = "partially paid"
            
            order.save()
            
            # Create notification for customer about payment
            create_notification(
                user_type='customer',
                user_id=order.customer.customer_id,
                notification_type='payment_received',
                title='Payment Received',
                message=f'Your payment of ₹{amount_paid_this_transaction} for order #{order.order_id} has been processed. Order is now {status_text}.',
                related_order_id=order.order_id
            )
            
        except Exception as order_update_error:
            return JsonResponse({
                'success': False, 
                'message': f'Failed to update order: {str(order_update_error)}'
            }, status=500)
        
        return JsonResponse({
            'success': True,
            'message': 'Payment verified and processed successfully',
            'new_balance': float(order.overall_amount - order.paid_amount),
            'payment_status': order.payment_status,
            'paid_amount': float(order.paid_amount),
            'total_amount': float(order.overall_amount)
        })
        
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({
            'success': False,
            'message': 'Payment signature verification failed. Invalid signature.'
        }, status=400)
    except Exception as e:
        # Log the error for debugging
        print(f"Error in verify_partial_payment: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}'
        }, status=500)

# Cash Payment Functions
@csrf_exempt
@require_POST
def request_cash_payment(request):
    """API endpoint to request cash payment approval"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        amount = float(data.get('amount'))
        customer_id = data.get('customer_id')
        reference = data.get('reference', '')
        notes = data.get('notes', '')
        
        # Get the order
        order = get_object_or_404(Orders, order_id=order_id)
        customer = get_object_or_404(CustomerTable, customer_id=customer_id)
        
        # Validate amount
        paid_amount = order.paid_amount or 0
        balance_due = order.overall_amount - paid_amount
        
        if amount <= 0 or amount > balance_due:
            return JsonResponse({
                'success': False, 
                'message': 'Invalid payment amount'
            })
            
        # Check if there's already a pending request
        existing_request = CashPaymentRequest.objects.filter(
            order=order,
            status=0  # Pending
        ).exists()
        
        if existing_request:
            return JsonResponse({
                'success': False,
                'message': 'There is already a pending cash payment request for this order.'
            })
        
        # Create the cash payment request
        cash_request = CashPaymentRequest.objects.create(
            order=order,
            customer=customer,
            amount=amount,
            reference=reference,
            notes=notes,
            status=0  # Pending
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Cash payment request submitted successfully',
            'request_id': cash_request.request_id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@role_required(["admin", "superadmin"])
def approve_cash_payment(request, request_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        cash_request = get_object_or_404(CashPaymentRequest, request_id=request_id)
        
        # Security check: Only allow admins to approve/reject their own orders
        if request.session.get('role') == 'admin':
            admin_id = request.session.get('user_id')
            if cash_request.order.admin_id != admin_id:
                return JsonResponse({
                    'success': False, 
                    'message': 'You can only process cash payment requests for your own orders.'
                })
        
        action = request.POST.get('action')
        
        if action not in ['approve', 'reject']:
            return JsonResponse({'success': False, 'message': 'Invalid action'})
        
        admin_id = request.session.get('user_id')
        admin = get_object_or_404(AdminTable, admin_id=admin_id)
        
        if action == 'approve':
            # Update request status
            cash_request.status = 1  # Approved
            cash_request.processed_at = timezone.now()
            cash_request.processed_by = admin
            cash_request.save()
            
            # Create payment record
            order = cash_request.order
            Payments.objects.create(
                order=order,
                amount=cash_request.amount,
                date=timezone.now().date(),
                reference=f"Cash Payment: {cash_request.reference}" if cash_request.reference else "Cash Payment",
                proof_link="Cash Payment Approved by Admin",
                payment_method="Cash"
            )
            
            # Update order payment status
            current_paid = order.paid_amount or 0
            order.paid_amount = current_paid + cash_request.amount
            
            if order.paid_amount >= order.overall_amount:
                order.payment_status = 2  # Fully paid
                payment_status_text = "fully paid"
            else:
                order.payment_status = 1  # Partially paid
                payment_status_text = "partially paid"
            
            order.save()
            
            # Create notification for customer
            create_notification(
                user_type='customer',
                user_id=cash_request.customer.customer_id,
                notification_type='payment_approved',
                title='Cash Payment Approved',
                message=f'Your cash payment of ₹{cash_request.amount} for order #{order.order_id} has been approved. Order is now {payment_status_text}.',
                related_order_id=order.order_id
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'Cash payment has been approved and recorded.'
            })
        else:  # reject
            # Update request status
            cash_request.status = 2  # Rejected
            cash_request.processed_at = timezone.now()
            cash_request.processed_by = admin
            cash_request.save()
            
            # Create notification for customer
            create_notification(
                user_type='customer',
                user_id=cash_request.customer.customer_id,
                notification_type='payment_rejected',
                title='Cash Payment Rejected',
                message=f'Your cash payment request of ₹{cash_request.amount} for order #{cash_request.order.order_id} has been rejected. Please contact support for more information.',
                related_order_id=cash_request.order.order_id
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'Cash payment request has been rejected.'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
# Subscription Payment Functions
def admin_subscription_payment(request):
    """Admin subscription payment page"""
    if request.method == "POST":
        # Check if it's a JSON request (AJAX)
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            # Handle AJAX request for creating Razorpay order
            try:
                data = json.loads(request.body)
                plan = data.get("plan")
            except:
                plan = request.POST.get("plan")
        else:
            plan = request.POST.get("plan")
        
        admin_id = request.session.get("user_id")

        if not admin_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login_app:login")

        amount = 100 if plan == "1month" else 200
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

        # If JSON request, return JSON response
        if 'application/json' in content_type:
            return JsonResponse({
                "order_id": razorpay_order["id"],
                "amount": amount * 100,
                "key_id": RAZORPAY_KEY_ID,
                "success_url": "/payment/admin-payment-success/",
                "redirect_url": "/admin-panel/admin-dashboard/"
            })

        return render(request, "payment_app/admin_subscription_payment.html", {
            "order_id": razorpay_order["id"],
            "amount": amount * 100,
            "key_id": RAZORPAY_KEY_ID
        })

    return render(request, "payment_app/admin_subscription_payment.html")

def customer_subscription_payment(request):
    """Customer subscription payment page"""
    if request.method == "POST":
        # Check if it's a JSON request (AJAX)
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            # Handle AJAX request for creating Razorpay order
            try:
                data = json.loads(request.body)
                plan = data.get("plan")
            except:
                plan = request.POST.get("plan")
        else:
            plan = request.POST.get("plan")
            
        customer_id = request.session.get("user_id")

        if not customer_id:
            messages.error(request, "Session expired. Please log in again.")
            return redirect("login_app:login")

        amount = 100 if plan == "1month" else 200
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

        # If JSON request, return JSON response
        if 'application/json' in content_type:
            return JsonResponse({
                "order_id": razorpay_order["id"],
                "amount": amount * 100,
                "key_id": RAZORPAY_KEY_ID,
                "success_url": "/payment/customer-payment-success/",
                "redirect_url": "/customer/customer-dashboard/"
            })

        return render(request, "payment_app/customer_subscription_payment.html", {
            "order_id": razorpay_order["id"],
            "amount": amount * 100,
            "key_id": RAZORPAY_KEY_ID
        })

    return render(request, "payment_app/customer_subscription_payment.html")

@csrf_exempt
def customer_payment_success(request):
    """
    Handles successful customer subscription payments.
    Assumes client-side has confirmed Razorpay success and sends details.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # IMPORTANT: Expecting razorpay_payment_id from the client's AJAX call
            razorpay_payment_id = data.get('razorpay_payment_id', 'N/A') 

            customer_id = request.session.get("user_id") # Assuming user_id is customer_id for this session
            amount = request.session.get("subscription_amount")
            days = request.session.get("subscription_days")
            # session_razorpay_order_id = request.session.get("razorpay_order_id") # Razorpay's order ID from session

            if not all([customer_id, amount, days]):
                return JsonResponse({"success": False, "message": "Session data missing or expired. Please log in again."})

            customer_instance = get_object_or_404(CustomerTable, customer_id=customer_id)
            
            # --- Create Payment Record ---
            try:
                Payments.objects.create(
                    order=None, # No direct order for subscriptions
                    amount=float(amount),
                    date=timezone.now().date(),
                    reference=f"cust_sub_{customer_id}_{razorpay_payment_id}",
                    proof_link=razorpay_payment_id,
                    payment_method="Razorpay"
                )
            except Exception as e:
                print(f"Error creating payment record for customer subscription {customer_id}: {e}")
                # Log and continue, or handle as critical error

            existing_subscription = Subscription.objects.filter(
                customer_id=customer_instance, # Use instance here
                subscription_type="customer"
            ).order_by("-end_date").first()

            if existing_subscription:
                start_date = existing_subscription.end_date + timedelta(days=1) if existing_subscription.end_date and existing_subscription.end_date >= now().date() else now().date()
                existing_subscription.start_date = start_date
                existing_subscription.end_date = start_date + timedelta(days=int(days)) - timedelta(days=1) # Inclusive end date
                existing_subscription.payment_amount += float(amount) # Ensure float for amount
                existing_subscription.subscription_status = 1 # Active
                existing_subscription.save()
                message_text = "Subscription extended successfully."
            else:
                Subscription.objects.create(
                    customer_id=customer_instance, # Use instance here
                    subscription_type="customer",
                    payment_amount=float(amount),
                    start_date=now().date(),
                    end_date=now().date() + timedelta(days=int(days)) - timedelta(days=1), # Inclusive end date
                    subscription_status=1 # Active
                )
                message_text = "Subscription created successfully."
            
            # Clear session variables for this subscription payment
            if "subscription_amount" in request.session: del request.session["subscription_amount"]
            if "subscription_days" in request.session: del request.session["subscription_days"]
            if "razorpay_order_id" in request.session: del request.session["razorpay_order_id"]
            # any other relevant session keys

            messages.success(request, message_text) # For next page load
            return JsonResponse({"success": True, "message": message_text})

        except CustomerTable.DoesNotExist:
            return JsonResponse({"success": False, "message": "Customer not found."})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"success": False, "message": f"Error processing customer subscription: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request. Expected POST method."})

@csrf_exempt
def payment_success(request):
    """
    Handles successful admin subscription payments.
    Assumes client-side has confirmed Razorpay success and sends details.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # IMPORTANT: Expecting razorpay_payment_id from the client's AJAX call
            razorpay_payment_id = data.get('razorpay_payment_id', 'N/A')

            admin_user_id = request.session.get("user_id") # Assuming user_id is admin_id for this session
            amount = request.session.get("subscription_amount")
            days = request.session.get("subscription_days")
            # session_razorpay_order_id = request.session.get("razorpay_order_id") # Razorpay's order ID from session


            if not all([admin_user_id, amount, days]):
                return JsonResponse({"success": False, "message": "Session data missing or expired. Please log in again."})

            admin_instance = get_object_or_404(AdminTable, admin_id=admin_user_id)

            # --- Create Payment Record ---
            try:
                Payments.objects.create(
                    order=None, # No direct order for subscriptions
                    amount=float(amount),
                    date=timezone.now().date(),
                    reference=f"admin_sub_{admin_user_id}_{razorpay_payment_id}",
                    proof_link=razorpay_payment_id,
                    payment_method="Razorpay", 
                )
            except Exception as e:
                print(f"Error creating payment record for admin subscription {admin_user_id}: {e}")
                # Log and continue, or handle as critical error

            existing_subscription = Subscription.objects.filter(
                admin_id=admin_instance, # Use instance here
                subscription_type="admin"
            ).order_by("-end_date").first()

            if existing_subscription:
                start_date = existing_subscription.end_date + timedelta(days=1) if existing_subscription.end_date and existing_subscription.end_date >= now().date() else now().date()
                existing_subscription.start_date = start_date
                existing_subscription.end_date = start_date + timedelta(days=int(days)) - timedelta(days=1) # Inclusive end date                existing_subscription.payment_amount += float(amount)
                existing_subscription.subscription_status = 1 # Active
                existing_subscription.save()
                message_text = "Subscription extended successfully."
                
                # Create notifications for subscription extension
                create_notification(
                    user_type='admin',
                    user_id=admin_user_id,
                    notification_type='subscription_payment',
                    title='Subscription Extended',
                    message=f'Your subscription has been extended successfully. Payment of ₹{amount} received.',
                    related_subscription_id=existing_subscription.sid
                )
                
                # Notification for superadmin
                create_notification(
                    user_type='superadmin',
                    user_id='1000000',  # Super admin ID
                    notification_type='admin_payment',
                    title='Admin Subscription Payment',
                    message=f'Admin {admin_instance.first_name} {admin_instance.last_name} made subscription payment of ₹{amount}',
                    related_subscription_id=existing_subscription.sid                )
            else:
                Subscription.objects.create(
                    admin_id=admin_instance, # Use instance here
                    subscription_type="admin",
                    payment_amount=float(amount),
                    start_date=now().date(),
                    end_date=now().date() + timedelta(days=int(days)) - timedelta(days=1), # Inclusive end date
                    subscription_status=1 # Active
                )
                message_text = "Subscription created successfully."
                
                # Create notifications for new subscription
                create_notification(
                    user_type='admin',
                    user_id=admin_user_id,
                    notification_type='subscription_payment',
                    title='Subscription Activated',
                    message=f'Your subscription has been activated successfully. Payment of ₹{amount} received.',
                )
                
                # Notification for superadmin
                create_notification(
                    user_type='superadmin',
                    user_id='1000000',  # Super admin ID
                    notification_type='admin_payment',
                    title='New Admin Subscription',
                    message=f'Admin {admin_instance.first_name} {admin_instance.last_name} activated subscription with payment of ₹{amount}',
                )

            # Clear session variables for this subscription payment
            if "subscription_amount" in request.session: del request.session["subscription_amount"]
            if "subscription_days" in request.session: del request.session["subscription_days"]
            if "razorpay_order_id" in request.session: del request.session["razorpay_order_id"]
            # any other relevant session keys

            messages.success(request, message_text) # For next page load
            return JsonResponse({"success": True, "message": message_text})

        except AdminTable.DoesNotExist:
            return JsonResponse({"success": False, "message": "Admin user not found."})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"success": False, "message": f"Error processing admin subscription: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request. Expected POST method."})


@require_POST
@csrf_exempt
def verify_admin_user_increase_payment(request):
    """
    Verifies the Razorpay payment signature and updates the subscription
    and admin's user count upon successful payment.
    Also creates a record in the Payments model.
    """
    try:
        data = json.loads(request.body)
        razorpay_payment_id = data.get('razorpay_payment_id')
        client_razorpay_order_id = data.get('razorpay_order_id') # Order ID from Razorpay's response
        razorpay_signature = data.get('razorpay_signature')

        # Retrieve details stored in session during order creation
        subscription_sid = request.session.get('user_increase_sub_id')
        expected_amount = request.session.get('user_increase_payment_amount')
        session_razorpay_order_id = request.session.get('user_increase_razorpay_order_id')

        if not all([subscription_sid, expected_amount, session_razorpay_order_id, razorpay_payment_id, client_razorpay_order_id, razorpay_signature]):
            return JsonResponse({'success': False, 'message': 'Payment verification failed: Essential data missing from session or request.'}, status=400)

        if client_razorpay_order_id != session_razorpay_order_id:
            return JsonResponse({'success': False, 'message': 'Payment verification failed: Order ID mismatch.'}, status=400)

        params_dict = {
            'razorpay_order_id': session_razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        # Verify the payment signature
        client.utility.verify_payment_signature(params_dict)

        # Optional: Fetch payment details from Razorpay for an additional check on amount and status
        # This adds an extra layer of security and confirms payment details with Razorpay directly.
        payment_details_from_razorpay = client.payment.fetch(razorpay_payment_id)
        if payment_details_from_razorpay['amount'] / 100 != expected_amount:
             return JsonResponse({'success': False, 'message': f'Payment verification failed: Amount mismatch. Expected {expected_amount}, paid {payment_details_from_razorpay["amount"] / 100}'}, status=400)
        if payment_details_from_razorpay['status'] != 'captured':
            # This case should ideally be handled by Razorpay's webhook if payment capture is delayed.
            # For immediate capture ('payment_capture': '1'), this check is a good safeguard.
            return JsonResponse({'success': False, 'message': 'Payment not successfully captured by Razorpay according to their API.'}, status=400)


        # If signature is verified and payment is captured, proceed to update your database
        subscription = get_object_or_404(UserIncreaseSubscription, sid=subscription_sid)
        
        if subscription.subscription_status != 1: # Ensure it was 'approved, pending payment' (status 1)
            # This prevents reprocessing or processing a non-payable subscription
            return JsonResponse({'success': False, 'message': 'Subscription is not in a payable state or has already been processed.'}, status=400)

        admin_user = get_object_or_404(AdminTable, admin_id=subscription.admin_id_id)

        # --- Create Payment Record ---
        try:
            Payments.objects.create(
                # 'order' field will be None as this is not tied to a product order
                # If your Payments model requires 'order', you might need to adjust the model
                # or create a different logging mechanism for subscription payments.
                order=None, 
                amount=expected_amount, # The actual amount paid for the subscription
                date=timezone.now().date(),
                reference=f"user_increase_sub_{subscription_sid}", # Custom reference
                proof_link=razorpay_payment_id, # Store Razorpay Payment ID as proof
                payment_method="Razorpay",
                # You might want to add a field to Payments model to link to AdminTable or CustomerTable directly
                # e.g., paid_by_admin=admin_user
            )
        except Exception as e:
            # Log this error, but don't necessarily fail the whole transaction if payment was successful
            # This depends on how critical the Payments record is for your immediate flow.
            print(f"Error creating payment record for admin subscription {subscription_sid}: {e}")
            # Don't show toast message here - status will be shown in content section
            pass


        # Update subscription status to 'Paid and Processed' (e.g., status 3)
        subscription.subscription_status = 3 # Assuming 3 means 'Paid and Processed'
        # You might want to add a field to UserIncreaseSubscription to store razorpay_payment_id
        # subscription.razorpay_payment_id = razorpay_payment_id 
        subscription.save()        # Increase admin's user count
        admin_user.user_count += 50 # Or whatever the agreed increase is
        admin_user.save()

        # Create notifications for user limit upgrade
        create_notification(
            user_type='admin',
            user_id=admin_user.admin_id,
            notification_type='subscription_upgrade',
            title='User Limit Increased',
            message=f'Your user limit has been successfully increased by 50. Payment of ₹{expected_amount} processed.',
            related_subscription_id=subscription_sid
        )

        # Notification for superadmin
        create_notification(
            user_type='superadmin',
            user_id='1000000',  # Super admin ID
            notification_type='subscription_upgrade',
            title='Admin User Limit Upgrade',
            message=f'Admin {admin_user.first_name} {admin_user.last_name} upgraded user limit by 50 users. Payment: ₹{expected_amount}',
            related_subscription_id=subscription_sid
        )

        # Clear the session variables used for this payment to prevent reuse
        if 'user_increase_sub_id' in request.session: del request.session['user_increase_sub_id']
        if 'user_increase_payment_amount' in request.session: del request.session['user_increase_payment_amount']
        if 'user_increase_razorpay_order_id' in request.session: del request.session['user_increase_razorpay_order_id']
        
        # Don't show toast message here - status will be shown in content section when page reloads
        return JsonResponse({'success': True, 'message': 'Payment successful and subscription updated.'})

    except razorpay.errors.SignatureVerificationError:
        # Log this error
        print(f"Razorpay Signature Verification Error for order {session_razorpay_order_id if 'session_razorpay_order_id' in locals() else 'UNKNOWN'}")
        return JsonResponse({'success': False, 'message': 'Payment verification failed: Invalid signature.'}, status=400)
    except UserIncreaseSubscription.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Subscription record not found during verification.'}, status=404)
    except AdminTable.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Admin record not found during verification.'}, status=404)
    except Exception as e:
        print(f"Error in verify_admin_user_increase_payment: {e}") # Log the error for debugging
        # Include more context in error logging if possible, like session_razorpay_order_id
        return JsonResponse({'success': False, 'message': f'An error occurred during payment verification: {str(e)}'}, status=500)


@require_POST
@role_required(["admin"])
def create_admin_user_increase_order(request):
    """
    Creates a Razorpay order for an admin's user count increase subscription.
    This is called via AJAX when the admin clicks the "Pay Now" button.
    """
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return JsonResponse({'success': False, 'message': 'User not authenticated.'}, status=401)

        admin = get_object_or_404(AdminTable, admin_id=user_id)
        # Find an approved subscription (status 1) for this admin that needs payment
        subscription = UserIncreaseSubscription.objects.filter(admin_id=admin, subscription_status=1).order_by('-sid').first()

        if not subscription:
            return JsonResponse({'success': False, 'message': 'No approved subscription upgrade found pending payment.'}, status=404)

        if not subscription.payment_amount or subscription.payment_amount <= 0:
            return JsonResponse({'success': False, 'message': 'Payment amount has not been set for this subscription by the superadmin.'}, status=400)

        amount_in_paise = int(subscription.payment_amount * 100)

        razorpay_order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': f'admin_increase_sub_{subscription.sid}_{timezone.now().timestamp()}',
            'payment_capture': '1', # Auto capture payment
            'notes': {
                'subscription_id': subscription.sid,
                'admin_id': user_id,
                'purpose': 'Admin User Count Increase Subscription'
            }
        }
        razorpay_order = client.order.create(data=razorpay_order_data)

        # Store necessary details in session for the verification step
        request.session['user_increase_sub_id'] = subscription.sid  # Store actual subscription ID
        request.session['user_increase_payment_amount'] = float(subscription.payment_amount)
        request.session['user_increase_razorpay_order_id'] = razorpay_order['id']

        return JsonResponse({
            'success': True,
            'key_id': RAZORPAY_KEY_ID,
            'amount': amount_in_paise, # This is what Razorpay checkout will use
            'razorpay_order_id': razorpay_order['id'],
            # Prefill data for Razorpay form
            'admin_name': f"{admin.first_name} {admin.last_name}",
            'admin_email': admin.email,
            'admin_phone': admin.phone_number
        })

    except AdminTable.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Admin user not found.'}, status=404)
    except UserIncreaseSubscription.DoesNotExist: # Should not happen if logic is correct, but good to have
        return JsonResponse({'success': False, 'message': 'Subscription record not found.'}, status=404)
    except Exception as e:
        print(f"Error in create_admin_user_increase_order: {e}") # Log the error for debugging
        return JsonResponse({'success': False, 'message': f'An error occurred while creating payment order: {str(e)}'}, status=500)

# Order Booking Fee Payment - COMMENTED OUT (No payment required for placing orders)
@role_required(["admin", "superadmin"])
def order_booking_payment(request):
    """Handle order booking fee payment (₹10) - DISABLED"""
    # Booking fee payment is no longer required
    # Orders can be placed directly without payment
    
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    
    if not user_id or role not in ["admin", "superadmin"]:
        return redirect('login_app:login')
    
    # Redirect directly to orders page since no payment is required
    messages.info(request, "Order booking fee has been waived. Orders can be placed directly.")
    
    if role == "superadmin":
        return redirect('orders_app:super_admin_orders')
    else:
        return redirect('orders_app:admin_orders')
    
    # COMMENTED OUT - Original payment logic
    """
    if request.method == "POST":
        # Handle payment verification
        if request.POST.get("razorpay_payment_id"):
            payment_id = request.POST.get("razorpay_payment_id")
            order_id = request.POST.get("razorpay_order_id")
            signature = request.POST.get("razorpay_signature")
            
            try:
                # Verify payment signature
                client.utility.verify_payment_signature({
                    'razorpay_order_id': order_id,
                    'razorpay_payment_id': payment_id,
                    'razorpay_signature': signature
                })
                
                # Create payment record for booking fee
                Payments.objects.create(
                    order=None,  # Booking fee is not tied to specific order
                    amount=10,
                    date=timezone.now().date(),
                    reference=payment_id,
                    proof_link=payment_id,
                    payment_method="Razorpay"
                )
                
                messages.success(request, "Booking fee payment successful!")
                
                # Get pending order ID from session if it exists
                pending_order_id = request.session.get('pending_order_id')
                if pending_order_id:
                    # Clear the session
                    del request.session['pending_order_id']
                
                # Redirect based on role to orders page
                if role == "superadmin":
                    return redirect('orders_app:super_admin_orders')
                else:
                    return redirect('orders_app:admin_orders')
                    
            except Exception as e:
                messages.error(request, f"Payment verification failed: {str(e)}")
                
        # Handle AJAX request to create Razorpay order
        elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                razorpay_order = client.order.create({
                    "amount": 1000,  # ₹10 in paise
                    "currency": "INR",
                    "payment_capture": 1,
                    "notes": {
                        "purpose": "Order booking fee",
                        "user_id": str(user_id),
                        "role": role
                    }
                })
                
                return JsonResponse({
                    "status": "success",
                    "razorpay_key": RAZORPAY_KEY_ID,
                    "order_id": razorpay_order["id"],
                    "amount": 10
                })
                
            except Exception as e:
                return JsonResponse({
                    "status": "error",
                    "message": f"Error creating payment: {str(e)}"
                })
    
    # Render payment page
    context = {
        'amount': 10,
        'purpose': 'Order Booking Fee',
        'description': 'One-time booking fee for placing orders',
        'user_role': role
    }
    return render(request, 'payment_app/booking_payment.html', context)
    """

# Debug endpoint for payment verification issues
@csrf_exempt
def debug_payment_verification(request):
    """Debug endpoint to check payment verification data"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            debug_info = {
                'received_data': {
                    'razorpay_payment_id': data.get('razorpay_payment_id'),
                    'razorpay_order_id': data.get('razorpay_order_id'),
                    'razorpay_signature': data.get('razorpay_signature'),
                    'order_id': data.get('order_id'),
                    'amount': data.get('amount'),
                },
                'razorpay_config': {
                    'key_id_exists': bool(RAZORPAY_KEY_ID),
                    'secret_exists': bool(RAZORPAY_SECRET),
                    'client_initialized': bool(client),
                }
            }
            
            # Check if order exists
            try:
                order_id = data.get('order_id')
                if order_id:
                    order = Orders.objects.get(order_id=order_id)
                    debug_info['order_info'] = {
                        'exists': True,
                        'order_id': order.order_id,
                        'overall_amount': float(order.overall_amount),
                        'paid_amount': float(order.paid_amount or 0),
                        'balance_due': float(order.overall_amount - (order.paid_amount or 0)),
                        'payment_status': order.payment_status,
                    }
                else:
                    debug_info['order_info'] = {'exists': False, 'error': 'No order_id provided'}
            except Orders.DoesNotExist:
                debug_info['order_info'] = {'exists': False, 'error': f'Order {order_id} not found'}
            except Exception as e:
                debug_info['order_info'] = {'exists': False, 'error': str(e)}
            
            return JsonResponse({
                'success': True,
                'debug_info': debug_info
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'raw_body': request.body.decode('utf-8') if request.body else 'No body'
            })
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)
