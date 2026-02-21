#!/bin/bash
cd /home/dev/advisor-portal-app
source /home/dev/advisor-portal-app/venv/bin/activate
python manage.py shell << 'EOF'
from cases.models import CaseDocument
from django.core.files.base import ContentFile
import os

# Get first case
case = CaseDocument.objects.first().case

# Create test file
test_content = ContentFile(b'Test file content')
test_doc = CaseDocument.objects.create(
    case=case,
    document_type='supporting',
    file=test_content,
    original_filename='test_django_save.txt',
    file_size=len(b'Test file content'),
    uploaded_by=case.member
)

print(f'Document ID: {test_doc.id}')
print(f'Document path: {test_doc.file.name}')
print(f'Full path: {test_doc.file.path}')
print(f'File exists on disk: {os.path.exists(test_doc.file.path)}')
EOF
