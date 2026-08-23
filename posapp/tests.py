from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .forms import UserAccountForm
from .models import Expense, Product, ProductVariant, Sale, SaleItem, SaleReturn


class PosBackendTests(TestCase):
    def test_staff_can_log_in_with_account_password(self):
        get_user_model().objects.create_user(
            username='staff-login',
            password='staff-secret',
            role='staff',
            view_dashboard=True,
        )

        response = self.client.post('/login/', {
            'username': 'staff-login',
            'password': 'staff-secret',
        })

        self.assertRedirects(response, '/dashboard/')
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_account_default_portal_controls_login_destination(self):
        get_user_model().objects.create_user(
            username='staff-default-portal',
            password='staff-secret',
            role='staff',
            view_reports=True,
            default_portal='reports',
        )

        response = self.client.post('/login/', {
            'username': 'staff-default-portal',
            'password': 'staff-secret',
        })

        self.assertRedirects(response, '/reports/')

    def test_staff_without_portal_permissions_cannot_open_portals(self):
        staff = get_user_model().objects.create_user(
            username='staff-no-portals',
            password='secret123',
            role='staff',
        )
        self.client.force_login(staff)

        for path in ('/products/', '/stock/', '/sales/', '/expenses/', '/reports/', '/returns/'):
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_delete_permission_is_separate_from_edit_permission(self):
        staff = get_user_model().objects.create_user(
            username='staff-delete-only',
            password='secret123',
            role='staff',
            view_products=True,
            delete_product=True,
        )
        product = Product.objects.create(product_code='F99-DELETE-ONLY', name='Delete Only', category='Top')
        self.client.force_login(staff)

        response = self.client.get('/products/')

        self.assertContains(response, 'Delete')
        self.assertNotContains(response, 'href="/products/%s/edit/"' % product.pk)

    def test_account_form_password_allows_staff_login(self):
        form = UserAccountForm(data={
            'username': 'staff-from-form',
            'full_name': 'Form Staff',
            'email': 'form-staff@example.com',
            'employee_id': 'FORM-001',
            'role': 'staff',
            'password': 'form-secret',
        })

        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(self.client.login(username='staff-from-form', password='form-secret'))

    def test_admin_can_reset_account_password(self):
        admin = get_user_model().objects.create_user(
            username='password-reset-admin',
            password='admin-secret',
            role='admin',
        )
        target = get_user_model().objects.create_user(
            username='password-reset-target',
            password='old-secret',
            role='staff',
        )
        self.client.force_login(admin)

        response = self.client.post(f'/accounts/{target.pk}/password-reset/', {
            'new_password': 'new-secret-123',
            'confirm_password': 'new-secret-123',
        })

        self.assertRedirects(response, '/accounts/')
        self.assertTrue(self.client.login(username=target.username, password='new-secret-123'))

    def test_edit_account_blank_password_preserves_existing_password(self):
        user = get_user_model().objects.create_user(
            username='preserve-password',
            password='original-secret',
            role='staff',
        )
        form = UserAccountForm(
            data={
                'username': user.username,
                'full_name': 'Updated Name',
                'email': '',
                'employee_id': '',
                'role': 'staff',
                'default_portal': '',
                'password': '',
            },
            instance=user,
        )

        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(self.client.login(username=user.username, password='original-secret'))

    def test_account_settings_does_not_include_password_field(self):
        user = get_user_model().objects.create_user(
            username='settings-no-password',
            password='secret123',
            role='staff',
        )
        form = UserAccountForm(instance=user)
        self.assertNotIn('password', form.fields)

    def test_edit_account_view_blank_password_preserves_existing_password(self):
        admin = get_user_model().objects.create_user(
            username='account-edit-admin',
            password='admin-secret',
            role='admin',
        )
        target = get_user_model().objects.create_user(
            username='account-edit-target',
            password='target-secret',
            role='staff',
        )
        self.client.force_login(admin)

        response = self.client.post(f'/accounts/{target.pk}/edit/', {
            'username': target.username,
            'full_name': target.full_name,
            'email': target.email,
            'employee_id': '',
            'role': 'staff',
            'default_portal': '',
            'password': '',
        })

        self.assertRedirects(response, '/accounts/')
        self.assertTrue(self.client.login(username=target.username, password='target-secret'))

    def test_user_role_and_product_creation(self):
        user = get_user_model().objects.create_user(
            username='admin1',
            password='secret123',
            role='admin',
            full_name='Admin One',
        )

        self.assertEqual(user.role, 'admin')
        self.assertTrue(user.is_admin)

        product = Product.objects.create(
            product_code='F99-001',
            name='Classic Tee',
            category='Top',
            cost_price=180.00,
            selling_price=350.00,
            normal_discount_price=320.00,
            special_discount_price=280.00,
            has_color=True,
            has_size=True,
        )

        self.assertEqual(product.product_code, 'F99-001')
        self.assertEqual(product.display_category, 'Top')
        self.assertTrue(product.can_edit())

    def test_account_create_form_requires_password(self):
        form = UserAccountForm(data={
            'username': 'staff01',
            'full_name': 'Staff One',
            'email': 'staff01@example.com',
            'employee_id': 'EMP-001',
            'role': 'staff',
            'password': '',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

    def test_sale_uses_discount_price_when_discount_selected(self):
        admin = get_user_model().objects.create_user(
            username='admin2',
            password='secret123',
            role='admin',
            full_name='Admin Two',
        )
        product = Product.objects.create(
            product_code='F99-100',
            name='Discount Tee',
            category='Top',
            cost_price=120.00,
            selling_price=500.00,
            normal_discount_price=420.00,
            special_discount_price=350.00,
            has_color=True,
            has_size=True,
        )
        product.variants.create(color='Red', size='M', quantity=10)

        self.client.force_login(admin)
        response = self.client.post('/sales/create/', {
            'product_code': 'F99-100',
            'variant_color': 'Red',
            'variant_size': 'M',
            'quantity': 2,
            'payment_method': 'split',
            'discount_type': 'normal',
            'online_amount': '200.00',
        })

        self.assertEqual(response.status_code, 302)
        sale = Sale.objects.get()
        self.assertEqual(sale.total_amount, Decimal('840.00'))
        self.assertEqual(sale.cash_amount, Decimal('640.00'))
        self.assertEqual(sale.online_amount, Decimal('200.00'))

    def test_sale_uses_custom_discount_price_only_when_product_allows_it(self):
        admin = get_user_model().objects.create_user(
            username='admin-custom-discount',
            password='secret123',
            role='admin',
        )
        product = Product.objects.create(
            product_code='F99-CUSTOM-DISCOUNT',
            name='Custom Discount Tee',
            category='Top',
            cost_price=100,
            selling_price=500,
            allow_custom_discount=True,
        )
        product.variants.create(color='Red', size='M', quantity=5)
        self.client.force_login(admin)

        response = self.client.post('/sales/create/', {
            'product_code': 'F99-CUSTOM-DISCOUNT',
            'variant_color': 'Red',
            'variant_size': 'M',
            'quantity': 2,
            'payment_method': 'cash',
            'discount_type': 'custom',
            'custom_discount_price': '275.00',
            'online_amount': '0',
        })

        self.assertEqual(response.status_code, 302)
        sale = Sale.objects.get()
        self.assertEqual(sale.total_amount, Decimal('550.00'))
        self.assertEqual(sale.total_profit, Decimal('350.00'))

        product.allow_custom_discount = False
        product.save(update_fields=['allow_custom_discount'])
        response = self.client.post('/sales/create/', {
            'product_code': 'F99-CUSTOM-DISCOUNT',
            'variant_color': 'Red',
            'variant_size': 'M',
            'quantity': 1,
            'payment_method': 'cash',
            'discount_type': 'custom',
            'custom_discount_price': '250.00',
            'online_amount': '0',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Sale.objects.count(), 1)

    def test_authorized_user_can_edit_sale(self):
        admin = get_user_model().objects.create_user(
            username='admin-edit-sale',
            password='secret123',
            role='admin',
        )
        product = Product.objects.create(
            product_code='F99-EDIT',
            name='Editable Tee',
            category='Top',
            cost_price=100,
            selling_price=300,
            normal_discount_price=250,
        )
        ProductVariant.objects.create(product=product, color='Red', size='M', quantity=5)
        sale = Sale.objects.create(
            invoice_no='SL-EDIT',
            agent=admin,
            total_amount=300,
            cash_amount=300,
        )
        SaleItem.objects.create(
            sale=sale,
            product=product,
            color='Red',
            size='M',
            quantity=1,
            unit_price=300,
            final_price=300,
            profit=200,
        )
        self.client.force_login(admin)

        self.assertEqual(self.client.get(f'/sales/{sale.pk}/edit/').status_code, 200)
        response = self.client.post(f'/sales/{sale.pk}/edit/', {
            'product_code': product.product_code,
            'variant_color': 'Red',
            'variant_size': 'M',
            'quantity': 1,
            'payment_method': 'online',
            'discount_type': 'normal',
            'online_amount': '0',
        })

        self.assertRedirects(response, '/sales/')
        sale.refresh_from_db()
        self.assertEqual(sale.total_amount, Decimal('250.00'))
        self.assertEqual(sale.online_amount, Decimal('250.00'))

    def test_authorized_user_can_edit_expense(self):
        admin = get_user_model().objects.create_user(
            username='admin-edit-expense',
            password='secret123',
            role='admin',
        )
        expense = Expense.objects.create(amount=100, purpose='Old purpose', agent=admin)
        self.client.force_login(admin)

        self.assertEqual(self.client.get(f'/expenses/{expense.pk}/edit/').status_code, 200)
        response = self.client.post(f'/expenses/{expense.pk}/edit/', {
            'amount': '125.50',
            'purpose': 'Updated purpose',
        })

        self.assertRedirects(response, '/expenses/')
        expense.refresh_from_db()
        self.assertEqual(expense.amount, Decimal('125.50'))
        self.assertEqual(expense.purpose, 'Updated purpose')

    def test_return_restores_stock_and_appears_in_return_log(self):
        admin = get_user_model().objects.create_user(
            username='admin-return',
            password='secret123',
            role='admin',
        )
        product = Product.objects.create(
            product_code='F99-RETURN',
            name='Returnable Tee',
            category='Top',
            cost_price=100,
            selling_price=300,
        )
        variant = ProductVariant.objects.create(product=product, color='Blue', size='L', quantity=3)
        sale = Sale.objects.create(invoice_no='SL-RETURN', agent=admin, total_amount=300, cash_amount=300)
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            color='Blue',
            size='L',
            quantity=1,
            unit_price=300,
            final_price=300,
            profit=200,
        )
        variant.quantity = 2
        variant.save(update_fields=['quantity'])
        self.client.force_login(admin)

        response = self.client.post(f'/sales/{sale.pk}/return/', {
            f'quantity_{item.pk}': '1',
            f'reason_{item.pk}': 'Wrong size',
        })

        self.assertRedirects(response, '/sales/')
        variant.refresh_from_db()
        self.assertEqual(variant.quantity, 3)
        self.assertEqual(sale.returns.get().quantity, 1)
        self.assertEqual(self.client.get('/returns/').status_code, 200)

        duplicate = self.client.post(f'/sales/{sale.pk}/return/', {
            f'quantity_{item.pk}': '1',
        })
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(sale.returns.count(), 1)

    def test_return_log_requires_permission_for_staff(self):
        staff = get_user_model().objects.create_user(
            username='staff-no-return-log',
            password='secret123',
            role='staff',
        )
        self.client.force_login(staff)
        self.assertEqual(self.client.get('/returns/').status_code, 403)

    def test_cancel_return_requires_permission_and_reverses_stock(self):
        staff = get_user_model().objects.create_user(
            username='staff-no-cancel-return',
            password='secret123',
            role='staff',
        )
        product = Product.objects.create(
            product_code='F99-CANCEL-RETURN',
            name='Cancellable Return Tee',
            category='Top',
        )
        variant = ProductVariant.objects.create(product=product, quantity=4)
        sale = Sale.objects.create(invoice_no='SL-CANCEL-RETURN', agent=staff)
        item = SaleItem.objects.create(sale=sale, product=product, quantity=1)
        sale_return = SaleReturn.objects.create(sale=sale, item=item, quantity=1)

        self.client.force_login(staff)
        self.assertEqual(self.client.post(f'/returns/{sale_return.pk}/cancel/').status_code, 403)

        staff.cancel_returned_products = True
        staff.view_return_notifications = True
        staff.save(update_fields=['cancel_returned_products', 'view_return_notifications'])
        response = self.client.post(f'/returns/{sale_return.pk}/cancel/?next=returns')

        self.assertRedirects(response, '/returns/')
        sale_return.refresh_from_db()
        self.assertTrue(sale_return.is_cancelled)
        variant.refresh_from_db()
        self.assertEqual(variant.quantity, 3)

    def test_dashboard_deducts_returned_sale_value(self):
        admin = get_user_model().objects.create_user(
            username='admin-dashboard-return',
            password='secret123',
            role='admin',
        )
        product = Product.objects.create(
            product_code='F99-DASH-RETURN',
            name='Dashboard Return Tee',
            category='Top',
            cost_price=50,
            selling_price=200,
        )
        sale = Sale.objects.create(
            invoice_no='SL-DASH-RETURN',
            agent=admin,
            payment_method='cash',
            total_amount=400,
            cash_amount=400,
        )
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=2,
            unit_price=200,
            final_price=400,
            profit=300,
        )
        SaleReturn.objects.create(sale=sale, item=item, quantity=1)
        self.client.force_login(admin)

        response = self.client.get('/dashboard/')

        self.assertEqual(response.context['total_sales'], Decimal('200'))
        self.assertEqual(response.context['cash_sales'], Decimal('200'))
        self.assertEqual(response.context['deposit_amount'], Decimal('200'))

    def test_reports_daily_ledger_and_csv_export(self):
        admin = get_user_model().objects.create_user(
            username='admin-ledger',
            password='secret123',
            role='admin',
        )
        product = Product.objects.create(
            product_code='F99-LEDGER',
            name='Ledger Tee',
            category='Top',
            cost_price=50,
            selling_price=200,
        )
        sale = Sale.objects.create(
            invoice_no='SL-LEDGER',
            agent=admin,
            total_amount=400,
            cash_amount=400,
        )
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=2,
            unit_price=200,
            final_price=400,
            profit=300,
        )
        self.client.force_login(admin)

        response = self.client.get('/reports/', {'date_range': 'today'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['ledger']), 1)
        self.assertEqual(response.context['ledger'][0]['total_sales'], Decimal('400'))
        self.assertEqual(response.context['ledger'][0]['sold_quantity'], 2)

        export = self.client.get('/reports/', {
            'date_range': 'today',
            'export': 'csv',
        })
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export['Content-Type'], 'text/csv')
        self.assertIn(b'Total Sales', export.content)
