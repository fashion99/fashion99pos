from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('protected-root/', views.protected_root, name='protected_root'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('products/', views.products, name='products'),
    path('products/create/', views.create_product, name='create_product'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('stock/', views.stock, name='stock'),
    path('sales/', views.sales, name='sales'),
    path('sales/create/', views.create_sale, name='create_sale'),
    path('sales/<int:sale_id>/edit/', views.edit_sale, name='edit_sale'),
    path('sales/<int:sale_id>/delete/', views.delete_sale, name='delete_sale'),
    path('sales/<int:sale_id>/return/', views.return_sale, name='return_sale'),
    path('returns/', views.sale_returns, name='sale_returns'),
    path('returns/<int:return_id>/cancel/', views.cancel_return, name='cancel_return'),
    path('expenses/<int:expense_id>/edit/', views.edit_expense, name='edit_expense'),
    path('expenses/<int:expense_id>/delete/', views.delete_expense, name='delete_expense'),
    path('expenses/', views.expenses, name='expenses'),
    path('expenses/create/', views.create_expense, name='create_expense'),
    path('reports/', views.reports, name='reports'),
    path('accounts/', views.accounts, name='accounts'),
    path('accounts/create/', views.create_account, name='create_account'),
    path('accounts/<int:user_id>/edit/', views.edit_account, name='edit_account'),
    path('accounts/<int:user_id>/password-reset/', views.reset_account_password, name='reset_account_password'),
    path('accounts/<int:user_id>/delete/', views.delete_account, name='delete_account'),
]
