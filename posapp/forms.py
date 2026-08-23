from django import forms

from .models import CustomUser, Expense, Product, Sale


PERMISSION_FIELDS = [
    ('view_dashboard', 'Portal: Dashboard'),
    ('view_products', 'Portal: Products'),
    ('view_stock', 'Portal: Stock'),
    ('view_own_sales_history', 'Portal: Own Sales History'),
    ('view_all_sales_history', 'Portal: All Sales History'),
    ('view_own_expense_history', 'Portal: Own Expense History'),
    ('view_all_expense_history', 'Portal: All Expense History'),
    ('view_reports', 'Portal: Reports'),
    ('view_return_notifications', 'Portal: Return Log'),
    ('add_product', 'Products: Add'),
    ('edit_product', 'Products: Edit'),
    ('delete_product', 'Products: Delete'),
    ('add_sales', 'Sales: Add'),
    ('edit_sales', 'Sales: Edit'),
    ('delete_sales', 'Sales: Delete'),
    ('return_sales', 'Sales: Return'),
    ('cancel_returned_products', 'Return Log: Cancel Return'),
    ('add_expense', 'Expenses: Add'),
    ('edit_expense', 'Expenses: Edit'),
    ('delete_expense', 'Expenses: Delete'),
    ('view_cost_price', 'Sales/Products: View Cost Price'),
    ('view_profit', 'Sales/Reports: View Profit'),
    ('view_today_calculations', 'Dashboard: View Today\'s Calculations'),
]


class UserAccountForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        label='New Password',
        help_text='Leave blank to keep the current password.',
    )

    class Meta:
        model = CustomUser
        fields = [
            'username',
            'full_name',
            'email',
            'employee_id',
            'role',
            'default_portal',
            'password',
        ] + [field for field, _ in PERMISSION_FIELDS]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['username'].required = True
        self.fields['full_name'].required = True
        self.fields['role'].choices = CustomUser.ROLE_CHOICES
        self.fields['default_portal'].required = False
        self.fields['default_portal'].widget.attrs.update({'class': 'form-control'})
        if self.instance.pk:
            self.fields.pop('password', None)
        else:
            self.fields['password'].required = True
        for field_name, label in PERMISSION_FIELDS:
            self.fields[field_name].widget.attrs.update({'class': 'checkbox-input'})

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')

        if not self.instance.pk and not password:
            self.add_error('password', 'Password is required for new accounts.')

        portal_permissions = {
            'dashboard': 'view_dashboard',
            'products': 'view_products',
            'stock': 'view_stock',
            'sales': ('view_own_sales_history', 'view_all_sales_history'),
            'expenses': ('view_own_expense_history', 'view_all_expense_history'),
            'reports': 'view_reports',
            'sale_returns': 'view_return_notifications',
        }
        portal = cleaned_data.get('default_portal')
        if portal and self.cleaned_data.get('role') != 'admin':
            permission = portal_permissions[portal]
            permissions = permission if isinstance(permission, tuple) else (permission,)
            if not any(cleaned_data.get(name) for name in permissions):
                self.add_error('default_portal', 'Assign this portal permission before selecting it as the login portal.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        elif self.instance.pk:
            user.password = self.instance.password
        if commit:
            user.save()
        return user


class PasswordResetForm(forms.Form):
    new_password = forms.CharField(
        label='New Password',
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('new_password') != cleaned_data.get('confirm_password'):
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data


class ProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user is not None and not user.has_permission('view_cost_price'):
            self.fields.pop('cost_price', None)

    class Meta:
        model = Product
        fields = [
            'product_code',
            'name',
            'category',
            'custom_category',
            'cost_price',
            'selling_price',
            'normal_discount_price',
            'special_discount_price',
            'allow_custom_discount',
            'has_color',
        ]
        widgets = {
            'product_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'E.g., PROD-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'custom_category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Custom category (optional)'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'normal_discount_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'special_discount_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'allow_custom_discount': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
            'has_color': forms.CheckboxInput(attrs={'class': 'checkbox-input'}),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['amount', 'purpose']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'purpose': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Electricity bill'}),
        }


class SaleForm(forms.Form):
    product_code = forms.CharField(
        label='Product Code',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter or type product code', 'list': 'product-code-options'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )
    payment_method = forms.ChoiceField(
        choices=Sale.PAYMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    discount_type = forms.ChoiceField(
        choices=Sale.DISCOUNT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    variant_color = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Color (optional)'}))
    variant_size = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Size (optional)'}))
    online_amount = forms.DecimalField(
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'})
    )
    custom_discount_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Enter custom sale price'})
    )

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        online_amount = cleaned_data.get('online_amount')

        if payment_method == 'split':
            if online_amount is None or online_amount < 0:
                self.add_error('online_amount', 'Online amount is required for split payments.')
        return cleaned_data

