from django.core.management.base import BaseCommand
import pandas as pd
from users.models import State, City

class Command(BaseCommand):
    help = "Import Indian States and Cities from Excel"

    def handle(self, *args, **kwargs):
        file_path = "india_states_cities.xlsx"

        df = pd.read_excel(file_path)

        df.columns = df.columns.str.strip().str.lower()

        for _, row in df.iterrows():

            if pd.isna(row.get("state")) or pd.isna(row.get("city")):
                continue

            state_name = str(row["state"]).strip()
            state_code = str(row["state_code"]).strip()
            city_name = str(row["city"]).strip()
            district_code = str(row["district_code"]).strip()

            state, _ = State.objects.get_or_create(
                name=state_name,
                defaults={"code": state_code}
            )

            City.objects.get_or_create(
                state=state,
                name=city_name,
                defaults={
                    "district_code": district_code
                }
            )

        self.stdout.write(
            self.style.SUCCESS(" States, Cities & District Codes imported successfully")
        )
