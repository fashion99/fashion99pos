from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('staff', 'Staff'),
    )
    PORTAL_CHOICES = (
        ('dashboard', 'Dashboard'),
        ('products', 'Products'),
        ('stock', 'Stock'),
        ('sales', 'Sales'),
        ('expenses', 'Expenses'),
        ('reports', 'Reports'),
        ('sale_returns', 'Return Log'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    full_name = models.CharField(max_length=150, blank=True)
    default_portal = models.CharField(max_length=30, choices=PORTAL_CHOICES, blank=True, default='')
    view_dashboard = models.BooleanField(default=False)
    add_sales = models.BooleanField(default=False)
    add_expense = models.BooleanField(default=False)
    add_product = models.BooleanField(default=False)
    edit_product = models.BooleanField(default=False)
    delete_product = models.BooleanField(default=False)
    edit_expense = models.BooleanField(default=False)
    delete_expense = models.BooleanField(default=False)
    edit_sales = models.BooleanField(default=False)
    delete_sales = models.BooleanField(default=False)
    return_sales = models.BooleanField(default=False)
    cancel_returned_products = models.BooleanField(default=False)
    view_cost_price = models.BooleanField(default=False)
    view_profit = models.BooleanField(default=False)
    view_products = models.BooleanField(default=False)
    view_stock = models.BooleanField(default=False)
    view_today_calculations = models.BooleanField(default=False)
    view_reports = models.BooleanField(default=False)
    view_return_notifications = models.BooleanField(default=False)
    view_all_sales_history = models.BooleanField(default=False)
    view_own_sales_history = models.BooleanField(default=False)
    view_all_expense_history = models.BooleanField(default=False)
    view_own_expense_history = models.BooleanField(default=False)

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_admin(self):
        return self.role == 'admin'

    def has_permission(self, permission_name):
        if self.is_admin:
            return True
        return bool(getattr(self, permission_name, False))

    @property
    def display_name(self):
        return self.get_full_name() or self.username


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_custom = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Product(models.Model):
    CATEGORY_CHOICES = (
        ('2pcs', '2pcs'),
        ('3pcs', '3pcs'),
        ('Top', 'Top'),
        ('Bottom', 'Bottom'),
        ('Other', 'Other'),
    )

    product_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    custom_category = models.CharField(max_length=100, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    normal_discount_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    special_discount_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allow_custom_discount = models.BooleanField(default=False)
    has_color = models.BooleanField(default=False)
    has_size = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product_code']

    def __str__(self):
        return f'{self.product_code} - {self.name}'

    @property
    def display_category(self):
        return self.custom_category or self.category

    @property
    def total_quantity(self):
        return sum(v.quantity for v in self.variants.all())

    def can_edit(self):
        return True


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    color = models.CharField(max_length=100, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'color', 'size')
        ordering = ['product__product_code', 'color', 'size']

    def __str__(self):
        return f'{self.product.product_code} / {self.color or "No Color"} / {self.size or "No Size"} / {self.quantity}'

    @property
    def label(self):
        return f'{self.color or "No Color"} - {self.size or "No Size"}'


class Expense(models.Model):
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    purpose = models.CharField(max_length=255)
    agent = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.amount} - {self.purpose}'


class Sale(models.Model):
    DISCOUNT_CHOICES = (
        ('none', 'No Discount'),
        ('normal', 'Normal Discount'),
        ('special', 'Special Discount'),
        ('custom', 'Custom Discount'),
    )
    PAYMENT_CHOICES = (
        ('cash', 'Cash'),
        ('online', 'Online'),
        ('split', 'Split'),
    )

    invoice_no = models.CharField(max_length=50, unique=True, blank=True)
    agent = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_CHOICES, default='none')
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    online_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.invoice_no or f'Sale-{self.pk}'

    @property
    def sale_date(self):
        return self.created_at.date()

    @property
    def has_returns(self):
        return self.returns.filter(is_cancelled=False).exists()

    @property
    def is_fully_returned(self):
        items = list(self.items.all())
        return bool(items) and all(item.is_fully_returned for item in items)

    @property
    def profit_per_unit(self):
        quantity = sum(item.quantity for item in self.items.all())
        return self.total_profit / quantity if quantity else 0


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    color = models.CharField(max_length=100, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    discount_type = models.CharField(max_length=20, default='none')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.product.product_code} x {self.quantity}'

    @property
    def returned_quantity(self):
        return sum(return_item.quantity for return_item in self.returns.filter(is_cancelled=False))

    @property
    def remaining_quantity(self):
        return max(self.quantity - self.returned_quantity, 0)

    @property
    def is_fully_returned(self):
        return self.returned_quantity >= self.quantity


class SaleReturn(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')
    item = models.ForeignKey(SaleItem, on_delete=models.CASCADE, related_name='returns')
    quantity = models.PositiveIntegerField(default=1)
    reason = models.CharField(max_length=255, blank=True)
    returned_at = models.DateTimeField(default=timezone.now)
    is_cancelled = models.BooleanField(default=False)

    def __str__(self):
        return f'Return for {self.sale.invoice_no}'
