from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('campaigns', '0003_maillog_sendernamerequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='smslog',
            name='recipient_phone',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='smslog',
            name='delivery_received_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]