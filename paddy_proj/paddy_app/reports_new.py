from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .decorators import role_required
from .models import Orders, CustomerTable, Payments, AdminTable
import pandas as pd
import io
from datetime import datetime
from django.db.models import Q
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
import csv
import xlsxwriter

def get_admin_report_data(request):
    """Get filtered report data for admin users"""
    # Get filter parameters
    customer_id = request.GET.get('customer', '')
    order_status = request.GET.get('order_status', '')
    payment_status = request.GET.get('payment_status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Start with all orders for admin
    orders = Orders.objects.filter(admin=request.user)
    
    # Apply filters
    if customer_id:
        orders = orders.filter(customer_id=customer_id)
    
    if order_status:
        orders = orders.filter(delivery_status=order_status)
    
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            orders = orders.filter(created_at__gte=start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            orders = orders.filter(created_at__lte=end_date)
        except ValueError:
            pass
    
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
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            orders = orders.filter(created_at__gte=start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            orders = orders.filter(created_at__lte=end_date)
        except ValueError:
            pass
    
    return orders

def generate_excel(data, filename="report.xlsx"):
    """Generate Excel file from report data"""
    # Create a pandas DataFrame
    df = pd.DataFrame(data)
    
    # Create an in-memory output file
    output = io.BytesIO()
    
    # Create Excel writer using XlsxWriter as the engine
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Convert the DataFrame to an XlsxWriter Excel object
    df.to_excel(writer, sheet_name='Report', index=False)
    
    # Get the xlsxwriter workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets['Report']
    
    # Add some header formatting
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#D7E4BC',
        'border': 1
    })
    
    # Write the column headers with the defined format
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(col_num, col_num, 15)  # Set width
    
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

def generate_pdf(data, filename="report.pdf"):
    """Generate PDF file from report data"""
    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()
    
    # Create the PDF object, using the buffer as its "file"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Sample style sheet
    styles = getSampleStyleSheet()
    
    # Add a title
    title = Paragraph("Paddy Report", styles['Heading1'])
    elements.append(title)
    
    # Add a timestamp
    date_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_paragraph = Paragraph(f"Generated on: {date_string}", styles['Normal'])
    elements.append(date_paragraph)
    
    # Prepare data for the table
    if data:
        # Extract column headers
        columns = list(data[0].keys())
        
        # Prepare table data
        table_data = [columns]  # First row is header
        
        # Add data rows
        for item in data:
            row = [str(item.get(col, '')) for col in columns]
            table_data.append(row)
        
        # Create the table
        table = Table(table_data)
        
        # Add style to the table
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(style)
        
        # Add the table to the elements
        elements.append(table)
    else:
        # If no data, add a message
        no_data = Paragraph("No data available for this report.", styles['Normal'])
        elements.append(no_data)
    
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

@login_required
@role_required(["admin"])
def admin_reports(request):
    """View for admin reports"""
    # Get customers for filter dropdown
    customers = CustomerTable.objects.filter(admin=request.user)
    
    # Get filtered orders
    orders = get_admin_report_data(request)
    
    # Format data for template
    orders_data = []
    for order in orders:
        payment_status = "Not Paid"
        if order.payment_status == 1:
            payment_status = "Paid"
            
        orders_data.append({
            'id': order.order_id,
            'customer_name': f"{order.customer.first_name} {order.customer.last_name}" if order.customer else "N/A",
            'order_date': order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A",
            'status': "Delivered" if order.delivery_status == 1 else "Pending",
            'payment_status': payment_status,
            'total_amount': order.overall_amount
        })
    
    # Handle export requests
    export_format = request.GET.get('export', '')
    if export_format == 'excel':
        return generate_excel(orders_data, filename="admin_report.xlsx")
    elif export_format == 'pdf':
        return generate_pdf(orders_data, filename="admin_report.pdf")
    
    # Return template with context
    return render(request, 'admin_reports.html', {
        'orders': orders_data,
        'customers': customers,
        'filters': {
            'customer': request.GET.get('customer', ''),
            'order_status': request.GET.get('order_status', ''),
            'payment_status': request.GET.get('payment_status', ''),
            'start_date': request.GET.get('start_date', ''),
            'end_date': request.GET.get('end_date', '')
        }
    })

@login_required
@role_required(["superadmin"])
def superadmin_reports(request):
    """View for superadmin reports"""
    # Get all admins and customers for filter dropdowns
    admins = AdminTable.objects.all()
    customers = CustomerTable.objects.all()
    
    # Get filtered orders
    orders = get_superadmin_report_data(request)
    
    # Format data for template
    orders_data = []
    for order in orders:
        payment_status = "Not Paid"
        if order.payment_status == 1:
            payment_status = "Paid"
            
        orders_data.append({
            'id': order.order_id,
            'admin_name': f"{order.admin.first_name} {order.admin.last_name}" if order.admin else "N/A",
            'customer_name': f"{order.customer.first_name} {order.customer.last_name}" if order.customer else "N/A",
            'order_date': order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A",
            'status': "Delivered" if order.delivery_status == 1 else "Pending",
            'payment_status': payment_status,
            'total_amount': order.overall_amount
        })
    
    # Handle export requests
    export_format = request.GET.get('export', '')
    if export_format == 'excel':
        return generate_excel(orders_data, filename="superadmin_report.xlsx")
    elif export_format == 'pdf':
        return generate_pdf(orders_data, filename="superadmin_report.pdf")
    
    # Return template with context
    return render(request, 'superadmin_reports.html', {
        'orders': orders_data,
        'admins': admins,
        'customers': customers,
        'filters': {
            'admin': request.GET.get('admin', ''),
            'customer': request.GET.get('customer', ''),
            'order_status': request.GET.get('order_status', ''),
            'payment_status': request.GET.get('payment_status', ''),
            'start_date': request.GET.get('start_date', ''),
            'end_date': request.GET.get('end_date', '')
        }
    })
