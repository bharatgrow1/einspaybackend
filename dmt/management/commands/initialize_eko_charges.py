# dmt/management/commands/initialize_eko_charges.py
from django.core.management.base import BaseCommand
from dmt.models import EKOChargeConfig

class Command(BaseCommand):
    help = 'Initialize EKO charge configuration data from Excel'
    
    def handle(self, *args, **options):
        # Your complete Excel data here
        data = [
            {'amount_from': 100, 'amount_to': 1000, 'customer_fee_net_gst': 8.47, 'eko_pricing': 7, 'commission_after_tds': 1.45},
            {'amount_from': 200, 'amount_to': 1000, 'customer_fee_net_gst': 8.47, 'eko_pricing': 7, 'commission_after_tds': 1.45},
            {'amount_from': 300, 'amount_to': 1000, 'customer_fee_net_gst': 8.47, 'eko_pricing': 7, 'commission_after_tds': 1.45},
            # Add ALL your Excel rows here
            {'amount_from': 10000, 'amount_to': 10000, 'customer_fee_net_gst': 84.75, 'eko_pricing': 7, 'commission_after_tds': 76.19},
            # Continue with all other rows...
        ]
        
        count = 0
        for item in data:
            obj, created = EKOChargeConfig.objects.update_or_create(
                amount_from=item['amount_from'],
                amount_to=item['amount_to'],
                defaults=item
            )
            if created:
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created EKO charge: ₹{obj.amount_from} - ₹{obj.amount_to}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {count} EKO charge entries')
        )