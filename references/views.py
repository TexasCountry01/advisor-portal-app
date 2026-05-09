import io
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST

from .models import ReferenceClause


@login_required
@require_GET
def search_clauses(request):
    """
    GET /references/api/search/?q=term
    Returns JSON list of matching active clauses.
    """
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    qs = ReferenceClause.objects.filter(
        is_active=True
    ).filter(
        Q(title__icontains=q) |
        Q(category__icontains=q) |
        Q(subcategory__icontains=q) |
        Q(body__icontains=q)
    ).order_by('sort_order', 'category', 'title')[:50]

    results = [
        {
            'id': c.id,
            'category': c.category,
            'subcategory': c.subcategory,
            'title': c.title,
            'body': c.body,
        }
        for c in qs
    ]
    return JsonResponse({'results': results})


@login_required
def reimport_view(request):
    """
    GET  /references/reimport/  — show upload form (admin only)
    POST /references/reimport/  — upload .docx and re-import
    """
    if request.user.role != 'administrator':
        return JsonResponse({'error': 'Forbidden'}, status=403)

    if request.method == 'POST':
        uploaded = request.FILES.get('docx_file')
        if not uploaded or not uploaded.name.endswith('.docx'):
            messages.error(request, 'Please upload a valid .docx file.')
            return redirect('references:reimport')

        try:
            from docx import Document
            from .management.commands.import_reference_doc import _parse_document

            data = b''.join(uploaded.chunks())
            doc = Document(io.BytesIO(data))
            clauses = _parse_document(doc)

            ReferenceClause.objects.all().delete()
            ReferenceClause.objects.bulk_create([ReferenceClause(**c) for c in clauses])

            messages.success(request, f'Imported {len(clauses)} reference clauses successfully.')
        except Exception as e:
            messages.error(request, f'Import failed: {e}')

        return redirect('references:reimport')

    clause_count = ReferenceClause.objects.filter(is_active=True).count()
    return render(request, 'references/reimport.html', {'clause_count': clause_count})
