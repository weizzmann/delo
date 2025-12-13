from app.services.volume_updater import recalc_entries


def test_recalc_simple():
    entries = [
        {'document_id': 1, 'pages_count': 2},
        {'document_id': 2, 'pages_count': 3},
    ]
    updated, total, rejected = recalc_entries(entries)
    assert total == 5
    assert rejected == []
    assert updated[0]['start_page'] == 1
    assert updated[0]['end_page'] == 2
    assert updated[1]['start_page'] == 3
