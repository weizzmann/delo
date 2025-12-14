"""Service to recalculate start/end pages for a sequence of documents.
Provides a pure function usable in tests and a DB-oriented helper.
"""
MAX_PAGES = 250


def recalc_entries(entries):
    """
    entries: list of dicts with at least {'document_id', 'pages_count'} in desired order.
    Returns: (updated_entries, total_pages, rejected_ids)
    updated_entries will include start_page and end_page and order (1-based)
    Rejection occurs when adding a document would exceed MAX_PAGES (business rule).
    """
    total = 0
    updated = []
    rejected = []
    order = 1
    for e in entries:
        pages = e.get('pages_count')
        did = e.get('document_id')
        if pages is None or pages <= 0:
            rejected.append(did)
            continue

        if total + pages > MAX_PAGES:
            rejected.append(did)
            break

        start = total + 1
        end = total + pages
        updated.append({
            'document_id': did,
            'pages_count': pages,
            'start_page': start,
            'end_page': end,
            'order': order,
        })
        order += 1
        total += pages

        if total == MAX_PAGES:
            break

    return updated, total, rejected
