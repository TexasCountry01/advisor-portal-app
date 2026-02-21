#!/usr/bin/env python
"""Analyze document 170 to understand why file is missing"""

import os
import sys
import django
import pathlib

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from cases.models import CaseDocument

# Get document 170
doc = CaseDocument.objects.get(id=170)

print("Document 170 Analysis")
print("=" * 60)
print("ID: 170")
print("Filename: {}".format(doc.original_filename))
print("File field value: '{}'".format(doc.file))
print("Document type: {}".format(doc.document_type))
print("Uploaded at: {}".format(doc.uploaded_at))
print("Uploaded by: {}".format(doc.uploaded_by))
print("File size in DB: {} bytes".format(doc.file_size))
print()

# Try to get file path
if doc.file:
    try:
        path = doc.file.path
        print("Expected file path: {}".format(path))
        
        p = pathlib.Path(path)
        if p.exists():
            print("File EXISTS on disk")
            actual_size = p.stat().st_size
            print("Actual size on disk: {} bytes".format(actual_size))
        else:
            print("File MISSING on disk")
            # Check if parent dir exists
            parent = p.parent
            print("Parent directory: {}".format(parent))
            print("Parent exists: {}".format(parent.exists()))
    except Exception as e:
        print("Error getting path: {}".format(e))
else:
    print("ERROR: File field is EMPTY!")
