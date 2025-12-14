from app.services.volume_calculator import calculate_volume_structure


def test_calculator_basic():
    ids = [1, 2, 3]
    pages_map = {1: 10, 2: 20, 3: 30}
    res = calculate_volume_structure(ids, pages_map)
    assert 'volumes' in res
    assert res['rejected_document_ids'] == []
    v = res['volumes'][0]
    assert v['total_pages'] == 60
    assert v['documents'][0]['start_page'] == 1
    assert v['documents'][0]['end_page'] == 10
    assert v['documents'][1]['start_page'] == 11
