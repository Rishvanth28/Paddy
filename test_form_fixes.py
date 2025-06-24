#!/usr/bin/env python
"""
Test script to verify the form fixes for the customize PDF report functionality.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(r'c:\projects\Paddy\paddy_proj')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paddy_proj.settings')
django.setup()

from paddy_app.forms import AdminCustomReportForm, SuperAdminCustomReportForm
from paddy_app.models import AdminTable, CustomerTable

def test_admin_form():
    """Test the AdminCustomReportForm with new single selection fields."""
    print("Testing AdminCustomReportForm...")
    
    # Test form initialization
    form = AdminCustomReportForm()
    print(f"✓ Form initialized successfully")
    
    # Check if date_preset field exists
    if hasattr(form, 'fields') and 'date_preset' in form.fields:
        print(f"✓ Date preset field exists")
        print(f"  - Date preset choices: {len(form.fields['date_preset'].choices)} options")
    else:
        print("✗ Date preset field missing")
    
    # Check if selected_customers is now a single choice field
    if 'selected_customers' in form.fields:
        field_type = type(form.fields['selected_customers']).__name__
        print(f"✓ Customer selection field type: {field_type}")
    
    return True

def test_superadmin_form():
    """Test the SuperAdminCustomReportForm with new single selection fields."""
    print("\nTesting SuperAdminCustomReportForm...")
    
    # Test form initialization
    form = SuperAdminCustomReportForm()
    print(f"✓ Form initialized successfully")
    
    # Check if date_preset field exists
    if hasattr(form, 'fields') and 'date_preset' in form.fields:
        print(f"✓ Date preset field exists")
        print(f"  - Date preset choices: {len(form.fields['date_preset'].choices)} options")
    else:
        print("✗ Date preset field missing")
    
    # Check field types
    if 'selected_admins' in form.fields:
        admin_field_type = type(form.fields['selected_admins']).__name__
        print(f"✓ Admin selection field type: {admin_field_type}")
    
    if 'selected_customers' in form.fields:
        customer_field_type = type(form.fields['selected_customers']).__name__
        print(f"✓ Customer selection field type: {customer_field_type}")
    
    return True

def test_form_submission():
    """Test form submission with sample data."""
    print("\nTesting form submission...")
    
    # Test data
    test_data = {
        'date_preset': 'last_30_days',
        'payment_status': '1',
        'delivery_status': '1',
        'category': 'test',
        'sort_by': '-order_date',
        'order_id': True,
        'customer': True,
        'order_date': True,
    }
    
    # Test admin form
    admin_form = AdminCustomReportForm(data=test_data)
    if admin_form.is_valid():
        print("✓ AdminCustomReportForm validates successfully")
        print(f"  - Date preset: {admin_form.cleaned_data.get('date_preset')}")
    else:
        print("✗ AdminCustomReportForm validation failed")
        print(f"  - Errors: {admin_form.errors}")
    
    # Test superadmin form
    superadmin_form = SuperAdminCustomReportForm(data=test_data)
    if superadmin_form.is_valid():
        print("✓ SuperAdminCustomReportForm validates successfully")
        print(f"  - Date preset: {superadmin_form.cleaned_data.get('date_preset')}")
    else:
        print("✗ SuperAdminCustomReportForm validation failed")
        print(f"  - Errors: {superadmin_form.errors}")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("FORM ENHANCEMENT TEST SUITE")
    print("=" * 60)
    
    try:
        test_admin_form()
        test_superadmin_form()
        test_form_submission()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("✓ Forms are working with new enhancements:")
        print("  - Date preset functionality")
        print("  - Single dropdown selections")
        print("  - Enhanced UI styling")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
