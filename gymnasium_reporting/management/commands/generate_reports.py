from django.core.management.base import BaseCommand
from gymnasium_reporting.views import generate_registration_report_csv, generate_enrollment_report_csv

class Command(BaseCommand):
    help = 'Generate daily reports'

    def handle(self, *args, **kwargs):
        generate_registration_report_csv()
        generate_enrollment_report_csv()
        self.stdout.write(self.style.SUCCESS('Successfully generated reports'))
