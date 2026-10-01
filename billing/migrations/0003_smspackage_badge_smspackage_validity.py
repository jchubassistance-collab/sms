from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='smspackage',
            name='badge',
            field=models.CharField(default='SMS', max_length=20),
        ),
        migrations.AddField(
            model_name='smspackage',
            name='validity',
            field=models.PositiveIntegerField(default=30),
        ),
    ]
