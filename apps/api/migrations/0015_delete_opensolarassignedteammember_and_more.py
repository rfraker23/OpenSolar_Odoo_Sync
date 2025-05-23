# Generated by Django 5.2 on 2025-05-09 15:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_rename_opensolarsalesrep_opensolarassignedteammember'),
    ]

    operations = [
        migrations.DeleteModel(
            name='OpenSolarAssignedTeamMember',
        ),
        migrations.AddField(
            model_name='opensolarproject',
            name='price_excluding_tax',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='opensolarproject',
            name='price_including_tax',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
