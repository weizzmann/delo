"""Volume calculator service: packs ordered document IDs into volumes
with EXACT MAX_PAGES limit per volume. Том создается только при 250 страницах.
"""
MAX_PAGES = 250


def calculate_volume_structure(document_ids, pages_map):
    """
    document_ids: ordered list of document ids
    pages_map: dict {doc_id: pages_count}

    Returns: {
      'volumes': [ 
        { 
          'documents': [ 
            {id, pages_count, start_page, end_page, order} 
          ], 
          'total_pages': int,  # Должно быть РОВНО 250 или 0
          'volume_number': int
        } 
      ],
      'rejected_document_ids': [ids],  # Документы, которые не поместились
      'partial_volume': {              # Частично заполненный том (менее 250 стр.)
        'documents': [...],
        'total_pages': int
      }
    }
    """
    volumes = []
    rejected = []
    
    if not document_ids:
        return {
            'volumes': [], 
            'rejected_document_ids': [],
            'partial_volume': None
        }
    
    current_volume_docs = []
    current_volume_total = 0
    current_volume_number = 1
    
    for did in document_ids:
        pages = pages_map.get(did)
        
        # Проверка валидности документа
        if pages is None:
            rejected.append({'id': did, 'reason': 'Документ не найден'})
            continue
            
        if pages <= 0:
            rejected.append({'id': did, 'reason': f'Неверное количество страниц: {pages}'})
            continue
        
        # Если документ больше MAX_PAGES - отклоняем
        if pages > MAX_PAGES:
            rejected.append({'id': did, 'reason': f'Документ слишком большой: {pages} > {MAX_PAGES} стр.'})
            continue
        
        # Проверяем, поместится ли документ в текущий том
        if current_volume_total + pages <= MAX_PAGES:
            # Документ помещается в текущий том
            start = current_volume_total + 1
            end = current_volume_total + pages
            current_volume_docs.append({
                'id': did,
                'pages_count': pages,
                'start_page': start,  # Относительно тома
                'end_page': end,      # Относительно тома
                'order': len(current_volume_docs) + 1  # Порядок в томе
            })
            current_volume_total += pages
            
            # Если том заполнен до предела (ровно 250), закрываем его
            if current_volume_total == MAX_PAGES:
                volumes.append({
                    'documents': current_volume_docs,
                    'total_pages': current_volume_total,
                    'volume_number': current_volume_number
                })
                # Начинаем следующий том
                current_volume_docs = []
                current_volume_total = 0
                current_volume_number += 1
                
        else:
            # Документ не помещается в текущий том
            # НЕ создаем новый том, а отклоняем документ
            rejected.append({
                'id': did, 
                'reason': f'Не помещается в текущий том. Доступно: {MAX_PAGES - current_volume_total} стр., требуется: {pages} стр.'
            })
    
    # Частично заполненный том (менее 250 стр.)
    partial_volume = None
    if current_volume_total > 0 and current_volume_total < MAX_PAGES:
        partial_volume = {
            'documents': current_volume_docs,
            'total_pages': current_volume_total
        }
    
    return {
        'volumes': volumes,
        'rejected_document_ids': rejected,
        'partial_volume': partial_volume
    }