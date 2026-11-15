from decimal import Decimal

from django.db import migrations, models
import django.core.validators


def create_payment_configuration(apps, schema_editor):
    PaymentConfiguration = apps.get_model('results', 'PaymentConfiguration')
    PaymentConfiguration.objects.get_or_create(
        pk=1,
        defaults={
            'minimum_payment_amount': Decimal('2000.00'),
            'processing_fee': Decimal('250.00'),
        },
    )


def remove_payment_configuration(apps, schema_editor):
    PaymentConfiguration = apps.get_model('results', 'PaymentConfiguration')
    PaymentConfiguration.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0006_testimonial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentConfiguration',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ('minimum_payment_amount', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('2000.00'),
                    help_text="Minimum amount applied to the student's fee balance.",
                    max_digits=10,
                    validators=[django.core.validators.MinValueValidator(Decimal('1.00'))],
                )),
                ('processing_fee', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('250.00'),
                    help_text='Additional charge added to every new payment.',
                    max_digits=10,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                )),
            ],
            options={
                'verbose_name': 'Payment Configuration',
                'verbose_name_plural': 'Payment Configuration',
            },
        ),
        migrations.AddField(
            model_name='feepayment',
            name='processing_fee',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
        ),
        migrations.RunPython(create_payment_configuration, remove_payment_configuration),
    ]
