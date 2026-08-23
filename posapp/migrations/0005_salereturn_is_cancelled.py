from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('posapp', '0004_alter_sale_discount_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='salereturn',
            name='is_cancelled',
            field=models.BooleanField(default=False),
        ),
    ]