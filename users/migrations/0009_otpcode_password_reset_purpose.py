from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0008_otpcode_purpose'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otpcode',
            name='purpose',
            field=models.CharField(
                choices=[
                    ('registration', 'Registration'),
                    ('login', 'Login'),
                    ('password_reset', 'Password Reset'),
                ],
                default='registration',
                max_length=20,
            ),
        ),
    ]