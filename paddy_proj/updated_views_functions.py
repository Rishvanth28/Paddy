# Updated views functions with filtering support

@role_required(["superadmin"])
def customize_pdf_report_superadmin(request):
    if request.method == 'POST':
        form = SuperAdminCustomReportForm(request.POST)
        if form.is_valid():
            # Store all form data in session for filtering and field selection
            cleaned_data = form.cleaned_data.copy()
            
            # Convert queryset to list of IDs (store in session)
            if cleaned_data.get('selected_admins'):
                cleaned_data['selected_admin_ids'] = [admin.admin_id for admin in cleaned_data['selected_admins']]
            if cleaned_data.get('selected_customers'):
                cleaned_data['selected_customer_ids'] = [customer.customer_id for customer in cleaned_data['selected_customers']]
            
            # Remove the queryset objects as they can't be serialized
            cleaned_data.pop('selected_admins', None)
            cleaned_data.pop('selected_customers', None)
            
            request.session['report_filters'] = cleaned_data
            return redirect('download_custom_pdf')
    else:
        form = SuperAdminCustomReportForm()

    return render(request, 'customize_pdf_report_superadmin.html', {'form': form})


@role_required(["admin", "superadmin"])
def download_custom_pdf(request):
    # Check for new filtering system first, then fall back to old system
    report_filters = request.session.get('report_filters')
    selected_fields = request.session.get('selected_fields')  # Legacy support
    
    if not report_filters and not selected_fields:
        # Redirect based on user role
        if hasattr(request.user, 'role') and request.user.role == 'superadmin':
            return redirect('customize_pdf_report_superadmin')
        else:
            return redirect('customize_pdf_report_admin')
    
    # Use new filtering system if available, otherwise fall back to legacy
    filters = report_filters or selected_fields
    
    # Start building the query
    orders_query = Orders.objects.select_related('admin', 'customer').prefetch_related(
        Prefetch('items', queryset=OrderItems.objects.all()),
        Prefetch('payments_set', queryset=Payments.objects.all())
    )
    
    # Apply filters
    filter_conditions = Q()
    
    # Admin/Customer filters
    selected_admin_ids = filters.get('selected_admin_ids', filters.get('selected_admins', []))
    selected_customer_ids = filters.get('selected_customer_ids', filters.get('selected_customers', []))
    
    if selected_admin_ids:
        filter_conditions |= Q(admin__admin_id__in=selected_admin_ids)
    if selected_customer_ids:
        filter_conditions |= Q(customer__customer_id__in=selected_customer_ids)
    
    # Date range filters
    if filters.get('date_from'):
        filter_conditions &= Q(order_date__gte=filters['date_from'])
    if filters.get('date_to'):
        filter_conditions &= Q(order_date__lte=filters['date_to'])
    
    # Payment status filter
    if filters.get('payment_status') != '' and filters.get('payment_status') is not None:
        filter_conditions &= Q(payment_status=int(filters['payment_status']))
    
    # Delivery status filter
    if filters.get('delivery_status') != '' and filters.get('delivery_status') is not None:
        filter_conditions &= Q(delivery_status=int(filters['delivery_status']))
    
    # Category filter
    if filters.get('category'):
        filter_conditions &= Q(category__icontains=filters['category'])
    
    # Amount range filters
    if filters.get('amount_min'):
        filter_conditions &= Q(overall_amount__gte=filters['amount_min'])
    if filters.get('amount_max'):
        filter_conditions &= Q(overall_amount__lte=filters['amount_max'])
    
    # Apply filters and sorting
    if filter_conditions:
        orders_query = orders_query.filter(filter_conditions)
    else:
        # If no filters, show all orders (for legacy compatibility)
        orders_query = orders_query.all()
    
    # Apply sorting
    sort_by = filters.get('sort_by', '-order_date')
    orders = orders_query.distinct().order_by(sort_by)

    # PDF Generation continues...
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=40,
        bottomMargin=30,
        title="Business Report"
    )

    # PDF generation code continues as before...
    # [Rest of the PDF generation code remains the same]


# Function to add filtering to unified report view
def apply_report_filters(orders_query, filters):
    """Apply filters to orders query"""
    filter_conditions = Q()
    
    # Date range filters
    if filters.get('date_from'):
        filter_conditions &= Q(order_date__gte=filters['date_from'])
    if filters.get('date_to'):
        filter_conditions &= Q(order_date__lte=filters['date_to'])
    
    # Payment status filter
    if filters.get('payment_status') != '' and filters.get('payment_status') is not None:
        filter_conditions &= Q(payment_status=int(filters['payment_status']))
    
    # Delivery status filter
    if filters.get('delivery_status') != '' and filters.get('delivery_status') is not None:
        filter_conditions &= Q(delivery_status=int(filters['delivery_status']))
    
    # Category filter
    if filters.get('category'):
        filter_conditions &= Q(category__icontains=filters['category'])
    
    # Amount range filters
    if filters.get('amount_min'):
        filter_conditions &= Q(overall_amount__gte=filters['amount_min'])
    if filters.get('amount_max'):
        filter_conditions &= Q(overall_amount__lte=filters['amount_max'])
    
    # Admin/Customer filters
    if filters.get('selected_admin_ids'):
        filter_conditions &= Q(admin__admin_id__in=filters['selected_admin_ids'])
    if filters.get('selected_customer_ids'):
        filter_conditions &= Q(customer__customer_id__in=filters['selected_customer_ids'])
    
    # Apply filters if any exist
    if filter_conditions:
        orders_query = orders_query.filter(filter_conditions)
    
    # Apply sorting
    sort_by = filters.get('sort_by', '-order_date')
    return orders_query.order_by(sort_by)
