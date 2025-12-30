import pandas as pd
from django.core.management.base import BaseCommand
from dmt.models import EkoBank

class Command(BaseCommand):
    help = "Import bank list from Excel into EkoBank model"

    def handle(self, *args, **kwargs):
        file_path = "Bank List.xlsx" 

        df = pd.read_excel(file_path)

        for _, row in df.iterrows():
            EkoBank.objects.update_or_create(
                bank_id=row["Bank ID"],
                defaults={
                    "bank_name": row["Bank Name"],
                    "bank_code": row["Bank Code"],
                    "imps_status": row["IMPS Status"],
                    "neft_status": row["NEFT Status"],
                    "verification_status": row["Verification Status"],
                    "ifsc_status": row["IFSC Status"],
                    "static_ifsc": row["Static IFSC"],
                }
            )

        self.stdout.write(self.style.SUCCESS("✔ Bank data imported successfully!"))
