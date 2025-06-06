# Generated by Django 5.1.7 on 2025-04-14 18:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop_app', '0005_transaction_paypal_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='epayco_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='payment_method',
            field=models.CharField(choices=[('paypal', 'PayPal'), ('epayco', 'ePayco'), ('unknown', 'Unknown')], default='unknown', max_length=20),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='currency',
            field=models.CharField(default='USD', max_length=10),
        ),
    ]
