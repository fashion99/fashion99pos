from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('posapp', '0002_customuser_cancel_returned_products'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='allow_custom_discount',
            field=models.BooleanField(default=False),
        ),
    ]