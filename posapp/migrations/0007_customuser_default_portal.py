from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('posapp', '0006_customuser_view_dashboard'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='default_portal',
            field=models.CharField(blank=True, choices=[('dashboard', 'Dashboard'), ('products', 'Products'), ('stock', 'Stock'), ('sales', 'Sales'), ('expenses', 'Expenses'), ('reports', 'Reports'), ('sale_returns', 'Return Log')], default='', max_length=30),
        ),
    ]