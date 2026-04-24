from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from store.models import Product, Order, OrderItem, CustomerProfile, Coupon, Review, Category, Complaint
from store.forms import ProductForm, CouponForm, CategoryForm


# Owner authentication check
def is_owner(user):
    return user.is_authenticated and (user.is_staff or user.username == 'TheDiora')


def owner_login_view(request):
    if request.user.is_authenticated and is_owner(request.user):
        return redirect('owner_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and is_owner(user):
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('owner_dashboard')
        else:
            messages.error(request, 'Invalid credentials.')
    
    context = {}
    return render(request, 'owner/login.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('owner_login')


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_dashboard_view(request):
    # Analytics data
    now = timezone.now()
    today = now.date()
    this_week = today - timedelta(days=7)
    this_month = today - timedelta(days=30)
    
    # Time-based reports
    last_1_hour = now - timedelta(hours=1)
    last_24_hours = now - timedelta(hours=24)
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)
    
    # 1 Hour Report
    orders_1h = Order.objects.filter(created_at__gte=last_1_hour)
    revenue_1h = orders_1h.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    count_1h = orders_1h.count()
    
    # 24 Hour Report
    orders_24h = Order.objects.filter(created_at__gte=last_24_hours)
    revenue_24h = orders_24h.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    count_24h = orders_24h.count()
    
    # 7 Days Report
    orders_7d = Order.objects.filter(created_at__gte=last_7_days)
    revenue_7d = orders_7d.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    count_7d = orders_7d.count()
    
    # 30 Days Report
    orders_30d = Order.objects.filter(created_at__gte=last_30_days)
    revenue_30d = orders_30d.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    count_30d = orders_30d.count()
    
    # Total statistics
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status__in=['delivered', 'completed']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_customers = CustomerProfile.objects.count()
    total_products = Product.objects.count()
    
    # Today's statistics
    today_orders = Order.objects.filter(created_at__date=today)
    today_revenue = today_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Weekly statistics
    week_orders = Order.objects.filter(created_at__date__gte=this_week)
    week_revenue = week_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Monthly statistics
    month_orders = Order.objects.filter(created_at__date__gte=this_month)
    month_revenue = month_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Recent orders
    recent_orders = Order.objects.order_by('-created_at')[:10]
    
    # Top selling products
    top_products = OrderItem.objects.values('product__name', 'product__id').annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:5]
    
    # Low stock products
    low_stock_products = Product.objects.filter(stock_quantity__lte=5, is_available=True)[:5]
    
    # Pending orders
    pending_orders = Order.objects.filter(status='pending').count()
    
    # All reviews (auto-approved)
    all_reviews_queryset = Review.objects.all().order_by('-created_at')[:20]
    total_reviews_count = Review.objects.count()
    
    # Cancelled orders
    cancelled_orders = Order.objects.filter(status='cancelled').order_by('-updated_at')[:10]
    
    # Returned orders
    returned_orders = Order.objects.filter(status='returned').order_by('-updated_at')[:10]
    
    # Pending complaints
    pending_complaints = Complaint.objects.filter(status='pending').order_by('-created_at')[:10]
    
    # All orders with timing info
    all_orders = Order.objects.all().order_by('-created_at')[:20]
    
    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_customers': total_customers,
        'total_products': total_products,
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'low_stock_products': low_stock_products,
        'pending_orders': pending_orders,
        'all_reviews': all_reviews_queryset,
        'total_reviews': total_reviews_count,
        'cancelled_orders': cancelled_orders,
        'returned_orders': returned_orders,
        'pending_complaints': pending_complaints,
        'all_orders': all_orders,
        # Time-based reports
        'orders_1h': count_1h,
        'revenue_1h': revenue_1h,
        'orders_24h': count_24h,
        'revenue_24h': revenue_24h,
        'orders_7d': count_7d,
        'revenue_7d': revenue_7d,
        'orders_30d': count_30d,
        'revenue_30d': revenue_30d,
    }
    return render(request, 'owner/dashboard.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def resolve_complaint_view(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    if request.method == 'POST':
        action = request.POST.get('action', 'resolve')
        response = request.POST.get('response', '')
        
        if not response:
            messages.error(request, 'Please provide a response.')
            return redirect('owner_dashboard')
        
        if action == 'resolve':
            complaint.resolve(response)
            messages.success(request, f'Complaint by {complaint.user.username} has been resolved.')
        elif action == 'reject':
            complaint.status = 'rejected'
            complaint.owner_response = response
            from django.utils import timezone
            complaint.resolved_at = timezone.now()
            complaint.save()
            messages.warning(request, f'Complaint by {complaint.user.username} has been rejected.')
    
    return redirect('owner_dashboard')


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_product_list_view(request):
    products = Product.objects.all().order_by('-created_at')
    
    # Search
    query = request.GET.get('q')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    
    # Filter by category
    category_slug = request.GET.get('category')
    if category_slug:
        from store.models import Category
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    # Filter by availability
    availability = request.GET.get('availability')
    if availability == 'available':
        products = products.filter(is_available=True)
    elif availability == 'unavailable':
        products = products.filter(is_available=False)
    
    # Filter by stock
    stock_filter = request.GET.get('stock')
    if stock_filter == 'low':
        products = products.filter(stock_quantity__lte=5)
    elif stock_filter == 'out':
        products = products.filter(stock_quantity=0)
    
    context = {
        'products': products,
        'query': query,
    }
    return render(request, 'owner/product_list.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_product_add_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" added successfully!')
            return redirect('owner_products')
    else:
        form = ProductForm()
    
    context = {'form': form}
    return render(request, 'owner/product_form.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_product_edit_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('owner_products')
    else:
        form = ProductForm(instance=product)
    
    context = {'form': form, 'product': product}
    return render(request, 'owner/product_form.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_product_delete_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product_name = product.name
    product.delete()
    messages.success(request, f'Product "{product_name}" deleted successfully!')
    return redirect('owner_products')


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_order_list_view(request):
    orders = Order.objects.all().order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    # Filter by payment method
    payment = request.GET.get('payment')
    if payment:
        orders = orders.filter(payment_method=payment)
    
    # Search by order number or customer
    query = request.GET.get('q')
    if query:
        orders = orders.filter(
            Q(order_number__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        )
    
    context = {
        'orders': orders,
        'status': status,
    }
    return render(request, 'owner/order_list.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_order_detail_view(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order_items = order.items.all()
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, f'Order #{order.order_number} status updated to {new_status}')
            return redirect('owner_order_detail', pk=pk)
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'owner/order_detail.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def print_shipping_label_view(request, order_id):
    """Print compact shipping label for box"""
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'owner/print_shipping_label.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def print_invoice_view(request, order_id):
    """Print detailed invoice/bill for customer"""
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'owner/print_invoice.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_customer_list_view(request):
    customers = CustomerProfile.objects.all().order_by('-created_at')
    
    # Search
    query = request.GET.get('q')
    if query:
        customers = customers.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query)
        )
    
    context = {
        'customers': customers,
        'query': query,
    }
    return render(request, 'owner/customer_list.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_customer_detail_view(request, pk):
    customer = get_object_or_404(CustomerProfile, pk=pk)
    orders = Order.objects.filter(user=customer.user).order_by('-created_at')
    
    context = {
        'customer': customer,
        'orders': orders,
    }
    return render(request, 'owner/customer_detail.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_analytics_view(request):
    # Time period selection
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    # Orders in period
    orders = Order.objects.filter(created_at__date__gte=start_date)
    
    # Revenue by status
    delivered_revenue = orders.filter(status__in=['delivered', 'completed']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Orders by status
    orders_by_status = orders.values('status').annotate(count=Count('id'))
    
    # Sales trend (daily)
    daily_sales = orders.filter(status__in=['delivered', 'completed']).extra(
        select={'date': 'DATE(created_at)'}
    ).values('date').annotate(total=Sum('total_amount')).order_by('date')
    
    # Top products
    top_products = OrderItem.objects.filter(order__created_at__date__gte=start_date).values(
        'product__name', 
        'product__id'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('price')
    ).order_by('-total_sold')[:10]
    
    # Payment method distribution
    payment_methods = orders.values('payment_method').annotate(count=Count('id'))
    
    context = {
        'days': days,
        'start_date': start_date,
        'delivered_revenue': delivered_revenue,
        'orders_by_status': orders_by_status,
        'daily_sales': daily_sales,
        'top_products': top_products,
        'payment_methods': payment_methods,
        'total_orders': orders.count(),
    }
    return render(request, 'owner/analytics.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_coupon_list_view(request):
    coupons = Coupon.objects.all().order_by('-created_at')
    
    context = {
        'coupons': coupons,
    }
    return render(request, 'owner/coupon_list.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_coupon_add_view(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save()
            messages.success(request, f'Coupon "{coupon.code}" created successfully!')
            return redirect('owner_coupons')
    else:
        form = CouponForm()
    
    context = {'form': form}
    return render(request, 'owner/coupon_form.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_coupon_edit_view(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            coupon = form.save()
            messages.success(request, f'Coupon "{coupon.code}" updated successfully!')
            return redirect('owner_coupons')
    else:
        form = CouponForm(instance=coupon)
    
    context = {'form': form, 'coupon': coupon}
    return render(request, 'owner/coupon_form.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_coupon_delete_view(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon_code = coupon.code
    coupon.delete()
    messages.success(request, f'Coupon "{coupon_code}" deleted successfully!')
    return redirect('owner_coupons')


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_review_list_view(request):
    reviews = Review.objects.all().order_by('-created_at')
    
    context = {
        'reviews': reviews,
    }
    return render(request, 'owner/review_list.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_category_list_view(request):
    categories = Category.objects.all().order_by('name')
    
    # Search
    query = request.GET.get('q')
    if query:
        categories = categories.filter(Q(name__icontains=query) | Q(description__icontains=query))
    
    context = {
        'categories': categories,
        'query': query,
    }
    return render(request, 'owner/category_list.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_category_add_view(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" added successfully!')
            return redirect('owner_categories')
    else:
        form = CategoryForm()
    
    context = {'form': form}
    return render(request, 'owner/category_form.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_category_edit_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('owner_categories')
    else:
        form = CategoryForm(instance=category)
    
    context = {'form': form, 'category': category}
    return render(request, 'owner/category_form.html', context)


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_category_delete_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category_name = category.name
    category.delete()
    messages.success(request, f'Category "{category_name}" deleted successfully!')
    return redirect('owner_categories')


@login_required(login_url='/owner/login/')
@user_passes_test(is_owner, login_url='/owner/login/')
def owner_promote_product_view(request, product_id):
    """Owner can promote a product (free promotion - no payment required)"""
    product = get_object_or_404(Product, id=product_id)
    product.is_promoted = not product.is_promoted
    product.save()
    
    status = "promoted" if product.is_promoted else "unpromoted"
    messages.success(request, f'Product "{product.name}" has been {status}!')
    return redirect('owner_products')
