from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .decorators import role_required
from .models import Orders, CustomerTable, Payments, AdminTable, OrderItems
import pandas as pd
import io
from datetime import datetime, timedelta
from django.db.models import Q
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
import csv
import xlsxwriter

def get_admin_report_data(request):
    """Get filtered report data for admin users"""
    # Get admin ID from session
    admin_id = request.session.get("user_id")
    
    # Get filter parameters
    customer_id = request.GET.get('customer', '')
    order_status = request.GET.get('order_status', '')
    payment_status = request.GET.get('payment_status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    date_preset = request.GET.get('date_preset', '')
    product_type = request.GET.get('product_type', '')  # New filter for product type
    sort_field = request.GET.get('sort', '')
    sort_dir = request.GET.get('dir', 'asc')
    
    # Handle date presets
    if date_preset:
        today = datetime.now().date()
        end_date = today.strftime('%Y-%m-%d')
        
        if date_preset == 'today':
            start_date = today.strftime('%Y-%m-%d')
        elif date_preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            start_date = yesterday.strftime('%Y-%m-%d')
            end_date = yesterday.strftime('%Y-%m-%d')
        elif date_preset == 'last_7_days':
            start_date = (today - timedelta(days=6)).strftime('%Y-%m-%d')
        elif date_preset == 'last_30_days':
            start_date = (today - timedelta(days=29)).strftime('%Y-%m-%d')
        elif date_preset == 'last_3_months':
            start_date = (today.replace(month=today.month-3 if today.month > 3 else today.month+9, 
                                        year=today.year if today.month > 3 else today.year-1)
                        ).strftime('%Y-%m-%d')
        elif date_preset == 'last_6_months':
            start_date = (today.replace(month=today.month-6 if today.month > 6 else today.month+6, 
                                        year=today.year if today.month > 6 else today.year-1)
                        ).strftime('%Y-%m-%d')
        elif date_preset == 'last_year':
            start_date = (today.replace(year=today.year-1)).strftime('%Y-%m-%d')
    
    # Start with all orders for admin
    orders = Orders.objects.filter(admin_id=admin_id)
    
    # Apply filters
    if customer_id:
        orders = orders.filter(customer_id=customer_id)
    
    if order_status:
        orders = orders.filter(delivery_status=order_status)
    
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    
    # Filter by product type (rice, paddy, pesticide)
    if product_type:
        orders = orders.filter(product_category_id=product_type)
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            orders = orders.filter(created_at__gte=start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            # Add a day to include the end date fully
            end_date = end_date + timedelta(days=1)
            orders = orders.filter(created_at__lte=end_date)
        except ValueError:
            pass
    
    # Apply sorting if specified
    if sort_field and sort_field in ['order_id', 'order_date', 'overall_amount', 'payment_status', 'delivery_status', 'product_category_id', 'quantity']:
        print(f"DEBUG: Applying sort - field: {sort_field}, direction: {sort_dir}")
        if sort_dir == 'desc':
            orders = orders.order_by(f'-{sort_field}')
        else:
            orders = orders.order_by(sort_field)
    else:
        print(f"DEBUG: Using default sort by order_id desc")
        # Default sorting by order_id
        orders = orders.order_by('-order_id')
    
    return orders

def get_superadmin_report_data(request):
    """Get filtered report data for superadmin users"""
    # Get filter parameters
    admin_id = request.GET.get('admin', '')
    customer_id = request.GET.get('customer', '')
    order_status = request.GET.get('order_status', '')
    payment_status = request.GET.get('payment_status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    date_preset = request.GET.get('date_preset', '')
    product_type = request.GET.get('product_type', '')  # New filter for product type
    sort_field = request.GET.get('sort', '')
    sort_dir = request.GET.get('dir', 'asc')
    
    # Handle date presets
    if date_preset:
        today = datetime.now().date()
        end_date = today.strftime('%Y-%m-%d')
        
        if date_preset == 'today':
            start_date = today.strftime('%Y-%m-%d')
        elif date_preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            start_date = yesterday.strftime('%Y-%m-%d')
            end_date = yesterday.strftime('%Y-%m-%d')
        elif date_preset == 'last_7_days':
            start_date = (today - timedelta(days=6)).strftime('%Y-%m-%d')
        elif date_preset == 'last_30_days':
            start_date = (today - timedelta(days=29)).strftime('%Y-%m-%d')
        elif date_preset == 'last_3_months':
            start_date = (today.replace(month=today.month-3 if today.month > 3 else today.month+9, 
                                        year=today.year if today.month > 3 else today.year-1)
                        ).strftime('%Y-%m-%d')
        elif date_preset == 'last_6_months':
            start_date = (today.replace(month=today.month-6 if today.month > 6 else today.month+6, 
                                        year=today.year if today.month > 6 else today.year-1)
                        ).strftime('%Y-%m-%d')
        elif date_preset == 'last_year':
            start_date = (today.replace(year=today.year-1)).strftime('%Y-%m-%d')
    
    # Start with all orders
    orders = Orders.objects.all()
    
    # Apply filters
    if admin_id:
        orders = orders.filter(admin_id=admin_id)
        
    if customer_id:
        orders = orders.filter(customer_id=customer_id)
    
    if order_status:
        orders = orders.filter(delivery_status=order_status)
    
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    
    # Filter by product type (rice, paddy, pesticide)
    if product_type:
        orders = orders.filter(product_category_id=product_type)
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            orders = orders.filter(created_at__gte=start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            # Add a day to include the end date fully
            end_date = end_date + timedelta(days=1)
            orders = orders.filter(created_at__lte=end_date)
        except ValueError:
            pass
    
    # Apply sorting if specified
    if sort_field and sort_field in ['order_id', 'order_date', 'overall_amount', 'payment_status', 'delivery_status', 'product_category_id', 'quantity']:
        print(f"DEBUG: Superadmin applying sort - field: {sort_field}, direction: {sort_dir}")
        if sort_dir == 'desc':
            orders = orders.order_by(f'-{sort_field}')
        else:
            orders = orders.order_by(sort_field)
    else:
        print(f"DEBUG: Superadmin using default sort by order_id desc")
        # Default sorting by order_id
        orders = orders.order_by('-order_id')
    
    return orders

def generate_excel(rice_paddy_data, pesticide_data, filename="report.xlsx", is_superadmin=False):
    """Generate Excel file from report data with separate sheets for rice/paddy and pesticide orders"""
    # Create an in-memory output file
    output = io.BytesIO()
    
    # Create Excel writer using XlsxWriter as the engine
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Get the workbook
    workbook = writer.book
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#0047AB',  # Dark blue
        'font_color': 'white',
        'border': 1,
        'align': 'center'
    })
    
    # Number format for amounts
    amount_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
    
    # Date format
    date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center'})
    
    # Quantity format (center-aligned with no decimals)
    quantity_format = workbook.add_format({'num_format': '#,##0', 'align': 'center'})
    
    # Product type format (center-aligned)
    product_format = workbook.add_format({'align': 'center'})
    
    # Status formats
    delivered_format = workbook.add_format({'font_color': 'green', 'align': 'center'})
    pending_format = workbook.add_format({'font_color': 'orange', 'align': 'center'})
    paid_format = workbook.add_format({'font_color': 'green', 'align': 'center'})
    not_paid_format = workbook.add_format({'font_color': 'red', 'align': 'center'})
    
    # Process Rice/Paddy Orders
    if rice_paddy_data:
        # Create a pandas DataFrame
        df = pd.DataFrame(rice_paddy_data)
        
        # Reorder columns to match the requested order
        ordered_columns = []
        if is_superadmin:
            # For superadmin reports (with admin column)
            ordered_columns = ['id', 'admin_name', 'customer_name', 'order_date', 'product_type', 'quantity', 
                              'total_amount', 'pending_amount', 'status', 'payment_status']
        else:
            # For admin reports (without admin column)
            ordered_columns = ['id', 'customer_name', 'order_date', 'product_type', 'quantity', 
                              'total_amount', 'pending_amount', 'status', 'payment_status']
        
        # Ensure all columns in ordered_columns exist in df
        ordered_columns = [col for col in ordered_columns if col in df.columns]
        
        # Reorder the DataFrame
        df = df[ordered_columns]
        
        # Rename columns to more readable format
        renamed_columns = {}
        for col in df.columns:
            if col == 'id':
                renamed_columns[col] = 'Order ID'
            elif col == 'admin_name':
                renamed_columns[col] = 'Admin'
            elif col == 'customer_name':
                renamed_columns[col] = 'Customer'
            elif col == 'order_date':
                renamed_columns[col] = 'Order Date'
            elif col == 'status':
                renamed_columns[col] = 'Delivery Status'
            elif col == 'payment_status':
                renamed_columns[col] = 'Payment Status'
            elif col == 'total_amount':
                renamed_columns[col] = 'Total Amount'
            elif col == 'pending_amount':
                renamed_columns[col] = 'Pending Amount'
            elif col == 'product_type':
                renamed_columns[col] = 'Product Type'
            elif col == 'quantity':
                renamed_columns[col] = 'Quantity'
            else:
                # Convert snake_case to Title Case
                renamed_columns[col] = ' '.join(word.title() for word in col.split('_'))
        
        df = df.rename(columns=renamed_columns)
        
        # Convert the DataFrame to an XlsxWriter Excel object
        df.to_excel(writer, sheet_name='Rice and Paddy Orders', index=False)
        
        # Get the worksheet object
        worksheet = writer.sheets['Rice and Paddy Orders']
        
        # Write the column headers with the defined format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Set column widths based on content
        if is_superadmin:
            worksheet.set_column('A:A', 10)  # Order ID
            worksheet.set_column('B:C', 25)  # Admin, Customer
            worksheet.set_column('D:D', 15)  # Order Date
            worksheet.set_column('E:E', 15)  # Product Type
            worksheet.set_column('F:F', 10)  # Quantity
            worksheet.set_column('G:H', 15)  # Total Amount, Pending Amount
            worksheet.set_column('I:J', 15)  # Delivery Status, Payment Status
        else:
            worksheet.set_column('A:A', 10)  # Order ID
            worksheet.set_column('B:B', 25)  # Customer
            worksheet.set_column('C:C', 15)  # Order Date
            worksheet.set_column('D:D', 15)  # Product Type
            worksheet.set_column('E:E', 10)  # Quantity
            worksheet.set_column('F:G', 15)  # Total Amount, Pending Amount
            worksheet.set_column('H:I', 15)  # Delivery Status, Payment Status
        
        # Apply conditional formatting for status columns
        status_col = None
        payment_col = None
        amount_cols = []
        product_col = None
        quantity_col = None
        
        for col_num, col_name in enumerate(df.columns):
            if col_name == 'Delivery Status':
                status_col = col_num
            elif col_name == 'Payment Status':
                payment_col = col_num
            elif 'Amount' in col_name:
                amount_cols.append(col_num)
            elif col_name == 'Product Type':
                product_col = col_num
            elif col_name == 'Quantity':
                quantity_col = col_num
        
        # Apply formatting to each row
        for row_num in range(1, len(df) + 1):
            # Apply amount formatting
            for col in amount_cols:
                worksheet.write(row_num, col, df.iloc[row_num-1, col], amount_format)
            
            # Apply product type formatting
            if product_col is not None:
                worksheet.write(row_num, product_col, df.iloc[row_num-1, product_col], product_format)
                
            # Apply quantity formatting
            if quantity_col is not None:
                worksheet.write(row_num, quantity_col, df.iloc[row_num-1, quantity_col], quantity_format)
            
            # Apply status formatting
            if status_col is not None:
                status_value = df.iloc[row_num-1, status_col]
                if status_value == 'Delivered':
                    worksheet.write(row_num, status_col, status_value, delivered_format)
                elif status_value == 'Pending':
                    worksheet.write(row_num, status_col, status_value, pending_format)
            
            # Apply payment status formatting
            if payment_col is not None:
                payment_value = df.iloc[row_num-1, payment_col]
                if payment_value == 'Paid':
                    worksheet.write(row_num, payment_col, payment_value, paid_format)
                elif payment_value == 'Not Paid':
                    worksheet.write(row_num, payment_col, payment_value, not_paid_format)
        
        # Add summary at the bottom
        total_rows = len(df) + 3  # Start 2 rows after the data
        
        worksheet.write(total_rows, 0, 'Summary:', workbook.add_format({'bold': True}))
        worksheet.write(total_rows + 1, 0, 'Total Orders:')
        worksheet.write(total_rows + 1, 1, len(df))
        
        # Calculate totals if amount columns exist
        if 'Total Amount' in df.columns and 'Pending Amount' in df.columns:
            total_amount = df['Total Amount'].sum()
            pending_amount = df['Pending Amount'].sum()
            paid_amount = total_amount - pending_amount
            
            worksheet.write(total_rows + 2, 0, 'Total Amount:')
            worksheet.write(total_rows + 2, 1, total_amount, amount_format)
            
            worksheet.write(total_rows + 3, 0, 'Paid Amount:')
            worksheet.write(total_rows + 3, 1, paid_amount, amount_format)
            
            worksheet.write(total_rows + 4, 0, 'Pending Amount:')
            worksheet.write(total_rows + 4, 1, pending_amount, amount_format)
    
    # Process Pesticide Orders
    if pesticide_data:
        # Create a pandas DataFrame
        df = pd.DataFrame(pesticide_data)
        
        # Reorder columns to match the requested order
        ordered_columns = []
        if is_superadmin:
            # For superadmin reports (with admin column)
            ordered_columns = ['id', 'admin_name', 'customer_name', 'order_date', 
                             'product_name', 'batch_number', 'expiry_date', 'item_quantity', 'unit',
                             'price_per_unit', 'item_total', 'status', 'payment_status']
        else:
            # For admin reports (without admin column)
            ordered_columns = ['id', 'customer_name', 'order_date', 
                             'product_name', 'batch_number', 'expiry_date', 'item_quantity', 'unit',
                             'price_per_unit', 'item_total', 'status', 'payment_status']
        
        # Ensure all columns in ordered_columns exist in df
        ordered_columns = [col for col in ordered_columns if col in df.columns]
        
        # Reorder the DataFrame
        df = df[ordered_columns]
        
        # Rename columns to more readable format
        renamed_columns = {}
        for col in df.columns:
            if col == 'id':
                renamed_columns[col] = 'Order ID'
            elif col == 'admin_name':
                renamed_columns[col] = 'Admin'
            elif col == 'customer_name':
                renamed_columns[col] = 'Customer'
            elif col == 'order_date':
                renamed_columns[col] = 'Order Date'
            elif col == 'status':
                renamed_columns[col] = 'Delivery Status'
            elif col == 'payment_status':
                renamed_columns[col] = 'Payment Status'
            elif col == 'product_name':
                renamed_columns[col] = 'Product Name'
            elif col == 'batch_number':
                renamed_columns[col] = 'Batch Number'
            elif col == 'expiry_date':
                renamed_columns[col] = 'Expiry Date'
            elif col == 'item_quantity':
                renamed_columns[col] = 'Quantity'
            elif col == 'unit':
                renamed_columns[col] = 'Unit'
            elif col == 'price_per_unit':
                renamed_columns[col] = 'Price per Unit'
            elif col == 'item_total':
                renamed_columns[col] = 'Item Total'
            else:
                # Convert snake_case to Title Case
                renamed_columns[col] = ' '.join(word.title() for word in col.split('_'))
        
        df = df.rename(columns=renamed_columns)
        
        # Convert the DataFrame to an XlsxWriter Excel object
        df.to_excel(writer, sheet_name='Pesticide Orders', index=False)
        
        # Get the worksheet object
        worksheet = writer.sheets['Pesticide Orders']
        
        # Write the column headers with the defined format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Set column widths based on content
        if is_superadmin:
            worksheet.set_column('A:A', 10)  # Order ID
            worksheet.set_column('B:C', 25)  # Admin, Customer
            worksheet.set_column('D:D', 15)  # Order Date
            worksheet.set_column('E:E', 20)  # Product Name
            worksheet.set_column('F:F', 15)  # Batch Number
            worksheet.set_column('G:G', 15)  # Expiry Date
            worksheet.set_column('H:H', 10)  # Quantity
            worksheet.set_column('I:I', 10)  # Unit
            worksheet.set_column('J:K', 15)  # Price per Unit, Item Total
            worksheet.set_column('L:M', 15)  # Delivery Status, Payment Status
        else:
            worksheet.set_column('A:A', 10)  # Order ID
            worksheet.set_column('B:B', 25)  # Customer
            worksheet.set_column('C:C', 15)  # Order Date
            worksheet.set_column('D:D', 20)  # Product Name
            worksheet.set_column('E:E', 15)  # Batch Number
            worksheet.set_column('F:F', 15)  # Expiry Date
            worksheet.set_column('G:G', 10)  # Quantity
            worksheet.set_column('H:H', 10)  # Unit
            worksheet.set_column('I:J', 15)  # Price per Unit, Item Total
            worksheet.set_column('K:L', 15)  # Delivery Status, Payment Status
        
        # Apply conditional formatting for status columns
        status_col = None
        payment_col = None
        amount_cols = []
        date_col = None
        quantity_col = None
        
        for col_num, col_name in enumerate(df.columns):
            if col_name == 'Delivery Status':
                status_col = col_num
            elif col_name == 'Payment Status':
                payment_col = col_num
            elif 'Amount' in col_name or col_name == 'Price per Unit' or col_name == 'Item Total':
                amount_cols.append(col_num)
            elif col_name == 'Expiry Date':
                date_col = col_num
            elif col_name == 'Quantity':
                quantity_col = col_num
        
        # Apply formatting to each row
        for row_num in range(1, len(df) + 1):
            # Apply amount formatting
            for col in amount_cols:
                worksheet.write(row_num, col, df.iloc[row_num-1, col], amount_format)
            
            # Apply date formatting
            if date_col is not None:
                date_value = df.iloc[row_num-1, date_col]
                worksheet.write(row_num, date_col, date_value, date_format)
                
            # Apply quantity formatting
            if quantity_col is not None:
                worksheet.write(row_num, quantity_col, df.iloc[row_num-1, quantity_col], quantity_format)
            
            # Apply status formatting
            if status_col is not None:
                status_value = df.iloc[row_num-1, status_col]
                if status_value == 'Delivered':
                    worksheet.write(row_num, status_col, status_value, delivered_format)
                elif status_value == 'Pending':
                    worksheet.write(row_num, status_col, status_value, pending_format)
            
            # Apply payment status formatting
            if payment_col is not None:
                payment_value = df.iloc[row_num-1, payment_col]
                if payment_value == 'Paid':
                    worksheet.write(row_num, payment_col, payment_value, paid_format)
                elif payment_value == 'Not Paid':
                    worksheet.write(row_num, payment_col, payment_value, not_paid_format)
        
        # Add summary at the bottom
        total_rows = len(df) + 3  # Start 2 rows after the data
        
        worksheet.write(total_rows, 0, 'Summary:', workbook.add_format({'bold': True}))
        worksheet.write(total_rows + 1, 0, 'Total Orders:')
        worksheet.write(total_rows + 1, 1, len(df))
        
        # Calculate totals for item_total if it exists
        if 'Item Total' in df.columns:
            total_amount = df['Item Total'].sum()
            
            worksheet.write(total_rows + 2, 0, 'Total Amount:')
            worksheet.write(total_rows + 2, 1, total_amount, amount_format)
    
    # Close the Pandas Excel writer and output the Excel file
    writer.close()
    
    # Seek to the beginning and read to copy the workbook to a variable
    output.seek(0)
    
    # Create the HttpResponse object with excel header
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response

def generate_pdf(rice_paddy_data, pesticide_data, filename="report.pdf", is_superadmin=False):
    """Generate PDF file from report data with separate tables for rice/paddy and pesticide orders"""
    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()        # Create the PDF object in landscape orientation with larger margins for better readability
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),  # Using landscape orientation
        rightMargin=60,          # Increased right margin
        leftMargin=60,           # Increased left margin
        topMargin=60,            # Increased top margin
        bottomMargin=60,         # Increased bottom margin
        allowSplitting=1,        # Control page breaks
        title=filename,          # Add metadata
        author="Paddy Management System"
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Sample style sheet
    styles = getSampleStyleSheet()
      # Add a title with better styling
    title_style = styles['Heading1']
    title_style.alignment = 1  # Center alignment
    title_style.textColor = colors.darkblue
    title_style.fontSize = 24
    title_style.spaceAfter = 15
    title_style.fontName = 'Helvetica-Bold'
    title = Paragraph("Paddy Order Report", title_style)
    elements.append(title)
    
    # Add a timestamp with better styling
    date_style = styles['Normal']
    date_style.alignment = 1  # Center alignment
    date_style.fontSize = 12
    date_style.textColor = colors.darkslategray
    date_style.spaceAfter = 25
    date_style.fontName = 'Helvetica'
    date_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_paragraph = Paragraph(f"Generated on: {date_string}", date_style)
    elements.append(date_paragraph)      # Section heading for Rice and Paddy Orders
    section_title_style = styles['Heading2']
    section_title_style.alignment = 0  # Left alignment
    section_title_style.textColor = colors.darkblue
    section_title_style.fontSize = 18
    section_title_style.spaceBefore = 30  # Increased space before section
    section_title_style.spaceAfter = 15
    section_title_style.fontName = 'Helvetica-Bold'
    section_title_style.borderWidth = 0
    section_title_style.borderColor = colors.darkblue
    section_title_style.borderPadding = 5
    
    # Add Rice and Paddy Orders Section
    rice_paddy_title = Paragraph("Rice & Paddy Orders", section_title_style)
    elements.append(rice_paddy_title)
    
    # Process Rice/Paddy Orders
    if rice_paddy_data:
        # Define columns based on user role
        if is_superadmin:
            ordered_columns = ['id', 'admin_name', 'customer_name', 'order_date', 'product_type', 'quantity', 
                              'total_amount', 'pending_amount', 'status', 'payment_status']
        else:
            ordered_columns = ['id', 'customer_name', 'order_date', 'product_type', 'quantity', 
                              'total_amount', 'pending_amount', 'status', 'payment_status']          # Make column headers more readable
        readable_headers = []
        for header in ordered_columns:
            if header == 'id':
                # Make Order ID appear on two lines to prevent header collision
                readable_headers.append('Order\nID')
            elif header == 'admin_name':
                readable_headers.append('Admin')
            elif header == 'customer_name':
                readable_headers.append('Customer\nName')  # Break customer name into two lines
            elif header == 'order_date':
                readable_headers.append('Order\nDate')  # Two lines for Order Date
            elif header == 'status':
                readable_headers.append('Delivery\nStatus')  # Two lines for Delivery Status
            elif header == 'payment_status':
                readable_headers.append('Payment\nStatus')  # Two lines for Payment Status
            elif header == 'total_amount':
                readable_headers.append('Total\nAmount')  # Two lines for Total Amount
            elif header == 'pending_amount':
                readable_headers.append('Pending\nAmount')  # Two lines for Pending Amount
            elif header == 'product_type':
                readable_headers.append('Product\nType')  # Two lines for Product Type
            elif header == 'quantity':
                readable_headers.append('Qty')  # Shorter text for Quantity
            else:
                # Convert snake_case to Title Case with line break
                words = [word.title() for word in header.split('_')]
                if len(words) > 1:
                    readable_headers.append(words[0] + '\n' + ' '.join(words[1:]))
                else:
                    readable_headers.append(words[0])
        
        # Prepare table data
        table_data = [readable_headers]  # First row is header
        
        # Add data rows in the correct order
        for item in rice_paddy_data:
            row = [str(item.get(col, '')) for col in ordered_columns]
            table_data.append(row)          # Define column widths - adjusted for landscape orientation with optimal spacing
        col_widths = []
        # Determine column widths based on content and importance
        if is_superadmin:
            col_widths = [
                70,   # Order ID - increased width for multiline header
                80,   # Admin name
                80,   # Customer name
                70,   # Order date
                70,   # Product type
                50,   # Quantity
                70,   # Total amount
                70,   # Pending amount
                70,   # Delivery status
                70    # Payment status
            ]
        else:
            col_widths = [
                70,   # Order ID - increased width for multiline header
                95,   # Customer name
                70,   # Order date
                70,   # Product type
                50,   # Quantity
                70,   # Total amount
                70,   # Pending amount
                70,   # Delivery status
                70    # Payment status
            ]
          # Create table with appropriate column widths
        table = Table(table_data, colWidths=col_widths)        # Add style to the table with improved formatting to prevent text overlay
        style = TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),  # Smaller font size for headers
            ('BOTTOMPADDING', (0, 0), (-1, 0), 14),  # Increased padding for multi-line headers
            ('TOPPADDING', (0, 0), (-1, 0), 14),     # Increased padding for multi-line headers
            ('LEFTPADDING', (0, 0), (-1, 0), 6),     # Increased left padding
            ('RIGHTPADDING', (0, 0), (-1, 0), 6),    # Increased right padding
            
            # Special border for column headers to visually separate them
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.white),
            ('LINEAFTER', (0, -1), (-2, 0), 0.5, colors.white),
            
            # Data rows styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),  # Reduced font size for data
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            
            # Alternate row coloring for better readability
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            
            # Align numeric columns to right
            ('ALIGN', (-4, 1), (-3, -1), 'RIGHT'),  # Amount columns
            
            # Center align certain columns
            ('ALIGN', (-2, 0), (-1, -1), 'CENTER'),  # Status columns
            ('ALIGN', (-6, 0), (-5, -1), 'CENTER'),  # Quantity column
            ('ALIGN', (-7, 0), (-7, -1), 'CENTER'),  # Product type column
            ('ALIGN', (-10, 0), (-10, -1), 'CENTER') if is_superadmin else ('ALIGN', (-9, 0), (-9, -1), 'CENTER'),  # Date column
            
            # Enhanced text wrapping for all cells to prevent overflow
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            
            # Special handling for Order ID column header
            ('LINEBEFORE', (0, 0), (0, 0), 1, colors.darkblue),
            ('LINEAFTER', (0, 0), (0, 0), 1, colors.darkblue),
        ])
          # Find status and payment status column indexes
        status_col = -1
        payment_col = -1
        product_col = -1
        
        for idx, header in enumerate(readable_headers):
            if header == 'Delivery Status':
                status_col = idx
            elif header == 'Payment Status':
                payment_col = idx
            elif header == 'Product Type':
                product_col = idx
        
        # Add conditional formatting for status columns
        for i in range(1, len(table_data)):
            # Delivery Status column
            if status_col >= 0:
                status_value = table_data[i][status_col]
                if status_value == 'Delivered':
                    style.add('TEXTCOLOR', (status_col, i), (status_col, i), colors.darkgreen)
                    style.add('FONTNAME', (status_col, i), (status_col, i), 'Helvetica-Bold')
                elif status_value == 'Pending':
                    style.add('TEXTCOLOR', (status_col, i), (status_col, i), colors.darkorange)
            
            # Payment Status column
            if payment_col >= 0:
                payment_value = table_data[i][payment_col]
                if payment_value == 'Paid':
                    style.add('TEXTCOLOR', (payment_col, i), (payment_col, i), colors.darkgreen)
                    style.add('FONTNAME', (payment_col, i), (payment_col, i), 'Helvetica-Bold')
                elif payment_value == 'Not Paid':
                    style.add('TEXTCOLOR', (payment_col, i), (payment_col, i), colors.red)
            
            # Product Type column - add different colors based on product type
            if product_col >= 0:
                product_value = table_data[i][product_col]
                if product_value == 'Rice':
                    style.add('TEXTCOLOR', (product_col, i), (product_col, i), colors.green)
                elif product_value == 'Paddy':
                    style.add('TEXTCOLOR', (product_col, i), (product_col, i), colors.brown)
        
        table.setStyle(style)
        
        # Add the table to the elements
        elements.append(table)
          # Add summary for Rice and Paddy Orders
        summary_title_style = styles['Heading3']
        summary_title_style.alignment = 0  # Left alignment
        summary_title_style.textColor = colors.darkblue
        summary_title_style.fontSize = 14
        summary_title_style.spaceBefore = 20
        summary_title_style.spaceAfter = 8
        summary_title_style.fontName = 'Helvetica-Bold'
        
        elements.append(Paragraph("Rice & Paddy Summary", summary_title_style))
        
        # Add summary details with better styling
        summary_style = styles['Normal']
        summary_style.fontSize = 11
        summary_style.alignment = 0  # Left alignment
        summary_style.spaceAfter = 6
        summary_style.fontName = 'Helvetica'
        
        # Calculate totals
        total_amount = sum(float(item.get('total_amount', 0)) for item in rice_paddy_data)
        pending_amount = sum(float(item.get('pending_amount', 0)) for item in rice_paddy_data)
        paid_amount = total_amount - pending_amount
          # Create a summary table for better alignment
        summary_data = [
            ["Total Orders:", f"{len(rice_paddy_data)}"],
            ["Total Amount:", f"₹{total_amount:,.2f}"],
            ["Paid Amount:", f"₹{paid_amount:,.2f}"],
            ["Pending Amount:", f"₹{pending_amount:,.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[140, 170])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (1, -1), colors.lightgrey),  # Highlight the last row
            ('LINEBELOW', (0, -1), (1, -1), 1, colors.darkblue),
        ]))
        elements.append(summary_table)
    else:
        # If no data, add a message with better styling
        no_data_style = styles['Normal']
        no_data_style.alignment = 0  # Left alignment
        no_data_style.textColor = colors.darkgrey
        no_data_style.fontSize = 12
        no_data_style.spaceBefore = 10
        no_data_style.spaceAfter = 20
        no_data_style.fontName = 'Helvetica-Oblique'
        no_data = Paragraph("No rice or paddy orders found matching your criteria.", no_data_style)
        elements.append(no_data)
    
    # Add Pesticide Orders Section
    pesticide_title = Paragraph("Pesticide Orders", section_title_style)
    elements.append(pesticide_title)
    
    # Process Pesticide Orders
    if pesticide_data:
        # Define columns based on user role
        if is_superadmin:
            ordered_columns = ['id', 'admin_name', 'customer_name', 'order_date', 
                              'product_name', 'batch_number', 'expiry_date', 'item_quantity', 'unit',
                              'price_per_unit', 'item_total', 'status', 'payment_status']
        else:
            ordered_columns = ['id', 'customer_name', 'order_date', 
                              'product_name', 'batch_number', 'expiry_date', 'item_quantity', 'unit',
                              'price_per_unit', 'item_total', 'status', 'payment_status']
          # Make column headers more readable
        readable_headers = []
        for header in ordered_columns:
            if header == 'id':
                # Make Order ID appear on two lines to prevent header collision
                readable_headers.append('Order\nID')
            elif header == 'admin_name':
                readable_headers.append('Admin')
            elif header == 'customer_name':
                readable_headers.append('Customer\nName')
            elif header == 'order_date':
                readable_headers.append('Order\nDate')  # Also make Order Date two lines
            elif header == 'status':
                readable_headers.append('Delivery\nStatus')  # Make Delivery Status two lines
            elif header == 'payment_status':
                readable_headers.append('Payment\nStatus')  # Make Payment Status two lines
            elif header == 'product_name':
                readable_headers.append('Product\nName')  # Make Product Name two lines
            elif header == 'batch_number':
                readable_headers.append('Batch\nNumber')  # Make Batch Number two lines
            elif header == 'expiry_date':
                readable_headers.append('Expiry\nDate')  # Make Expiry Date two lines
            elif header == 'item_quantity':
                readable_headers.append('Qty')
            elif header == 'unit':
                readable_headers.append('Unit')
            elif header == 'price_per_unit':
                readable_headers.append('Price per\nUnit')  # Make Price per Unit two lines
            elif header == 'item_total':
                readable_headers.append('Item\nTotal')  # Make Item Total two lines
            else:
                # Convert snake_case to Title Case
                readable_headers.append(' '.join(word.title() for word in header.split('_')))
        
        # Prepare table data
        table_data = [readable_headers]  # First row is header
        
        # Add data rows in the correct order
        for item in pesticide_data:
            row = [str(item.get(col, '')) for col in ordered_columns]
            table_data.append(row)          # Define column widths - carefully adjusted for pesticide orders to prevent text overlay
        col_widths = []
        # Determine column widths based on content and importance
        if is_superadmin:
            col_widths = [
                60,   # Order ID - increased for multiline header
                55,   # Admin name
                55,   # Customer name
                55,   # Order date
                65,   # Product name
                55,   # Batch number
                55,   # Expiry date
                40,   # Quantity
                35,   # Unit
                55,   # Price per unit
                55,   # Item total
                55,   # Delivery status
                55    # Payment status
            ]
        else:
            col_widths = [
                60,   # Order ID - increased for multiline header
                60,   # Customer name
                55,   # Order date
                65,   # Product name
                55,   # Batch number
                55,   # Expiry date
                40,   # Quantity
                35,   # Unit
                55,   # Price per unit
                55,   # Item total
                55,   # Delivery status
                55    # Payment status
            ]
        
        # Create table with appropriate column widths
        table = Table(table_data, colWidths=col_widths)        # Add style to the table with improved formatting to prevent text overlay
        style = TableStyle([
                        # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),  # Smaller font size for headers
            ('BOTTOMPADDING', (0, 0), (-1, 0), 14),  # Increased padding for multi-line headers
            ('TOPPADDING', (0, 0), (-1, 0), 14),     # Increased padding for multi-line headers
            ('LEFTPADDING', (0, 0), (-1, 0), 6),     # Increased left padding
            ('RIGHTPADDING', (0, 0), (-1, 0), 6),    # Increased right padding
            
            # Special border for column headers to visually separate them
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.white),
            ('LINEAFTER', (0, -1), (-2, 0), 0.5, colors.white),
            
            # Data rows styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),  # Reduced font size for data
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            
            # Alternate row coloring for better readability
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            
            # Align numeric columns to right
            ('ALIGN', (-4, 1), (-3, -1), 'RIGHT'),  # Price and total columns
            
            # Center align certain columns
            ('ALIGN', (-2, 0), (-1, -1), 'CENTER'),  # Status columns
            ('ALIGN', (-6, 0), (-5, -1), 'CENTER'),  # Quantity and unit columns
            ('ALIGN', (-8, 0), (-7, -1), 'CENTER'),  # Batch number and expiry date
              # Enhanced text wrapping for all cells to prevent overflow
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), True),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
              # Special handling for Order ID column header
            ('LINEBEFORE', (0, 0), (0, 0), 1, colors.darkblue),
            ('LINEAFTER', (0, 0), (0, 0), 1, colors.darkblue),
        ])
          # Find specific column indexes
        status_col = -1
        payment_col = -1
        expiry_col = -1
        
        for idx, header in enumerate(readable_headers):
            if header == 'Delivery Status':
                status_col = idx
            elif header == 'Payment Status':
                payment_col = idx
            elif header == 'Expiry Date':
                expiry_col = idx
        
        # Add conditional formatting for status columns
        for i in range(1, len(table_data)):
            # Delivery Status column
            if status_col >= 0:
                status_value = table_data[i][status_col]
                if status_value == 'Delivered':
                    style.add('TEXTCOLOR', (status_col, i), (status_col, i), colors.darkgreen)
                    style.add('FONTNAME', (status_col, i), (status_col, i), 'Helvetica-Bold')
                elif status_value == 'Pending':
                    style.add('TEXTCOLOR', (status_col, i), (status_col, i), colors.darkorange)
            
            # Payment Status column
            if payment_col >= 0:
                payment_value = table_data[i][payment_col]
                if payment_value == 'Paid':
                    style.add('TEXTCOLOR', (payment_col, i), (payment_col, i), colors.darkgreen)
                    style.add('FONTNAME', (payment_col, i), (payment_col, i), 'Helvetica-Bold')
                elif payment_value == 'Not Paid':
                    style.add('TEXTCOLOR', (payment_col, i), (payment_col, i), colors.red)
            
            # Expiry Date column - add warning color if near expiry
            if expiry_col >= 0:
                try:
                    expiry_value = table_data[i][expiry_col]
                    expiry_date = datetime.strptime(expiry_value, "%Y-%m-%d").date()
                    today = datetime.now().date()
                    days_to_expiry = (expiry_date - today).days
                    
                    if days_to_expiry < 30:  # Less than a month to expiry
                        style.add('TEXTCOLOR', (expiry_col, i), (expiry_col, i), colors.red)
                        style.add('FONTNAME', (expiry_col, i), (expiry_col, i), 'Helvetica-Bold')
                    elif days_to_expiry < 90:  # Less than 3 months to expiry
                        style.add('TEXTCOLOR', (expiry_col, i), (expiry_col, i), colors.orange)
                except (ValueError, TypeError):
                    # Skip if date format is invalid
                    pass
        
        table.setStyle(style)
        
        # Add the table to the elements
        elements.append(table)
          # Add summary for Pesticide Orders
        summary_title_style = styles['Heading3']
        summary_title_style.alignment = 0  # Left alignment
        summary_title_style.textColor = colors.darkblue
        summary_title_style.fontSize = 14
        summary_title_style.spaceBefore = 20
        summary_title_style.spaceAfter = 8
        summary_title_style.fontName = 'Helvetica-Bold'
        
        elements.append(Paragraph("Pesticide Summary", summary_title_style))
        
        # Add summary details with better styling
        summary_style = styles['Normal']
        summary_style.fontSize = 11
        summary_style.alignment = 0  # Left alignment
        summary_style.spaceAfter = 6
        summary_style.fontName = 'Helvetica'
        
        # Calculate totals
        total_amount = sum(float(item.get('item_total', 0)) for item in pesticide_data)
        
        # Count unique orders
        unique_order_ids = set(item.get('id') for item in pesticide_data)
          # Create a summary table for better alignment
        summary_data = [
            ["Total Orders:", f"{len(unique_order_ids)}"],
            ["Total Items:", f"{len(pesticide_data)}"],
            ["Total Amount:", f"₹{total_amount:,.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[140, 170])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (1, -1), colors.lightgrey),  # Highlight the last row
            ('LINEBELOW', (0, -1), (1, -1), 1, colors.darkblue),
        ]))
        
        elements.append(summary_table)
    else:
        # If no data, add a message with better styling
        no_data_style = styles['Normal']
        no_data_style.alignment = 0  # Left alignment
        no_data_style.textColor = colors.darkgrey
        no_data_style.fontSize = 12
        no_data_style.spaceBefore = 10
        no_data_style.spaceAfter = 20
        no_data_style.fontName = 'Helvetica-Oblique'
        no_data = Paragraph("No pesticide orders found matching your criteria.", no_data_style)
        elements.append(no_data)

    # Add overall summary section
    if rice_paddy_data or pesticide_data:
        overall_title_style = styles['Heading2']
        overall_title_style.alignment = 0  # Left alignment
        overall_title_style.textColor = colors.darkblue
        overall_title_style.fontSize = 16
        overall_title_style.spaceBefore = 30  # Increased spacing
        overall_title_style.spaceAfter = 10
        overall_title_style.fontName = 'Helvetica-Bold'
        
        elements.append(Paragraph("Overall Summary", overall_title_style))
        
        # Calculate overall totals
        rice_paddy_total = sum(float(item.get('total_amount', 0)) for item in rice_paddy_data)
        pesticide_total = sum(float(item.get('item_total', 0)) for item in pesticide_data)
        overall_total = rice_paddy_total + pesticide_total
        
        rice_paddy_pending = sum(float(item.get('pending_amount', 0)) for item in rice_paddy_data)
        overall_paid = overall_total - rice_paddy_pending
          # Create a summary table for better alignment
        summary_data = [
            ["Total Rice & Paddy Orders:", f"{len(rice_paddy_data)}"],
            ["Total Pesticide Orders:", f"{len(set(item.get('id') for item in pesticide_data))}"],
            ["Overall Total Amount:", f"₹{overall_total:,.2f}"],
            ["Overall Paid Amount:", f"₹{overall_paid:,.2f}"],
            ["Overall Pending Amount:", f"₹{rice_paddy_pending:,.2f}"]
        ]
        
        # Add a more professional-looking summary table
        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEBELOW', (0, -1), (1, -1), 1, colors.darkblue),
            ('BACKGROUND', (0, -1), (1, -1), colors.lightgrey),
        ]))
        
        elements.append(summary_table)
    
    # Build the PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    response.write(pdf)
    
    return response

@role_required(["admin"])
def admin_reports(request):
    """View for admin reports"""
    # Check if user is logged in
    if not request.session.get("user_id") or not request.session.get("role"):
        return redirect("/")
    
    # Get admin ID from session
    admin_id = request.session.get("user_id")
    
    # Get customers for filter dropdown
    customers = CustomerTable.objects.filter(admin_id=admin_id)
    
    # Get filtered orders
    orders = get_admin_report_data(request)
    
    # Debug: Print the first few order IDs to check sorting
    print(f"DEBUG: First 5 order IDs after sorting: {[order.order_id for order in orders[:5]]}")
    print(f"DEBUG: Sort parameters - sort: {request.GET.get('sort', '')}, dir: {request.GET.get('dir', '')}")
    
    # Format data for template
    rice_paddy_orders = []
    pesticide_orders = []
    
    for order in orders:
        payment_status = "Not Paid"
        if order.payment_status == 1:
            payment_status = "Paid"
        
        # Get product type name based on product_category_id
        product_type = "Unknown"
        if order.product_category_id == 1:
            product_type = "Rice"
        elif order.product_category_id == 2:
            product_type = "Paddy"
        elif order.product_category_id == 3:
            product_type = "Pesticide"
            
        # Create base order data
        order_data = {
            'id': order.order_id,
            'customer_name': f"{order.customer.first_name} {order.customer.last_name}" if order.customer else "N/A",
            'order_date': order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A",
            'status': "Delivered" if order.delivery_status == 1 else "Pending",
            'payment_status': payment_status,
            'total_amount': order.overall_amount,
            'pending_amount': order.overall_amount - (order.paid_amount or 0),
            'product_type': product_type,
            'quantity': order.quantity
        }
            
        # Separate pesticide orders from rice/paddy orders
        if order.product_category_id == 3:  # Pesticide
            # Get order items for pesticides
            order_items = OrderItems.objects.filter(order=order)
            if order_items.exists():
                for item in order_items:
                    pesticide_order = order_data.copy()
                    pesticide_order.update({
                        'product_name': item.product_name,
                        'batch_number': item.batch_number,
                        'expiry_date': item.expiry_date.strftime('%Y-%m-%d') if item.expiry_date else "N/A",
                        'price_per_unit': item.price_per_unit,
                        'item_quantity': item.quantity,
                        'item_total': item.total_amount,
                        'unit': item.unit
                    })
                    pesticide_orders.append(pesticide_order)
            else:
                # If no order items found, still add the basic pesticide order
                pesticide_orders.append(order_data)
        else:  # Rice or Paddy
            rice_paddy_orders.append(order_data)
    
    # Handle export requests
    export_format = request.GET.get('export', '')
    if export_format == 'excel':
        return generate_excel(rice_paddy_orders, pesticide_orders, filename="admin_report.xlsx")
    elif export_format == 'pdf':
        return generate_pdf(rice_paddy_orders, pesticide_orders, filename="admin_report.pdf")
    
    # Return template with context
    return render(request, 'admin_reports.html', {
        'rice_paddy_orders': rice_paddy_orders,
        'pesticide_orders': pesticide_orders,
        'customers': customers,
        'filters': {
            'customer': request.GET.get('customer', ''),
            'order_status': request.GET.get('order_status', ''),
            'payment_status': request.GET.get('payment_status', ''),
            'start_date': request.GET.get('start_date', ''),
            'end_date': request.GET.get('end_date', ''),
            'date_preset': request.GET.get('date_preset', ''),
            'product_type': request.GET.get('product_type', ''),
            'sort': request.GET.get('sort', ''),
            'dir': request.GET.get('dir', '')
        }
    })

@role_required(["superadmin"])
def superadmin_reports(request):
    """View for superadmin reports"""
    # Check if user is logged in
    if not request.session.get("user_id") or not request.session.get("role"):
        return redirect("/")
    
    # Get all admins and customers for filter dropdowns
    admins = AdminTable.objects.all()
    customers = CustomerTable.objects.all()
    
    # Get filtered orders
    orders = get_superadmin_report_data(request)
    
    # Debug: Print the first few order IDs to check sorting
    print(f"DEBUG: Superadmin First 5 order IDs after sorting: {[order.order_id for order in orders[:5]]}")
    print(f"DEBUG: Superadmin Sort parameters - sort: {request.GET.get('sort', '')}, dir: {request.GET.get('dir', '')}")
    
    # Format data for template
    rice_paddy_orders = []
    pesticide_orders = []
    
    for order in orders:
        payment_status = "Not Paid"
        if order.payment_status == 1:
            payment_status = "Paid"
        
        # Get product type name based on product_category_id
        product_type = "Unknown"
        if order.product_category_id == 1:
            product_type = "Rice"
        elif order.product_category_id == 2:
            product_type = "Paddy"
        elif order.product_category_id == 3:
            product_type = "Pesticide"
            
        # Create base order data
        order_data = {
            'id': order.order_id,
            'admin_name': f"{order.admin.first_name} {order.admin.last_name}" if order.admin else "N/A",
            'customer_name': f"{order.customer.first_name} {order.customer.last_name}" if order.customer else "N/A",
            'order_date': order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A",
            'status': "Delivered" if order.delivery_status == 1 else "Pending",
            'payment_status': payment_status,
            'total_amount': order.overall_amount,
            'pending_amount': order.overall_amount - (order.paid_amount or 0),
            'product_type': product_type,
            'quantity': order.quantity
        }
            
        # Separate pesticide orders from rice/paddy orders
        if order.product_category_id == 3:  # Pesticide
            # Get order items for pesticides
            order_items = OrderItems.objects.filter(order=order)
            if order_items.exists():
                for item in order_items:
                    pesticide_order = order_data.copy()
                    pesticide_order.update({
                        'product_name': item.product_name,
                        'batch_number': item.batch_number,
                        'expiry_date': item.expiry_date.strftime('%Y-%m-%d') if item.expiry_date else "N/A",
                        'price_per_unit': item.price_per_unit,
                        'item_quantity': item.quantity,
                        'item_total': item.total_amount,
                        'unit': item.unit
                    })
                    pesticide_orders.append(pesticide_order)
            else:
                # If no order items found, still add the basic pesticide order
                pesticide_orders.append(order_data)
        else:  # Rice or Paddy
            rice_paddy_orders.append(order_data)
    
    # Handle export requests
    export_format = request.GET.get('export', '')
    if export_format == 'excel':
        return generate_excel(rice_paddy_orders, pesticide_orders, filename="superadmin_report.xlsx", is_superadmin=True)
    elif export_format == 'pdf':
        return generate_pdf(rice_paddy_orders, pesticide_orders, filename="superadmin_report.pdf", is_superadmin=True)
    
    # Return template with context
    return render(request, 'superadmin_reports.html', {
        'rice_paddy_orders': rice_paddy_orders,
        'pesticide_orders': pesticide_orders,
        'admins': admins,
        'customers': customers,
        'filters': {
            'admin': request.GET.get('admin', ''),
            'customer': request.GET.get('customer', ''),
            'order_status': request.GET.get('order_status', ''),
            'payment_status': request.GET.get('payment_status', ''),
            'start_date': request.GET.get('start_date', ''),
            'end_date': request.GET.get('end_date', ''),
            'date_preset': request.GET.get('date_preset', ''),
            'product_type': request.GET.get('product_type', ''),
            'sort': request.GET.get('sort', ''),
            'dir': request.GET.get('dir', '')
        }
    })
