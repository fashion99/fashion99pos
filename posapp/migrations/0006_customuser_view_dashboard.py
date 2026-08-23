from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('posapp', '0005_salereturn_is_cancelled'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='view_dashboard',
            field=models.BooleanField(default=False),
        ),
    ]