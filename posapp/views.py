from __future__ import annotations

import csv
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ExpenseForm, PasswordResetForm, ProductForm, SaleForm, UserAccountForm
from .models import CustomUser, Expense, Product, ProductVariant, Sale, SaleItem, SaleReturn


def require_login(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return None


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


@login_required
def protected_root(request):
    return redirect('dashboard')


def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            portal_urls = {
                'dashboard': 'dashboard',
                'products': 'products',
                'stock': 'stock',
                'sales': 'sales',
                'expenses': 'expenses',
                'reports': 'reports',
                'sale_returns': 'sale_returns',
            }
            default_portal = portal_urls.get(user.default_portal)
            portal_permissions = {
                'dashboard': ('view_dashboard',),
                'products': ('view_products',),
                'stock': ('view_stock',),
                'sales': ('view_own_sales_history', 'view_all_sales_history'),
                'expenses': ('view_own_expense_history', 'view_all_expense_history'),
                'reports': ('view_reports',),
                'sale_returns': ('view_return_notifications',),
            }
            if default_portal and any(user.has_permission(permission) for permission in portal_permissions.get(user.default_portal, ())):
                return redirect(default_portal)
            if user.has_permission('view_dashboard'):
                return redirect('dashboard')
            portal_permissions = (
                ('view_products', 'products'),
                ('view_stock', 'stock'),
                ('view_own_sales_history', 'sales'),
                ('view_all_sales_history', 'sales'),
                ('view_own_expense_history', 'expenses'),
                ('view_all_expense_history', 'expenses'),
                ('view_reports', 'reports'),
                ('view_return_notifications', 'sale_returns'),
            )
            for permission, portal in portal_permissions:
                if user.has_permission(permission):
                    return redirect(portal)
            logout(request)
            messages.error(request, 'No portal access has been assigned to this account.')
            return redirect('login')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'posapp/login.html')


@login_required
def logout_user(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    if not request.user.has_permission('view_dashboard'):
        return HttpResponse('Forbidden', status=403)
    today = timezone.localdate()
    sales = Sale.objects.filter(created_at__date=today)
    cash_sales = sales.filter(payment_method__in=['cash', 'split']).aggregate(total=Sum('cash_amount'))['total'] or Decimal('0')
    online_sales = sales.aggregate(total=Sum('online_amount'))['total'] or Decimal('0')
    expenses = Expense.objects.filter(created_at__date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_sales = sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_profit = sales.aggregate(total=Sum('total_profit'))['total'] or Decimal('0')

    returned_sales = SaleReturn.objects.filter(is_cancelled=False, returned_at__date=today).select_related('sale', 'item')
    returned_total = Decimal('0')
    returned_cash = Decimal('0')
    returned_online = Decimal('0')
    for sale_return in returned_sales:
        returned_value = sale_return.item.unit_price * sale_return.quantity
        returned_total += returned_value
        if sale_return.item.quantity:
            total_profit -= (sale_return.item.profit / sale_return.item.quantity) * sale_return.quantity
        sale_total = sale_return.sale.total_amount
        if sale_total:
            returned_cash += returned_value * sale_return.sale.cash_amount / sale_total
            returned_online += returned_value * sale_return.sale.online_amount / sale_total

    total_sales = max(total_sales - returned_total, Decimal('0'))
    cash_sales = max(cash_sales - returned_cash, Decimal('0'))
    online_sales = max(online_sales - returned_online, Decimal('0'))
    deposit_amount = cash_sales - expenses
    
    context = {
        'total_sales': total_sales,
        'cash_sales': cash_sales,
        'online_sales': online_sales,
        'total_expenses': expenses,
        'deposit_amount': deposit_amount,
        'total_profit': max(total_profit, Decimal('0')),
        'can_view_profit': request.user.role == 'admin' or request.user.has_permission('view_profit'),
    }
    return render(request, 'posapp/dashboard.html', context)


@login_required
def products(request):
    if not any(request.user.has_permission(permission) for permission in (
        'view_products', 'add_product', 'edit_product', 'delete_product',
    )):
        return HttpResponse('Forbidden', status=403)
    queryset = Product.objects.all()
    category = request.GET.getlist('category')
    if category:
        queryset = queryset.filter(category__in=category)
    search = request.GET.get('q')
    if search:
        queryset = queryset.filter(
            Q(product_code__icontains=search)
            | Q(name__icontains=search)
            | Q(category__icontains=search)
            | Q(custom_category__icontains=search)
        )
    return render(request, 'posapp/products.html', {
        'products': queryset,
        'categories': Product.CATEGORY_CHOICES,
        'selected_categories': category,
        'can_edit_product': request.user.has_permission('edit_product'),
        'can_delete_product': request.user.has_permission('delete_product'),
    })


@login_required
def create_product(request):
    if request.user.role != 'admin' and not request.user.has_permission('add_product'):
        return HttpResponse('Forbidden', status=403)

    form = ProductForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        product = form.save(commit=False)
        product.save()
        
        from .models import ProductVariant
        
        # Handle variants if product has colors
        if product.has_color:
            colors_data = request.POST.getlist('color_name')
            
            # For each color, create variants with individual size quantities
            for color_index, color in enumerate(colors_data):
                if color:
                    # Get all sizes and quantities for this color
                    size_names = request.POST.getlist(f'size_name_{color_index}')
                    size_quantities = request.POST.getlist(f'size_quantity_{color_index}')
                    
                    # Create a variant for each size with its specific quantity
                    for size_name, size_qty in zip(size_names, size_quantities):
                        if size_name and size_qty:
                            try:
                                qty_val = int(size_qty)
                                ProductVariant.objects.get_or_create(
                                    product=product,
                                    color=color,
                                    size=size_name,
                                    defaults={'quantity': qty_val}
                                )
                            except (ValueError, TypeError):
                                pass
        else:
            # No color, just quantity
            qty = request.POST.get('product_quantity', 0)
            if qty:
                try:
                    qty_val = int(qty)
                    ProductVariant.objects.get_or_create(
                        product=product,
                        color=None,
                        size=None,
                        defaults={'quantity': qty_val}
                    )
                except (ValueError, TypeError):
                    pass
        
        messages.success(request, 'Product created successfully.')
        return redirect('products')
    return render(request, 'posapp/product_form.html', {'form': form, 'title': 'Create Product'})


@login_required
def edit_product(request, product_id):
    if request.user.role != 'admin' and not request.user.has_permission('edit_product'):
        return HttpResponse('Forbidden', status=403)

    product = Product.objects.get(pk=product_id)
    form = ProductForm(request.POST or None, instance=product, user=request.user)
    if request.method == 'POST' and form.is_valid():
        product = form.save(commit=False)
        product.save()
        
        # Clear existing variants
        product.variants.all().delete()
        
        from .models import ProductVariant
        
        # Handle variants if product has colors
        if product.has_color:
            colors_data = request.POST.getlist('color_name')
            
            # For each color, create variants with individual size quantities
            for color_index, color in enumerate(colors_data):
                if color:
                    # Get all sizes and quantities for this color
                    size_names = request.POST.getlist(f'size_name_{color_index}')
                    size_quantities = request.POST.getlist(f'size_quantity_{color_index}')
                    
                    # Create a variant for each size with its specific quantity
                    for size_name, size_qty in zip(size_names, size_quantities):
                        if size_name and size_qty:
                            try:
                                qty_val = int(size_qty)
                                ProductVariant.objects.create(
                                    product=product,
                                    color=color,
                                    size=size_name,
                                    quantity=qty_val
                                )
                            except (ValueError, TypeError):
                                pass
        else:
            # No color, just quantity
            qty = request.POST.get('product_quantity', 0)
            if qty:
                try:
                    qty_val = int(qty)
                    ProductVariant.objects.create(
                        product=product,
                        color=None,
                        size=None,
                        quantity=qty_val
                    )
                except (ValueError, TypeError):
                    pass
        
        messages.success(request, 'Product updated successfully.')
        return redirect('products')
    
    import json
    variants_json = json.dumps(list(product.variants.values('color', 'size', 'quantity'))) if product.pk else '[]'
    return render(request, 'posapp/product_form.html', {'form': form, 'title': 'Edit Product', 'product': product, 'variants_json': variants_json})


@login_required
def delete_product(request, product_id):
    if request.user.role != 'admin' and not request.user.has_permission('delete_product'):
        return HttpResponse('Forbidden', status=403)

    product = Product.objects.get(pk=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully.')
    return redirect('products')


@login_required
def stock(request):
    if not request.user.has_permission('view_stock'):
        return HttpResponse('Forbidden', status=403)
    items = Product.objects.prefetch_related('variants').all()
    
    # Search functionality
    search = request.GET.get('q', '')
    if search:
        items = items.filter(product_code__icontains=search) | items.filter(name__icontains=search)
    
    total_qty = sum(item.total_quantity for item in items)
    return render(request, 'posapp/stock.html', {
        'products': items,
        'grand_total_quantity': total_qty,
        'search_query': search,
        'can_add_sales': request.user.has_permission('add_sales'),
    })


@login_required
def create_sale(request):
    if request.user.role != 'admin' and not request.user.has_permission('add_sales'):
        return HttpResponse('Forbidden', status=403)

    products = Product.objects.prefetch_related('variants').all().order_by('product_code')
    product_data = [
        {
            'code': product.product_code,
            'name': product.name,
            'price': str(product.selling_price),
            'normal_discount_price': str(product.normal_discount_price),
            'special_discount_price': str(product.special_discount_price),
            'allow_custom_discount': product.allow_custom_discount,
            'cost_price': str(product.cost_price) if request.user.has_permission('view_cost_price') else None,
            'variants': [
                {'color': variant.color or '', 'size': variant.size or '', 'quantity': variant.quantity}
                for variant in product.variants.all()
            ],
        }
        for product in products
    ]

    products_json = json.dumps(product_data)

    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['product_code'].strip()
            product = Product.objects.filter(product_code__iexact=code).first()
            if not product:
                messages.error(request, 'Product code not found.')
                return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})

            quantity = form.cleaned_data['quantity']
            color = (form.cleaned_data.get('variant_color') or '').strip() or None
            size = (form.cleaned_data.get('variant_size') or '').strip() or None
            payment_method = form.cleaned_data['payment_method']
            online_amount = form.cleaned_data.get('online_amount') or Decimal('0')

            stock_variant = None
            if product.variants.exists():
                if color or size:
                    stock_variant = product.variants.filter(color=color or '', size=size or '').first()
                if stock_variant and quantity > stock_variant.quantity:
                    messages.error(request, f'Only {stock_variant.quantity} units available for this variant.')
                    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})
                if not stock_variant and (color or size):
                    messages.error(request, 'Selected variant is not available for this product.')
                    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})
                if not stock_variant and not (color or size):
                    messages.error(request, 'Please choose a variant for this product.')
                    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})
            elif quantity > product.total_quantity:
                messages.error(request, f'Only {product.total_quantity} units available for this product.')
                return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})

            discount_type = form.cleaned_data['discount_type']
            if discount_type == 'normal':
                unit_price = product.normal_discount_price or product.selling_price
            elif discount_type == 'special':
                unit_price = product.special_discount_price or product.normal_discount_price or product.selling_price
            elif discount_type == 'custom':
                unit_price = form.cleaned_data.get('custom_discount_price')
                if not product.allow_custom_discount:
                    form.add_error('discount_type', 'Custom discount is not enabled for this product.')
                    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})
                if unit_price is None or unit_price > product.selling_price:
                    form.add_error('custom_discount_price', 'Enter a custom price no greater than the selling price.')
                    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})
            else:
                unit_price = product.selling_price

            final_price = unit_price * quantity
            total_profit = (unit_price - product.cost_price) * quantity

            if payment_method == 'cash':
                cash_amount = final_price
                online_paid = Decimal('0')
            elif payment_method == 'online':
                cash_amount = Decimal('0')
                online_paid = final_price
            else:
                if online_amount <= 0:
                    messages.error(request, 'For split payment, enter the online amount.')
                    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})
                online_paid = online_amount
                cash_amount = final_price - online_paid
                if cash_amount < 0:
                    messages.error(request, 'Online amount cannot be greater than total sale value.')
                    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})

            sale = Sale.objects.create(
                invoice_no=f'SL-{timezone.localtime().strftime("%Y%m%d%H%M%S%f")}',
                agent=request.user,
                payment_method=payment_method,
                discount_type=discount_type,
                cash_amount=cash_amount,
                online_amount=online_paid,
                total_amount=final_price,
                total_profit=total_profit,
            )

            SaleItem.objects.create(
                sale=sale,
                product=product,
                color=color,
                size=size,
                quantity=quantity,
                discount_type=discount_type,
                unit_price=unit_price,
                final_price=final_price,
                profit=total_profit,
            )

            if stock_variant:
                stock_variant.quantity -= quantity
                stock_variant.save(update_fields=['quantity'])
            elif product.variants.exists():
                for variant in product.variants.all():
                    if (variant.color or '') == (color or '') and (variant.size or '') == (size or ''):
                        variant.quantity -= quantity
                        variant.save(update_fields=['quantity'])
                        break

            messages.success(request, 'Sale recorded successfully.')
            return redirect('sales')

        return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})

    form = SaleForm(initial={'product_code': request.GET.get('product_code', '')})
    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Add Sale'})


@login_required
def sales(request):
    if not any(request.user.has_permission(permission) for permission in (
        'view_own_sales_history', 'view_all_sales_history', 'add_sales', 'edit_sales', 'delete_sales', 'return_sales',
    )):
        return HttpResponse('Forbidden', status=403)
    today = timezone.localdate()
    selected_date = request.GET.get('date')
    
    if selected_date:
        try:
            selected_date = timezone.datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today
    
    sales_qs = Sale.objects.select_related('agent').prefetch_related('items__returns').filter(created_at__date=selected_date)
    if not request.user.has_permission('view_all_sales_history'):
        sales_qs = sales_qs.filter(agent=request.user)
    
    # Get daily totals
    daily_total = sales_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    daily_cash = sales_qs.aggregate(total=Sum('cash_amount'))['total'] or Decimal('0')
    daily_online = sales_qs.aggregate(total=Sum('online_amount'))['total'] or Decimal('0')
    
    context = {
        'sales': sales_qs,
        'selected_date': selected_date.isoformat(),
        'daily_total': daily_total,
        'daily_cash': daily_cash,
        'daily_online': daily_online,
        'can_view_profit': request.user.has_permission('view_profit'),
        'can_add_sales': request.user.has_permission('add_sales'),
    }
    return render(request, 'posapp/sales.html', context)


@login_required
def create_expense(request):
    if request.user.role != 'admin' and not request.user.has_permission('add_expense'):
        return HttpResponse('Forbidden', status=403)

    form = ExpenseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        expense = form.save(commit=False)
        expense.agent = request.user
        expense.save()
        messages.success(request, 'Expense added successfully.')
        return redirect('expenses')
    return render(request, 'posapp/expense_form.html', {'form': form, 'title': 'Add Expense'})


@login_required
def expenses(request):
    if not any(request.user.has_permission(permission) for permission in (
        'view_own_expense_history', 'view_all_expense_history', 'add_expense', 'edit_expense', 'delete_expense',
    )):
        return HttpResponse('Forbidden', status=403)
    today = timezone.localdate()
    selected_date = request.GET.get('date')
    
    if selected_date:
        try:
            selected_date = timezone.datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today
    
    expenses_qs = Expense.objects.select_related('agent').filter(created_at__date=selected_date)
    if not request.user.has_permission('view_all_expense_history'):
        expenses_qs = expenses_qs.filter(agent=request.user)
    
    # Get daily total
    daily_total = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    context = {
        'expenses': expenses_qs,
        'selected_date': selected_date.isoformat(),
        'daily_total': daily_total,
        'can_add_expense': request.user.has_permission('add_expense'),
    }
    return render(request, 'posapp/expenses.html', context)


@login_required
def reports(request):
    if not request.user.has_permission('view_reports'):
        return HttpResponse('Forbidden', status=403)
    report_type = request.GET.get('report_type', 'sales')
    date_range = 'custom'
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = timezone.localdate()
    if start_date and end_date:
        start = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        end = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        start = today
        end = today

    sales_qs = Sale.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
    expenses_qs = Expense.objects.filter(created_at__date__gte=start, created_at__date__lte=end)

    total_sales = sales_qs.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_profit = sales_qs.aggregate(total=Sum('total_profit'))['total'] or Decimal('0')
    ledger = []
    ledger_date = start
    while ledger_date <= end:
        day_sales = Sale.objects.filter(created_at__date=ledger_date)
        day_expenses = Expense.objects.filter(created_at__date=ledger_date)
        day_returns = SaleReturn.objects.filter(is_cancelled=False, returned_at__date=ledger_date).select_related('sale', 'item')

        gross_sales = day_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        cash_sales = day_sales.aggregate(total=Sum('cash_amount'))['total'] or Decimal('0')
        online_sales = day_sales.aggregate(total=Sum('online_amount'))['total'] or Decimal('0')
        total_expense = day_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        sold_quantity = SaleItem.objects.filter(sale__created_at__date=ledger_date).aggregate(total=Sum('quantity'))['total'] or 0
        returned_quantity = day_returns.aggregate(total=Sum('quantity'))['total'] or 0
        returned_total = Decimal('0')
        returned_cash = Decimal('0')
        returned_online = Decimal('0')
        returned_profit = Decimal('0')
        for sale_return in day_returns:
            returned_value = sale_return.item.unit_price * sale_return.quantity
            returned_total += returned_value
            if sale_return.item.quantity:
                returned_profit += (sale_return.item.profit / sale_return.item.quantity) * sale_return.quantity
            if sale_return.sale.total_amount:
                returned_cash += returned_value * sale_return.sale.cash_amount / sale_return.sale.total_amount
                returned_online += returned_value * sale_return.sale.online_amount / sale_return.sale.total_amount

        net_sales = max(gross_sales - returned_total, Decimal('0'))
        net_cash = max(cash_sales - returned_cash, Decimal('0'))
        net_online = max(online_sales - returned_online, Decimal('0'))
        ledger.append({
            'date': ledger_date,
            'total_sales': net_sales,
            'total_cash': net_cash,
            'total_online': net_online,
            'total_expense': total_expense,
            'deposit': net_cash - total_expense,
            'sold_quantity': sold_quantity,
            'returned_quantity': returned_quantity,
            'net_quantity': max(sold_quantity - returned_quantity, 0),
            'profit': max((day_sales.aggregate(total=Sum('total_profit'))['total'] or Decimal('0')) - returned_profit, Decimal('0')),
        })
        ledger_date += timezone.timedelta(days=1)

    total_profit = sum((row['profit'] for row in ledger), Decimal('0'))

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="fashion99-ledger-{start}-to-{end}.csv"'
        writer = csv.writer(response)
        headers = ['Date', 'Total Sales', 'Total Cash', 'Total Online', 'Total Expense', 'Amount to Deposit', 'Sold Quantity', 'Returned Quantity', 'Net Quantity']
        if request.user.role == 'admin' or request.user.has_permission('view_profit'):
            headers.insert(8, 'Profit')
        writer.writerow(headers)
        for row in ledger:
            values = [
                row['date'].isoformat(), row['total_sales'], row['total_cash'], row['total_online'],
                row['total_expense'], row['deposit'], row['sold_quantity'], row['returned_quantity'], row['net_quantity'],
            ]
            if request.user.role == 'admin' or request.user.has_permission('view_profit'):
                values.insert(5, row['profit'])
            writer.writerow(values)
        return response

    context = {
        'report_type': report_type,
        'date_range': date_range,
        'start_date': start_date or start.isoformat(),
        'end_date': end_date or end.isoformat(),
        'reports': [],
        'total_sales': total_sales,
        'total_expenses': total_expenses,
        'total_profit': total_profit,
        'ledger': ledger,
        'can_view_profit': request.user.role == 'admin' or request.user.has_permission('view_profit'),
    }
    return render(request, 'posapp/reports.html', context)


@login_required
def accounts(request):
    if request.user.role != 'admin':
        return HttpResponse('Forbidden', status=403)
    users = CustomUser.objects.all().order_by('username')
    return render(request, 'posapp/accounts.html', {'users': users})


@login_required
def create_account(request):
    if request.user.role != 'admin':
        return HttpResponse('Forbidden', status=403)

    form = UserAccountForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('accounts')
    return render(request, 'posapp/account_form.html', {'form': form, 'title': 'Create Account'})


@login_required
def edit_account(request, user_id):
    target = CustomUser.objects.get(pk=user_id)
    if request.user.role != 'admin' and request.user.pk != target.pk:
        return HttpResponse('Forbidden', status=403)

    form = UserAccountForm(request.POST or None, instance=target, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('accounts')
    return render(request, 'posapp/account_form.html', {'form': form, 'title': 'Edit Account', 'user_obj': target})


@login_required
def reset_account_password(request, user_id):
    if request.user.role != 'admin':
        return HttpResponse('Forbidden', status=403)

    target = get_object_or_404(CustomUser, pk=user_id)
    form = PasswordResetForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        target.set_password(form.cleaned_data['new_password'])
        target.save(update_fields=['password'])
        messages.success(request, f'Password reset for {target.username}.')
        return redirect('accounts')
    return render(request, 'posapp/password_reset.html', {'form': form, 'user_obj': target})


@login_required
def delete_account(request, user_id):
    if request.user.role != 'admin':
        return HttpResponse('Forbidden', status=403)
    if request.user.pk == user_id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('accounts')
    user = CustomUser.objects.get(pk=user_id)
    user.delete()
    return redirect('accounts')


@login_required
def delete_sale(request, sale_id):
    if request.user.role != 'admin' and not request.user.has_permission('delete_sales'):
        return HttpResponse('Forbidden', status=403)
    
    sale = Sale.objects.get(pk=sale_id)
    
    # Restore stock
    for item in sale.items.all():
        if item.color or item.size:
            variant = item.product.variants.filter(color=item.color or '', size=item.size or '').first()
            if variant:
                variant.quantity += item.quantity
                variant.save(update_fields=['quantity'])
    
    sale.delete()
    messages.success(request, 'Sale deleted successfully.')
    return redirect('sales')
@login_required
def edit_sale(request, sale_id):
    if request.user.role != 'admin' and not request.user.has_permission('edit_sales'):
        return HttpResponse('Forbidden', status=403)
    
    sale = get_object_or_404(Sale.objects.prefetch_related('items'), pk=sale_id)
    sale_item = sale.items.first()
    if not sale_item:
        messages.error(request, 'This sale has no item to edit.')
        return redirect('sales')

    products = Product.objects.prefetch_related('variants').all()
    product_data = []
    for product in products:
        product_data.append({
            'code': product.product_code,
            'name': product.name,
            'price': str(product.selling_price),
            'normal_discount_price': str(product.normal_discount_price),
            'special_discount_price': str(product.special_discount_price),
            'allow_custom_discount': product.allow_custom_discount,
            'cost_price': str(product.cost_price) if request.user.has_permission('view_cost_price') else None,
            'variants': list(product.variants.values('color', 'size', 'quantity')),
        })
    products_json = json.dumps(product_data)
    
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            if quantity > sale_item.quantity:
                messages.error(request, 'Edited quantity cannot exceed the original quantity.')
                return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Edit Sale', 'sale': sale})

            product = sale_item.product
            discount_type = form.cleaned_data['discount_type']
            if discount_type == 'normal':
                unit_price = product.normal_discount_price or product.selling_price
            elif discount_type == 'special':
                unit_price = product.special_discount_price or product.normal_discount_price or product.selling_price
            elif discount_type == 'custom':
                unit_price = form.cleaned_data.get('custom_discount_price')
                if not product.allow_custom_discount:
                    form.add_error('discount_type', 'Custom discount is not enabled for this product.')
                    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Edit Sale', 'sale': sale})
                if unit_price is None or unit_price > product.selling_price:
                    form.add_error('custom_discount_price', 'Enter a custom price no greater than the selling price.')
                    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Edit Sale', 'sale': sale})
            else:
                unit_price = product.selling_price

            total_amount = unit_price * quantity
            payment_method = form.cleaned_data['payment_method']
            online_amount = form.cleaned_data.get('online_amount') or Decimal('0')
            if payment_method == 'cash':
                cash_amount, online_amount = total_amount, Decimal('0')
            elif payment_method == 'online':
                cash_amount = Decimal('0')
                online_amount = total_amount
            else:
                if online_amount > total_amount:
                    form.add_error('online_amount', 'Online amount cannot exceed the sale total.')
                    return render(request, 'posapp/sale_form.html', {'form': form, 'products': product_data, 'products_json': products_json, 'title': 'Edit Sale', 'sale': sale})
                cash_amount = total_amount - online_amount

            sale.payment_method = payment_method
            sale.discount_type = discount_type
            sale.cash_amount = cash_amount
            sale.online_amount = online_amount
            sale.total_amount = total_amount
            sale.total_profit = (unit_price - product.cost_price) * quantity
            sale.save(update_fields=['payment_method', 'discount_type', 'cash_amount', 'online_amount', 'total_amount', 'total_profit'])

            sale_item.quantity = quantity
            sale_item.discount_type = discount_type
            sale_item.unit_price = unit_price
            sale_item.final_price = total_amount
            sale_item.profit = sale.total_profit
            sale_item.save(update_fields=['quantity', 'discount_type', 'unit_price', 'final_price', 'profit'])
            messages.success(request, 'Sale updated successfully.')
            return redirect('sales')

        return render(request, 'posapp/sale_form.html', {
            'form': form,
            'products': product_data,
            'products_json': products_json,
            'title': 'Edit Sale',
            'sale': sale,
        })
    
    # Create a simple form with initial values
    form = SaleForm(initial={
        'product_code': sale_item.product.product_code,
        'quantity': sale_item.quantity,
        'variant_color': sale_item.color or '',
        'variant_size': sale_item.size or '',
        'payment_method': sale.payment_method,
        'discount_type': sale.discount_type,
        'custom_discount_price': sale_item.unit_price if sale_item.discount_type == 'custom' else None,
        'online_amount': sale.online_amount,
    })
    
    context = {
        'form': form,
        'products': product_data,
        'products_json': products_json,
        'title': 'Edit Sale',
        'sale': sale,
    }
    return render(request, 'posapp/sale_form.html', context)


@login_required
def edit_expense(request, expense_id):
    if request.user.role != 'admin' and not request.user.has_permission('edit_expense'):
        return HttpResponse('Forbidden', status=403)
    
    expense = Expense.objects.get(pk=expense_id)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully.')
            return redirect('expenses')
    else:
        form = ExpenseForm(instance=expense)
    
    return render(request, 'posapp/expense_form.html', {'form': form, 'title': 'Edit Expense'})


@login_required
def delete_expense(request, expense_id):
    if request.user.role != 'admin' and not request.user.has_permission('delete_expense'):
        return HttpResponse('Forbidden', status=403)
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    expense = get_object_or_404(Expense, pk=expense_id)
    expense.delete()
    messages.success(request, 'Expense deleted successfully.')
    return redirect('expenses')



@login_required
def return_sale(request, sale_id):
    if request.user.role != 'admin' and not request.user.has_permission('return_sales'):
        return HttpResponse('Forbidden', status=403)
    
    sale = get_object_or_404(Sale.objects.prefetch_related('items__returns'), pk=sale_id)
    
    if request.method == 'POST':
        with transaction.atomic():
            for item in sale.items.all():
                try:
                    quantity = int(request.POST.get(f'quantity_{item.id}', 0))
                except (TypeError, ValueError):
                    quantity = 0
                reason = request.POST.get(f'reason_{item.id}', '').strip()
                remaining_quantity = item.remaining_quantity
            
                if quantity < 0 or quantity > remaining_quantity:
                    messages.error(request, f'Return quantity for {item.product.name} cannot exceed {remaining_quantity}.')
                    return render(request, 'posapp/return_sale.html', {'sale': sale, 'items': sale.items.all()})
                
                if quantity > 0:
                    SaleReturn.objects.create(
                        sale=sale,
                        item=item,
                        quantity=quantity,
                        reason=reason,
                    )
                    
                    variant = item.product.variants.filter(color=item.color or '', size=item.size or '').first()
                    if variant:
                        variant.quantity += quantity
                        variant.save(update_fields=['quantity'])
        
        messages.success(request, 'Return recorded successfully.')
        return redirect('sales')
    
    context = {
        'sale': sale,
        'items': sale.items.all(),
    }
    return render(request, 'posapp/return_sale.html', context)


@login_required
def sale_returns(request):
    if request.user.role != 'admin' and not request.user.has_permission('view_return_notifications'):
        return HttpResponse('Forbidden', status=403)
    
    returns = SaleReturn.objects.select_related('sale', 'item__product').all().order_by('-returned_at')
    
    context = {
        'returns': returns,
        'can_cancel_returned_products': request.user.has_permission('cancel_returned_products'),
    }
    return render(request, 'posapp/sale_returns.html', context)


@login_required
def cancel_return(request, return_id):
    if not request.user.has_permission('cancel_returned_products'):
        return HttpResponse('Forbidden', status=403)
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    sale_return = get_object_or_404(
        SaleReturn.objects.filter(is_cancelled=False).select_related('item__product'),
        pk=return_id,
    )
    variant = sale_return.item.product.variants.filter(
        color=sale_return.item.color,
        size=sale_return.item.size,
    ).first()
    if not variant:
        variant = sale_return.item.product.variants.filter(
            color=sale_return.item.color or None,
            size=sale_return.item.size or None,
        ).first()
    if not variant or variant.quantity < sale_return.quantity:
        messages.error(request, 'This returned product cannot be cancelled because its stock has changed.')
        return redirect('sale_returns' if request.GET.get('next') == 'returns' else 'reports')

    with transaction.atomic():
        variant.quantity -= sale_return.quantity
        variant.save(update_fields=['quantity'])
        sale_return.is_cancelled = True
        sale_return.save(update_fields=['is_cancelled'])

    messages.success(request, 'Returned product cancellation completed.')
    return redirect('sale_returns' if request.GET.get('next') == 'returns' else 'reports')
