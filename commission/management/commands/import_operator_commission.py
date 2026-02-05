from django.core.management.base import BaseCommand
import csv
from decimal import Decimal

from bbps.models import Operator
from services.models import ServiceSubCategory
from commission.models import OperatorCommission, CommissionPlan
from users.models import User


class Command(BaseCommand):
    help = "Import Operator Commission from CSV (CSV = Source of Truth)"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **options):
        csv_file = options['csv_file']

        # 🔐 Superadmin (mandatory)
        superadmin = User.objects.filter(role='superadmin', is_active=True).first()
        if not superadmin:
            self.stdout.write(self.style.ERROR("Superadmin not found"))
            return

        # 📦 Default commission plan
        default_plan = CommissionPlan.objects.first()
        if not default_plan:
            self.stdout.write(self.style.ERROR("Commission plan not found"))
            return

        skipped = []   # 👈 IMPORTANT

        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    operator_name = row['Operator Name'].strip()
                    commission_type = row['Commission Type'].strip().lower()

                    raw_value = row['B2B Commission BELOW 5K']
                    csv_value = Decimal(raw_value.replace('₹', '').strip())

                    # ✅ SAFE operator lookup (fallback based)
                    operator = (
                        Operator.objects.filter(operator_name__iexact=operator_name).first()
                        or Operator.objects.filter(operator_name__icontains=operator_name).first()
                        or Operator.objects.filter(
                            operator_name__icontains=operator_name.replace("FASTag", "").strip()
                        ).first()
                    )

                    if not operator:
                        skipped.append(operator_name)
                        continue

                    # ✅ Service subcategory
                    subcategory = ServiceSubCategory.objects.get(
                        name=row['Category']
                    )

                    # 🔥 CSV = MASTER → DB update
                    obj, created = OperatorCommission.objects.update_or_create(
                        operator=operator,
                        service_subcategory=subcategory,
                        commission_plan=default_plan,
                        operator_circle=None,
                        defaults={
                            'operator_name': operator.operator_name,
                            'operator_type': operator.operator_type,
                            'commission_type': commission_type,
                            'max_commission_value': csv_value,  # 🔒 CAP
                            'commission_value': csv_value,      # auto-fill
                            'created_by': superadmin
                        }
                    )

                    status = "CREATED" if created else "UPDATED"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{status} | {operator.operator_name} | ₹{csv_value}"
                        )
                    )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error for operator {row.get('Operator Name')}: {str(e)}"
                        )
                    )

        # 🟡 Skipped operators report
        if skipped:
            self.stdout.write(self.style.WARNING("\nSkipped operators (not found in DB):"))
            for name in skipped:
                self.stdout.write(self.style.WARNING(f"- {name}"))

        self.stdout.write(self.style.SUCCESS("\nCSV import completed successfully"))
