from django.core.management.base import BaseCommand
from bbps.models import bbpsServiceCharge, Operator
from django.conf import settings

class Command(BaseCommand):
    help = 'Initialize bbps service charges'
    
    def handle(self, *args, **options):
        # Initialize service charges
        service_charges = [
            {
                'amount_range': '0-100',
                'min_amount': 0,
                'max_amount': 100,
                'service_charge': 2.00,
                'charge_type': 'fixed'
            },
            {
                'amount_range': '101-500',
                'min_amount': 101,
                'max_amount': 500,
                'service_charge': 3.00,
                'charge_type': 'fixed'
            },
            {
                'amount_range': '501-1000',
                'min_amount': 501,
                'max_amount': 1000,
                'service_charge': 5.00,
                'charge_type': 'fixed'
            },
            {
                'amount_range': '1001-5000',
                'min_amount': 1001,
                'max_amount': 5000,
                'service_charge': 10.00,
                'charge_type': 'fixed'
            },
            {
                'amount_range': '5001-10000',
                'min_amount': 5001,
                'max_amount': 10000,
                'service_charge': 15.00,
                'charge_type': 'fixed'
            },
        ]
        
        for charge_data in service_charges:
            charge, created = bbpsServiceCharge.objects.update_or_create(
                amount_range=charge_data['amount_range'],
                defaults=charge_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created service charge: {charge.amount_range} - ₹{charge.service_charge}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Updated service charge: {charge.amount_range} - ₹{charge.service_charge}')
                )
        
        # Add default operators (manual entries for common operators)
        default_operators = [
            {
                'operator_id': '1',
                'operator_name': 'Airtel Prepaid',
                'operator_type': 'prepaid',
                'category_id': 5,
                'circle': 'All India',
                'is_active': True
            },
            {
                'operator_id': '90',
                'operator_name': 'Jio Prepaid',
                'operator_type': 'prepaid',
                'category_id': 5,
                'circle': 'All India',
                'is_active': True
            },
            {
                'operator_id': '400',
                'operator_name': 'Vi Prepaid',
                'operator_type': 'prepaid',
                'category_id': 5,
                'circle': 'All India',
                'is_active': True
            },
            {
                'operator_id': '5',
                'operator_name': 'BSNL Prepaid',
                'operator_type': 'prepaid',
                'category_id': 5,
                'circle': 'All India',
                'is_active': True
            },
            {
                'operator_id': '41',
                'operator_name': 'Airtel Postpaid',
                'operator_type': 'postpaid',
                'category_id': 10,
                'circle': 'All India',
                'is_active': True
            },
            {
                'operator_id': '172',
                'operator_name': 'Jio Postpaid',
                'operator_type': 'postpaid',
                'category_id': 10,
                'circle': 'All India',
                'is_active': True
            },
            {
                'operator_id': '20',
                'operator_name': 'Tata Sky',
                'operator_type': 'dth',
                'category_id': 4,
                'circle': 'All India',
                'is_active': True
            },
            {
                'operator_id': '21',
                'operator_name': 'Airtel DTH',
                'operator_type': 'dth',
                'category_id': 4,
                'circle': 'All India',
                'is_active': True
            },
            {
                'operator_id': '16',
                'operator_name': 'Dish TV',
                'operator_type': 'dth',
                'category_id': 4,
                'circle': 'All India',
                'is_active': True
            },
        ]
        
        for operator_data in default_operators:
            operator, created = Operator.objects.update_or_create(
                operator_id=operator_data['operator_id'],
                defaults=operator_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created operator: {operator.operator_name} ({operator.operator_id})')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully initialized bbps data')
        )