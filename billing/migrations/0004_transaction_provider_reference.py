from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0003_smspackage_badge_smspackage_validity'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='provider_reference',
            field=models.CharField(blank=True, max_length=36),
        ),
    ]