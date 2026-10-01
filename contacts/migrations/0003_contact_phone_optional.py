from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('contacts', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='phone',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]