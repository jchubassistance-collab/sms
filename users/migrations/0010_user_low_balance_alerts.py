from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0009_otpcode_password_reset_purpose'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='low_balance_alerts',
            field=models.BooleanField(default=False),
        ),
    ]
