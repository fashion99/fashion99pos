from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('posapp', '0007_customuser_default_portal'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='delete_product',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='customuser',
            name='delete_sales',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='customuser',
            name='delete_expense',
            field=models.BooleanField(default=False),
        ),
    ]