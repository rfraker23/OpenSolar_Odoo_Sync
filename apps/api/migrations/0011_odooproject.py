# Generated by Django 5.2 on 2025-04-15 17:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_rename_online_url_opensolarproposal_proposal_link_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OdooProject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.CharField(max_length=100, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('customer_name', models.CharField(blank=True, max_length=255, null=True)),
                ('total_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ],
        ),
    ]
