import os
import json
import re
import razorpay
from datetime import datetime
from .models import Notification

def number_to_words_indian(num):
    """Convert a number to words using the Indian numbering system (lakhs, crores)"""
    
    # Define word representations
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 
            'Seventeen', 'Eighteen', 'Nineteen']
    
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    # Handle zero separately
    if num == 0:
        return "Zero"
    
    # Convert to string for easier manipulation
    num_str = str(num)
    
    # Function to convert a number less than 1000 to words
    def convert_less_than_thousand(n):
        if n == 0:
            return ""
        
        if n < 20:
            return ones[n]
        
        if n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
        
        return ones[n // 100] + " Hundred" + (" " + convert_less_than_thousand(n % 100) if n % 100 != 0 else "")
    
    # For Indian system
    words = []
    
    # Handle crores (1,00,00,000 and above)
    if len(num_str) > 7:
        crores = int(num_str[:-7])
        words.append(convert_less_than_thousand(crores) + " Crore")
        num_str = num_str[-7:]
    
    # Handle lakhs (1,00,000 to 99,99,999)
    if len(num_str) > 5:
        lakhs = int(num_str[:-5])
        if lakhs > 0:
            words.append(convert_less_than_thousand(lakhs) + " Lakh")
        num_str = num_str[-5:]
    
    # Handle thousands (1,000 to 99,999)
    if len(num_str) > 3:
        thousands = int(num_str[:-3])
        if thousands > 0:
            words.append(convert_less_than_thousand(thousands) + " Thousand")
        num_str = num_str[-3:]
    
    # Handle last three digits (hundreds, tens, ones)
    if int(num_str) > 0:
        words.append(convert_less_than_thousand(int(num_str)))
    
    return " ".join(words) + " Rupees Only"


def create_notification(user_type, user_id, notification_type, title, message, 
                       related_order_id=None, related_payment_id=None, related_subscription_id=None):
    """
    Create a notification for a user
    
    Args:
        user_type: 'customer', 'admin', or 'superadmin'
        user_id: The ID of the user (customer_id or admin_id)
        notification_type: Type of notification from NOTIFICATION_TYPES
        title: Notification title
        message: Notification message
        related_order_id: Optional order ID reference
        related_payment_id: Optional payment ID reference
        related_subscription_id: Optional subscription ID reference
    """
    try:
        notification = Notification.objects.create(
            user_type=user_type,
            user_id=str(user_id),
            notification_type=notification_type,
            title=title,
            message=message,
            related_order_id=related_order_id,
            related_payment_id=related_payment_id,
            related_subscription_id=related_subscription_id
        )
        return notification
    except Exception as e:
        print(f"Error creating notification: {e}")
        return None


def get_user_notifications(user_type, user_id, limit=50):
    """
    Get notifications for a specific user
    
    Args:
        user_type: 'customer', 'admin', or 'superadmin'
        user_id: The ID of the user
        limit: Maximum number of notifications to return
    """
    return Notification.objects.filter(
        user_type=user_type,
        user_id=str(user_id)
    ).order_by('-created_at')[:limit]


def mark_notification_as_read(notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(notification_id=notification_id)
        notification.is_read = True
        notification.save()
        return True
    except Notification.DoesNotExist:
        return False


def get_unread_notification_count(user_type, user_id):
    """Get count of unread notifications for a user"""
    return Notification.objects.filter(
        user_type=user_type,
        user_id=str(user_id),
        is_read=False
    ).count()


def validate_gst(gst):
    """Validate GST number format"""
    gst_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(gst_pattern, gst))

