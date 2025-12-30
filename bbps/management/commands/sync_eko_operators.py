from django.core.management.base import BaseCommand
from bbps.services.eko_service import bbps_manager
from bbps.models import Operator
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync operators from EKO API'
    
    def handle(self, *args, **options):
        categories = [
            ('broadband', 'Broadband Postpaid'),
            ('gas', 'Gas'),
            ('dth', 'DTH'),
            ('prepaid', 'Mobile Prepaid'),
            ('tax', 'Tax'),
            ('credit', 'Credit Card'),
            ('electricity', 'Electricity'),
            ('landline', 'Landline'),
            ('postpaid', 'Mobile Postpaid'),
            ('water', 'Water'),
            ('society', 'Housing Society'),
            ('ott', 'Subscription / OTT'),
            ('education', 'Education'),
            ('municipal_tax', 'Municipal Taxes'),
            ('clubs', 'Clubs & Associations'),
            ('cable', 'Cable TV'),
            ('lpg', 'LPG Cylinder'),
            ('hospital', 'Hospital'),
            ('insurance', 'Insurance'),
            ('loan', 'Loan EMI'),
            ('fastag', 'FASTag'),
            ('municipal_services', 'Municipal Services'),
            ('subscription_2', 'Subscription2'),
        ]

        
        for category_key, category_name in categories:
            self.stdout.write(f"Syncing {category_name} operators...")
            
            result = bbps_manager.get_operators(category_key)
            
            if result.get('success'):
                operators = result.get('operators', [])
                count = 0
                
                for op in operators:
                    operator_id = str(op.get('operator_id', ''))
                    operator_name = op.get('name') or op.get('operator_name', '')
                    
                    if operator_id and operator_name:
                        # Try to extract circle/location from name or use default
                        circle = op.get('circle', '')
                        location = op.get('location', '')
                        
                        # If operator name contains location hint, extract it
                        if '(' in operator_name and ')' in operator_name:
                            import re
                            match = re.search(r'\((.*?)\)', operator_name)
                            if match:
                                location = match.group(1)
                        
                        obj, created = Operator.objects.update_or_create(
                            operator_id=operator_id,
                            defaults={
                                'operator_name': operator_name,
                                'operator_type': category_key,
                                'category_id': op.get('category_id'),
                                'circle': circle,
                                'state': op.get('state', ''),
                                'location': location,
                                'is_active': True
                            }
                        )
                        
                        if created:
                            count += 1
                            self.stdout.write(f"  Added: {operator_name} ({operator_id})")
                        else:
                            self.stdout.write(f"  Updated: {operator_name} ({operator_id})")
                
                self.stdout.write(self.style.SUCCESS(f"Synced {count} {category_name} operators"))
            else:
                self.stdout.write(self.style.WARNING(f"Failed to sync {category_name}: {result.get('message')}"))
        
        # Count total active operators
        total_operators = Operator.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(f"Total active operators: {total_operators}"))
        self.stdout.write(self.style.SUCCESS("Operator sync completed"))