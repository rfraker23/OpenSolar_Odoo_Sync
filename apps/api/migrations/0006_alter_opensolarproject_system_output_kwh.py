# Generated by Django 5.2 on 2025-04-10 21:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_opensolarproject_battery_size_kwh_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='opensolarproject',
            name='system_output_kwh',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
    ]
