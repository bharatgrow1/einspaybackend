from django.core.management.base import BaseCommand
import csv

from bbps.models import Operator
from services.models import ServiceSubCategory


class Command(BaseCommand):
    help = "Export ALL operators (even without commission) to master CSV"

    def handle(self, *args, **kwargs):
        filename = "ALL_OPERATORS_MASTER.csv"

        subcategories = list(
            ServiceSubCategory.objects.values_list("name", flat=True)
        )

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow([
                "Operator ID",
                "Operator Name",
                "Operator Type",
                "Service Subcategory",
                "Commission Type",
                "B2B Commission BELOW 5K"
            ])

            for operator in Operator.objects.all():
                for subcat in subcategories:
                    writer.writerow([
                        operator.operator_id,
                        operator.operator_name,
                        operator.operator_type,
                        subcat,           # editable
                        "fixed",          # default
                        ""                # YOU fill this
                    ])

        self.stdout.write(
            self.style.SUCCESS(
                f"ALL operators exported successfully → {filename}"
            )
        )
