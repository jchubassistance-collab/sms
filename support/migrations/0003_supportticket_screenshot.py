from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('support', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportticket',
            name='screenshot',
            field=models.FileField(blank=True, upload_to='support/screenshots/'),
        ),
    ]