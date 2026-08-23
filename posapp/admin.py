from django.contrib import admin

from .models import (
    CustomUser,
    Expense,
    Product,
    ProductVariant,
    Sale,
    SaleItem,
    SaleReturn,
)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_code', 'name', 'category', 'selling_price')
    search_fields = ('product_code', 'name')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'color', 'size', 'quantity')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('amount', 'purpose', 'agent', 'created_at')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'agent', 'payment_method', 'total_amount', 'created_at')


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'final_price')


@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display = ('sale', 'item', 'quantity', 'returned_at')
