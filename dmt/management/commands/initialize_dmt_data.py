from django.core.management.base import BaseCommand
from dmt.models import DMTServiceCharge, DMTBank

class Command(BaseCommand):
    help = 'Initialize DMT service charges and banks data'
    
    def handle(self, *args, **options):
        service_charges = [
            {'amount_range': '0-1000', 'min_amount': 0, 'max_amount': 1000, 'service_charge': 5.00},
            {'amount_range': '1001-10000', 'min_amount': 1001, 'max_amount': 10000, 'service_charge': 10.00},
            {'amount_range': '10001-25000', 'min_amount': 10001, 'max_amount': 25000, 'service_charge': 15.00},
            {'amount_range': '25001-50000', 'min_amount': 25001, 'max_amount': 50000, 'service_charge': 20.00},
        ]
        
        for charge_data in service_charges:
            charge, created = DMTServiceCharge.objects.get_or_create(
                amount_range=charge_data['amount_range'],
                defaults=charge_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created service charge: {charge.amount_range}')
                )
        
        banks = [
            {'bank_id': 11, 'bank_name': 'Punjab National Bank', 'ifsc_prefix': 'PUNB'},
            {'bank_id': 12, 'bank_name': 'State Bank of India', 'ifsc_prefix': 'SBIN'},
            {'bank_id': 13, 'bank_name': 'HDFC Bank', 'ifsc_prefix': 'HDFC'},
            {'bank_id': 14, 'bank_name': 'ICICI Bank', 'ifsc_prefix': 'ICIC'},
            {'bank_id': 15, 'bank_name': 'Axis Bank', 'ifsc_prefix': 'UTIB'},
        ]
        
        for bank_data in banks:
            bank, created = DMTBank.objects.get_or_create(
                bank_id=bank_data['bank_id'],
                defaults=bank_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created bank: {bank.bank_name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully initialized DMT data')
        )