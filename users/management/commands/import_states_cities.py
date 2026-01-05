from django.core.management.base import BaseCommand
import pandas as pd
from users.models import State, City

class Command(BaseCommand):
    help = "Import Indian States and Cities from Excel"

    def handle(self, *args, **kwargs):
        file_path = "india_states_cities.xlsx"  # project root me rakho

        df = pd.read_excel(file_path)

        for _, row in df.iterrows():
            state_name = row["state"].strip()
            state_code = row["state_code"].strip()
            city_name = row["city"].strip()

            state, _ = State.objects.get_or_create(
                name=state_name,
                defaults={"code": state_code}
            )

            City.objects.get_or_create(
                state=state,
                name=city_name
            )

        self.stdout.write(self.style.SUCCESS("✅ States & Cities imported successfully"))
