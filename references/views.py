import io
import json

from django.contrib.auth import get_user_model
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
    GET /references/api/search/?q=term[&category=name]
    Returns JSON list of matching active clauses, title/category matches first.
    Optional ?category= scopes results to a single category (for Browse mode).
    """
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    if len(q) < 2:
        return JsonResponse({'results': []})

    qs = ReferenceClause.objects.filter(is_active=True)
    if category:
        qs = qs.filter(category=category)

    # Title/category/subcategory matches — shown first
    title_matches = list(
        qs.filter(
            Q(title__icontains=q) |
            Q(category__icontains=q) |
            Q(subcategory__icontains=q)
        ).order_by('sort_order', 'category', 'title')[:100]
    )
    title_match_ids = {c.id for c in title_matches}

    # Body-only matches — shown after, only if we have room
    body_matches = []
    if len(title_matches) < 200:
        body_matches = list(
            qs.filter(body__icontains=q)
              .exclude(id__in=title_match_ids)
              .order_by('sort_order', 'category', 'title')[:200 - len(title_matches)]
        )

    all_clauses = title_matches + body_matches

    results = [
        {
            'id': c.id,
            'category': c.category,
            'subcategory': c.subcategory,
            'title': c.title,
            'body': c.body,
            'is_featured': c.is_featured,
        }
        for c in all_clauses
    ]
    return JsonResponse({'results': results})


@login_required
@require_GET
def featured_clauses(request):
    """
    GET /references/api/featured/[?category=name]
    Returns featured active clauses, optionally scoped to one category.
    """
    category = request.GET.get('category', '').strip()
    qs = ReferenceClause.objects.filter(is_active=True, is_featured=True)
    if category:
        qs = qs.filter(category=category)
    qs = qs.order_by('sort_order', 'category', 'title')

    results = [
        {
            'id': c.id,
            'category': c.category,
            'subcategory': c.subcategory,
            'title': c.title,
            'body': c.body,
            'is_featured': True,
        }
        for c in qs
    ]
    return JsonResponse({'results': results})


@login_required
@require_GET
def clauses_by_category(request):
    """
    GET /references/api/clauses/           — returns ALL active clauses in document order
    GET /references/api/clauses/?category= — returns clauses for that category only
    No text-search cap; full bodies included.
    """
    category = request.GET.get('category', '').strip()
    if category:
        qs = ReferenceClause.objects.filter(
            is_active=True, category=category
        ).order_by('sort_order', 'subcategory', 'title')
    else:
        qs = ReferenceClause.objects.filter(
            is_active=True
        ).order_by('sort_order', 'category', 'subcategory', 'title')

    results = [
        {
            'id': c.id,
            'category': c.category,
            'subcategory': c.subcategory,
            'title': c.title,
            'body': c.body,
            'is_featured': c.is_featured,
        }
        for c in qs
    ]
    return JsonResponse({'results': results})


@login_required
@require_GET
def clause_detail(request, clause_id):
    """
    GET /references/api/clause/<id>/
    Returns a single clause by PK. Used as a fallback when the JS cache
    is missing the body (e.g. stale localStorage entries).
    """
    try:
        c = ReferenceClause.objects.get(pk=clause_id, is_active=True)
    except ReferenceClause.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    return JsonResponse({
        'id': c.id,
        'category': c.category,
        'subcategory': c.subcategory,
        'title': c.title,
        'body': c.body,
        'is_featured': c.is_featured,
    })


@login_required
@require_GET
def categories_list(request):
    """
    GET /references/api/categories/
    Returns the full category/subcategory tree with clause counts.
    Used by Browse mode in the Reference Library panel.
    """
    from collections import defaultdict

    qs = ReferenceClause.objects.filter(is_active=True).values(
        'category', 'subcategory'
    ).order_by('sort_order', 'category', 'subcategory')

    # Build tree: {category: {subcategory: count}}
    tree = defaultdict(lambda: defaultdict(int))
    cat_counts = defaultdict(int)

    for row in qs:
        cat = row['category']
        sub = row['subcategory'] or ''
        tree[cat][sub] += 1
        cat_counts[cat] += 1

    categories = []
    for cat, subs in tree.items():
        sub_list = [
            {'name': sub, 'count': count}
            for sub, count in sorted(subs.items())
            if sub  # skip the empty-subcategory bucket from sub list
        ]
        categories.append({
            'name': cat,
            'count': cat_counts[cat],
            'subcategories': sub_list,
        })

    return JsonResponse({'categories': categories})


@login_required
@require_GET
def user_searches_get(request):
    """GET /references/api/user-searches/ — return the current user's saved searches."""
    searches = request.user.ref_saved_searches or []
    return JsonResponse({'searches': searches[:10]})


@login_required
@require_POST
def user_searches_save(request):
    """POST /references/api/user-searches/save/ — prepend a search query and save."""
    try:
        data = json.loads(request.body)
        q = (data.get('q') or '').strip()
    except (json.JSONDecodeError, AttributeError):
        q = ''
    if not q or len(q) < 2:
        return JsonResponse({'ok': False, 'error': 'query too short'})
    searches = list(request.user.ref_saved_searches or [])
    searches = [s for s in searches if s.lower() != q.lower()]
    searches.insert(0, q)
    searches = searches[:10]
    get_user_model().objects.filter(pk=request.user.pk).update(ref_saved_searches=searches)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def user_searches_clear(request):
    """POST /references/api/user-searches/clear/ — wipe the user's saved searches."""
    get_user_model().objects.filter(pk=request.user.pk).update(ref_saved_searches=[])
    return JsonResponse({'ok': True})


@login_required
def reimport_view(request):
    """
    GET  /references/reimport/  — show upload form (admin only)
    POST /references/reimport/  — upload .docx and re-import,
                                   preserving is_featured flags by title match.
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

            if not clauses:
                messages.error(request, 'Import aborted: no clauses were found in the uploaded document. '
                                        'The file may use unexpected heading styles. Existing clauses were NOT changed.')
            else:
                # Preserve featured flags by title before wiping
                featured_titles = set(
                    ReferenceClause.objects.filter(is_featured=True).values_list('title', flat=True)
                )

                ReferenceClause.objects.all().delete()

                # Restore is_featured for clauses whose title still exists in the new import
                new_objects = []
                for c in clauses:
                    c['is_featured'] = c['title'] in featured_titles
                    new_objects.append(ReferenceClause(**c))

                ReferenceClause.objects.bulk_create(new_objects)
                restored = sum(1 for c in clauses if c['is_featured'])
                messages.success(
                    request,
                    f'Imported {len(clauses)} reference clauses successfully. '
                    f'{restored} featured flag(s) restored by title match.'
                )
        except Exception as e:
            messages.error(request, f'Import failed: {e}')

        return redirect('references:reimport')

    clause_count = ReferenceClause.objects.filter(is_active=True).count()
    featured_count = ReferenceClause.objects.filter(is_active=True, is_featured=True).count()
    return render(request, 'references/reimport.html', {
        'clause_count': clause_count,
        'featured_count': featured_count,
    })

