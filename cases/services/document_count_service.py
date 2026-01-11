"""
Service for document counting and messaging.
Provides consistent formatting of document counts across the application.
"""


def get_document_count_message(case, include_breakdown=True):
    """
    Get a formatted message showing document counts for a case.
    
    Args:
        case: The Case object
        include_breakdown: If True, shows breakdown by type; if False, just total
        
    Returns:
        str: Formatted message with document count(s)
    """
    total = case.documents.count()
    
    if not include_breakdown:
        return f"Total documents: {total}"
    
    ff_count = case.documents.filter(document_type='fact_finder').count()
    sup_count = case.documents.filter(document_type='supporting').count()
    report_count = case.documents.filter(document_type='report').count()
    
    parts = []
    if ff_count > 0:
        parts.append(f"{ff_count} Federal Fact Finder")
    if sup_count > 0:
        parts.append(f"{sup_count} Supporting")
    if report_count > 0:
        parts.append(f"{report_count} Report(s)")
    
    # If no documents or none match the types above
    if not parts:
        return f"Total documents: {total}"
    
    breakdown = ", ".join(parts)
    return f"Documents: {breakdown} ({total} total)"


def get_simple_document_count(case):
    """
    Get a simple count without breakdown or emoji.
    Useful for inline messages.
    
    Args:
        case: The Case object
        
    Returns:
        int: Total number of documents
    """
    return case.documents.count()


def get_document_count_summary(case):
    """
    Get detailed breakdown of all document types.
    
    Args:
        case: The Case object
        
    Returns:
        dict: Dictionary with counts for each document type
    """
    return {
        'total': case.documents.count(),
        'fact_finder': case.documents.filter(document_type='fact_finder').count(),
        'supporting': case.documents.filter(document_type='supporting').count(),
        'report': case.documents.filter(document_type='report').count(),
        'other': case.documents.filter(document_type='other').count(),
    }
