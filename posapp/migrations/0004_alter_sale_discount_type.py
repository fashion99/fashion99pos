from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('posapp', '0003_product_allow_custom_discount_and_custom_sale_discount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='discount_type',
            field=models.CharField(
                choices=[
                    ('none', 'No Discount'),
                    ('normal', 'Normal Discount'),
                    ('special', 'Special Discount'),
                    ('custom', 'Custom Discount'),
                ],
                default='none',
                max_length=20,
            ),
        ),
    ]
