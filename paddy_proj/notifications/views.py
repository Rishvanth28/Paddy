from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from paddy_app.decorators import role_required
from paddy_app.models import Notification
from paddy_app.helpers import get_user_notifications, get_unread_notification_count, mark_notification_as_read
import json


@role_required(["customer"])
def customer_notifications(request):
    """Display notifications for customer"""
    customer_id = request.session.get("user_id")
    if not customer_id:
        return redirect('login')
    
    notifications = get_user_notifications('customer', customer_id)
    unread_count = get_unread_notification_count('customer', customer_id)
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    return render(request, 'customer_notifications.html', context)


@role_required(["admin"])
def admin_notifications(request):
    """Display notifications for admin"""
    admin_id = request.session.get("user_id")
    if not admin_id:
        return redirect('login')
    
    notifications = get_user_notifications('admin', admin_id)
    unread_count = get_unread_notification_count('admin', admin_id)
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    return render(request, 'admin_notifications.html', context)


@role_required(["superadmin"])
def superadmin_notifications(request):
    """Display notifications for superadmin"""
    admin_id = request.session.get("user_id")
    
    # Get all admin payment and subscription notifications
    notifications = Notification.objects.filter(
        Q(user_type='admin', notification_type__in=['subscription_payment', 'subscription_upgrade', 'admin_payment']) |
        Q(user_type='superadmin', user_id=str(admin_id))
    ).order_by('-created_at')[:50]
    
    unread_count = Notification.objects.filter(
        Q(user_type='admin', notification_type__in=['subscription_payment', 'subscription_upgrade', 'admin_payment']) |
        Q(user_type='superadmin', user_id=str(admin_id)),
        is_read=False
    ).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    return render(request, 'superadmin_notifications.html', context)


@require_POST
def mark_notification_read(request):
    """Mark a notification as read via AJAX"""
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        if mark_notification_as_read(notification_id):
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'Notification not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read for current user"""
    try:
        user_id = request.session.get("user_id")
        role = request.session.get("role")
        
        if not user_id or not role:
            return JsonResponse({'success': False, 'message': 'Session expired'})
        
        # For superadmin, mark both admin notifications and their own notifications as read
        if role == 'superadmin':
            Notification.objects.filter(
                Q(user_type='admin', notification_type__in=['subscription_payment', 'subscription_upgrade', 'admin_payment']) |
                Q(user_type='superadmin', user_id=str(user_id)),
                is_read=False
            ).update(is_read=True)
        else:
            # For other users, only mark their own notifications as read
            user_type = role
            Notification.objects.filter(
                user_type=user_type,
                user_id=str(user_id),
                is_read=False
            ).update(is_read=True)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
def delete_notifications(request):
    """Delete selected notifications for current user"""
    try:
        # Parse request data
        data = json.loads(request.body)
        notification_ids = data.get('notification_ids', [])
        
        # Validate session
        user_id = request.session.get("user_id")
        role = request.session.get("role")
        
        if not user_id or not role:
            return JsonResponse({'success': False, 'error': 'Session expired. Please login again.'})
        
        # Additional role validation for security
        if role not in ['admin', 'customer', 'superadmin']:
            return JsonResponse({'success': False, 'error': 'Invalid user role'})
        
        if not notification_ids:
            return JsonResponse({'success': False, 'error': 'No notifications selected'})
        
        # Validate notification IDs
        if not isinstance(notification_ids, list):
            return JsonResponse({'success': False, 'error': 'Invalid notification IDs format'})
        
        # Convert string IDs to integers
        try:
            notification_ids = [int(id) for id in notification_ids]
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid notification ID format'})
        
        # For superadmin, allow deleting both admin notifications and their own notifications
        if role == 'superadmin':
            deleted_count = Notification.objects.filter(
                notification_id__in=notification_ids
            ).filter(
                Q(user_type='admin', notification_type__in=['subscription_payment', 'subscription_upgrade', 'admin_payment']) |
                Q(user_type='superadmin', user_id=str(user_id))
            ).delete()[0]
        else:
            # For other users, only delete their own notifications
            user_type = role
            deleted_count = Notification.objects.filter(
                notification_id__in=notification_ids,
                user_type=user_type,
                user_id=str(user_id)
            ).delete()[0]
        
        if deleted_count > 0:
            return JsonResponse({
                'success': True, 
                'message': f'{deleted_count} notification(s) deleted successfully',
                'deleted_count': deleted_count
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': 'No matching notifications found or unauthorized access'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})
