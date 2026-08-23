from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('posapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='cancel_returned_products',
            field=models.BooleanField(default=False),
        ),
    ]