# Generated migration to fix legacy document_type values
from django.db import migrations


def fix_document_type_values(apps, schema_editor):
    """Convert legacy document type values to new format"""
    CaseDocument = apps.get_model('cases', 'CaseDocument')
    
    # Fix legacy document types
    updates = [
        ('Federal Fact Finder', 'fact_finder'),
        ('Supporting Document', 'supporting'),
    ]
    
    for old_value, new_value in updates:
        count = CaseDocument.objects.filter(document_type=old_value).update(document_type=new_value)
        if count > 0:
            print(f"Updated {count} documents: '{old_value}' -> '{new_value}'")


def reverse_fix(apps, schema_editor):
    """Reverse the migration (convert back to legacy format)"""
    CaseDocument = apps.get_model('cases', 'CaseDocument')
    
    # Note: This is not a perfect reverse since we lose the original values,
    # but for safety we just document it
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0016_case_credit_adjustment_reason_creditauditlog'),
    ]

    operations = [
        migrations.RunPython(fix_document_type_values, reverse_fix),
    ]
