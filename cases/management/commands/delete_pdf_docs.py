from django.core.management.base import BaseCommand
from cases.models import CaseDocument

class Command(BaseCommand):
    help = 'Delete all federal fact finder PDF documents to force regeneration'

    def handle(self, *args, **options):
        docs = CaseDocument.objects.filter(document_type='federal_fact_finder')
        count = docs.count()
        docs.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} PDF documents'))
