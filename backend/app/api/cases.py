from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from ..models import Case, Volume, VolumeDocument, Document, Department, User
from ..extensions import db
from ..services.volume_calculator import calculate_volume_structure
from ..services.volume_updater import recalc_entries

api_cases = Blueprint('api_cases', __name__)

MAX_PAGES = 250  # Максимальное количество страниц в томе


@api_cases.route('/departments', methods=['GET'])
@login_required
def list_departments():
    if current_user.username != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    depts = Department.query.all()
    return jsonify([{'id': d.id, 'name': d.name} for d in depts])


@api_cases.route('/cases', methods=['GET'])
@login_required
def list_cases():
    if current_user.username == 'admin':
        cases = Case.query.all()
    else:
        cases = Case.query.filter_by(department_id=current_user.department_id).all()
    result = []
    for case in cases:
        volumes_info = []
        # Сортируем тома по номеру
        sorted_volumes = sorted(case.volumes, key=lambda v: v.number)
        for vol in sorted_volumes:
            # Подсчитываем количество документов в томе
            documents_count = len(vol.documents)
            
            volumes_info.append({
                'volume_id': vol.id,
                'volume_number': vol.number,
                'pages_start': vol.pages_start,
                'pages_end': vol.pages_end,
                'total_pages': vol.total_pages,
                'documents_count': documents_count,
                'is_full': vol.total_pages == MAX_PAGES,
                'is_verified': vol.is_verified,
                'verified_by': vol.verified_by,
                'verified_at': vol.verified_at.isoformat() if vol.verified_at else None,
                'verifier_name': vol.verifier.username if vol.verifier else None
            })
        
        # Находим текущий том (частично заполненный и не проверенный) или создаем новый
        current_volume = None
        for vol in sorted_volumes:
            if not vol.is_verified and vol.total_pages < MAX_PAGES:
                current_volume = {
                    'volume_id': vol.id,
                    'volume_number': vol.number,
                    'total_pages': vol.total_pages,
                    'free_pages': MAX_PAGES - vol.total_pages
                }
                break
        
        result.append({
            'case_id': case.id,
            'name': case.name,
            'description': case.description,
            'department': case.department.name,
            'volumes': volumes_info,
            'current_volume': current_volume
        })
    return jsonify(result)


@api_cases.route('/cases', methods=['POST'])
@login_required
def create_case():
    payload = request.get_json() or {}
    print("=== CREATE CASE ===")
    print(f"Payload: {payload}")
    print(f"Current user: {current_user.username}, Department ID: {current_user.department_id}")
    
    name = payload.get('name')
    description = payload.get('description')
    ids = payload.get('document_ids') or []
    department_id = payload.get('department_id')

    if not name:
        return jsonify({'error': 'name required'}), 400

    # Определяем ID департамента
    if current_user.username == 'admin' and department_id:
        dept_id = int(department_id)
    else:
        dept_id = current_user.department_id

    print(f"Using Department ID: {dept_id}")
    print(f"Document IDs: {ids}")
    
    # Проверяем, что документы не используются в других делах (если есть)
    if ids:
        used_documents = check_documents_usage(ids)
        if used_documents:
            return jsonify({
                'error': 'Некоторые документы уже используются в других делах',
                'used_documents': used_documents
            }), 400

    # Если есть документы - рассчитываем структуру томов
    if ids:
        docs = Document.query.filter(Document.id.in_(ids)).all()
        pages_map = {d.id: d.pages_count for d in docs}
        print(f"Pages map: {pages_map}")
        result = calculate_volume_structure(ids, pages_map)
        print(f"Calculation result - volumes: {len(result.get('volumes', []))}, partial: {result.get('partial_volume')}")
    else:
        result = {
            'volumes': [], 
            'rejected_document_ids': [],
            'partial_volume': None
        }

    try:
        # create case
        case = Case(name=name, description=description, department_id=dept_id)
        db.session.add(case)
        db.session.flush()
        print(f"Created case with ID: {case.id}")

        # create full volumes (250 pages each)
        for vol_data in result.get('volumes', []):
            volume_number = vol_data['volume_number']
            total_pages = vol_data['total_pages']
            
            # В каждом томе страницы с 1 до total_pages
            pages_start = 1
            pages_end = total_pages
            
            # Создаем том
            v = Volume(
                case_id=case.id,
                number=volume_number,
                pages_start=pages_start,
                pages_end=pages_end,
                department_id=dept_id
            )
            db.session.add(v)
            db.session.flush()
            print(f"Created volume {volume_number} with {total_pages} pages")
            
            # Создаем связи документов с томом (в порядке из vol_data)
            for doc in vol_data.get('documents', []):
                vd = VolumeDocument(
                    volume_id=v.id,
                    document_id=doc['id'],
                    order_in_volume=doc['order'],
                    start_page=doc['start_page'],
                    end_page=doc['end_page']
                )
                db.session.add(vd)
        
        # Создаем частично заполненный том (если есть)
        partial_volume = result.get('partial_volume')
        if partial_volume and partial_volume['total_pages'] > 0:
            # Находим следующий номер тома
            next_volume_number = len(result.get('volumes', [])) + 1
            
            pages_start = 1
            pages_end = partial_volume['total_pages']
            
            # Создаем частично заполненный том
            v = Volume(
                case_id=case.id,
                number=next_volume_number,
                pages_start=pages_start,
                pages_end=pages_end,
                department_id=dept_id
            )
            db.session.add(v)
            db.session.flush()
            print(f"Created partial volume {next_volume_number} with {pages_end} pages")
            
            # Создаем связи документов с томом (в порядке из partial_volume)
            for doc in partial_volume.get('documents', []):
                vd = VolumeDocument(
                    volume_id=v.id,
                    document_id=doc['id'],
                    order_in_volume=doc['order'],
                    start_page=doc['start_page'],
                    end_page=doc['end_page']
                )
                db.session.add(vd)

        db.session.commit()
        print("Database commit successful")
        
        # Форматируем отклоненные документы для ответа
        formatted_rejected = []
        for rejected in result.get('rejected_document_ids', []):
            if isinstance(rejected, dict):
                formatted_rejected.append(rejected)
            else:
                formatted_rejected.append({'id': rejected, 'reason': 'Неизвестная причина'})
        
        return jsonify({
            'case_id': case.id,
            'volumes_count': len(result.get('volumes', [])),
            'has_partial_volume': partial_volume is not None,
            'rejected_documents': formatted_rejected,
            'message': f'Создано томов: {len(result.get("volumes", []))}. ' +
                       f'Частично заполненный том: {"Да" if partial_volume else "Нет"}. ' +
                       f'Отклонено документов: {len(formatted_rejected)}'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating case: {str(e)}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@api_cases.route('/cases/<int:case_id>/documents', methods=['PUT'])
@login_required
def add_documents_to_case(case_id):
    case = Case.query.get_or_404(case_id)
    if case.department_id != current_user.department_id and current_user.username != 'admin':
        return jsonify({'error': 'forbidden'}), 403

    payload = request.get_json() or {}
    documents_data = payload.get('documents', [])  # Теперь принимаем массив объектов с данными документов
    
    print("=== ADD DOCUMENTS TO CASE ===")
    print(f"Case ID: {case_id}")
    print(f"Documents data: {documents_data}")
    
    if not documents_data:
        return jsonify({'error': 'documents data required'}), 400
    
    # Извлекаем ID документов для проверки
    new_ids = [doc.get('id') for doc in documents_data if doc.get('id')]
    selection_order = [doc.get('id') for doc in documents_data]  # Порядок из массива
    
    # Проверяем, что документы не используются в других делах
    used_documents = check_documents_usage(new_ids, exclude_case_id=case_id)
    if used_documents:
        return jsonify({
            'error': 'Некоторые документы уже используются в других делах',
            'used_documents': used_documents
        }), 400

    # Находим текущий том (частично заполненный и не проверенный) или создаем новый
    current_volume = Volume.query.filter_by(
        case_id=case_id
    ).filter_by(is_verified=False).filter(Volume.pages_end < MAX_PAGES).order_by(Volume.number).first()
    
    # Если нет частично заполненного и не проверенного тома, создаем новый
    if not current_volume:
        # Находим максимальный номер тома
        max_volume = Volume.query.filter_by(case_id=case_id).order_by(Volume.number.desc()).first()
        next_volume_number = (max_volume.number + 1) if max_volume else 1
        
        print(f"Creating new volume {next_volume_number}")
        # Создаем новый том
        current_volume = Volume(
            case_id=case_id,
            number=next_volume_number,
            pages_start=1,
            pages_end=0,  # Пока пустой
            department_id=case.department_id
        )
        db.session.add(current_volume)
        db.session.flush()
    else:
        print(f"Using existing volume {current_volume.number} with {current_volume.total_pages} pages")
    
    # Получаем существующие документы в текущем томе
    existing_vds = VolumeDocument.query.filter_by(volume_id=current_volume.id)\
                                       .order_by(VolumeDocument.order_in_volume).all()
    existing_ids_in_volume = [vd.document_id for vd in existing_vds]
    
    # Фильтруем документы, которые уже есть в томе
    filtered_documents = []
    for doc_data in documents_data:
        doc_id = doc_data.get('id')
        if doc_id not in existing_ids_in_volume:
            filtered_documents.append(doc_data)
    
    print(f"Filtered documents (not in volume): {len(filtered_documents)}")
    
    # Если после фильтрации не осталось документов
    if not filtered_documents:
        return jsonify({
            'message': 'Все выбранные документы уже находятся в этом томе',
            'volume_id': current_volume.id,
            'volume_number': current_volume.number,
            'accepted_count': 0,
            'rejected_count': 0,
            'current_pages': current_volume.total_pages,
            'available_pages': MAX_PAGES - current_volume.total_pages
        }), 200
    
    # Создаем словарь с данными документов
    documents_map = {}
    for doc_data in filtered_documents:
        doc_id = doc_data.get('id')
        if doc_id:
            documents_map[doc_id] = {
                'pages': doc_data.get('pages_count', doc_data.get('pages', 0)),
                'title': doc_data.get('title', ''),
                'incoming_number': doc_data.get('incoming_number', ''),
                'outgoing_number': doc_data.get('outgoing_number', ''),
                'extra_info': doc_data.get('extra_info', ''),
                'selection_index': filtered_documents.index(doc_data) + 1
            }
    
    print(f"Documents map: {documents_map}")

    # Рассчитываем, какие документы поместятся в текущий том
    available_pages = MAX_PAGES - current_volume.total_pages
    accepted_docs = []
    rejected_docs = []
    
    current_total = current_volume.total_pages
    order_offset = len(existing_vds)
    
    print(f"Starting calculation. Current total: {current_total}, Available: {available_pages}")
    
    for doc_data in filtered_documents:  # В порядке из массива
        doc_id = doc_data.get('id')
        doc_info = documents_map.get(doc_id, {})
        pages = doc_info.get('pages', 0)
        selection_index = doc_info.get('selection_index', 0)
        
        print(f"Processing doc {doc_id}, pages: {pages}, selection order: {selection_index}")
        
        if not pages or pages <= 0:
            rejected_docs.append({
                'id': doc_id,
                'reason': 'Неверное количество страниц: ' + str(pages),
                'order': selection_index
            })
            continue
            
        if pages > MAX_PAGES:
            rejected_docs.append({
                'id': doc_id,
                'reason': f'Документ слишком большой: {pages} > {MAX_PAGES} стр.',
                'order': selection_index
            })
            continue
            
        if current_total + pages <= MAX_PAGES:
            # Документ помещается
            start_page = current_total + 1
            end_page = current_total + pages
            
            # Сохраняем порядок выбора
            current_order = order_offset + len(accepted_docs) + 1
            
            print(f"  Document fits! Adding at order {current_order}, pages {start_page}-{end_page}")
            
            # Добавляем связь документа с томом
            vd = VolumeDocument(
                volume_id=current_volume.id,
                document_id=doc_id,
                order_in_volume=current_order,
                start_page=start_page,
                end_page=end_page
            )
            db.session.add(vd)
            accepted_docs.append({
                'id': doc_id,
                'pages': pages,
                'start_page': start_page,
                'end_page': end_page,
                'order_in_volume': current_order,
                'selection_order': selection_index,
                'title': doc_info.get('title', '')
            })
            current_total += pages
        else:
            # Документ не помещается
            rejected_docs.append({
                'id': doc_id,
                'reason': f'Недостаточно места. Доступно: {MAX_PAGES - current_total} стр., требуется: {pages} стр.',
                'order': selection_index
            })
    
    # Обновляем информацию о томе
    if current_total > 0:
        current_volume.pages_end = current_total
    
    # Проверяем, заполнился ли том и нужно ли создавать новый для оставшихся документов
    volume_full = current_total == MAX_PAGES
    if volume_full and rejected_docs:
        print(f"Volume {current_volume.number} is full! Creating new volume for remaining documents")
        
        # Создаем новый том для оставшихся документов
        max_volume = Volume.query.filter_by(case_id=case_id).order_by(Volume.number.desc()).first()
        next_volume_number = max_volume.number + 1
        
        new_volume = Volume(
            case_id=case_id,
            number=next_volume_number,
            pages_start=1,
            pages_end=0,
            department_id=case.department_id
        )
        db.session.add(new_volume)
        db.session.flush()
        
        # Пробуем добавить оставшиеся документы в новый том
        remaining_docs = [doc for doc in rejected_docs if 'Недостаточно места' in doc['reason']]
        if remaining_docs:
            print(f"Trying to add {len(remaining_docs)} remaining docs to new volume {next_volume_number}")
            
            # Сбрасываем счетчики для нового тома
            new_current_total = 0
            new_accepted_docs = []
            new_rejected_docs = []
            new_order = 1
            
            for doc_info in remaining_docs:
                doc_id = doc_info['id']
                pages = documents_map.get(doc_id, {}).get('pages', 0)
                
                if pages and new_current_total + pages <= MAX_PAGES:
                    start_page = new_current_total + 1
                    end_page = new_current_total + pages
                    
                    vd = VolumeDocument(
                        volume_id=new_volume.id,
                        document_id=doc_id,
                        order_in_volume=new_order,
                        start_page=start_page,
                        end_page=end_page
                    )
                    db.session.add(vd)
                    
                    new_accepted_docs.append({
                        'id': doc_id,
                        'pages': pages,
                        'start_page': start_page,
                        'end_page': end_page,
                        'order_in_volume': new_order,
                        'selection_order': doc_info['order'],
                        'title': documents_map.get(doc_id, {}).get('title', '')
                    })
                    
                    new_current_total += pages
                    new_order += 1
                else:
                    new_rejected_docs.append(doc_info)
            
            # Обновляем новый том
            if new_current_total > 0:
                new_volume.pages_end = new_current_total
            
            # Обновляем списки принятых/отклоненных
            accepted_docs.extend(new_accepted_docs)
            rejected_docs = new_rejected_docs
    
    db.session.commit()
    
    # Сортируем принятые документы по порядку выбора для удобства отображения
    accepted_docs_sorted = sorted(accepted_docs, key=lambda x: x['selection_order'])
    
    return jsonify({
        'message': 'Документы добавлены',
        'volume_id': current_volume.id,
        'volume_number': current_volume.number,
        'accepted_count': len(accepted_docs),
        'rejected_count': len(rejected_docs),
        'accepted_documents': accepted_docs_sorted,
        'rejected_documents': rejected_docs,
        'current_pages': current_total,
        'available_pages': MAX_PAGES - current_total,
        'volume_full': volume_full,
        'volume_full_message': f'Том {current_volume.number} полностью заполнен ({MAX_PAGES} стр.)' if volume_full else None,
        'selection_order_preserved': True
    }), 200


@api_cases.route('/cases/<int:case_id>/preview-add', methods=['POST'])
@login_required
def preview_add_documents(case_id):
    """
    Предварительный расчет добавления документов в дело.
    Показывает, какие документы поместятся и в каком порядке.
    """
    case = Case.query.get_or_404(case_id)
    if case.department_id != current_user.department_id and current_user.username != 'admin':
        return jsonify({'error': 'forbidden'}), 403

    payload = request.get_json() or {}
    documents_data = payload.get('documents', [])
    
    if not documents_data:
        return jsonify({'error': 'documents data required'}), 400
    
    # Находим текущий том (частично заполненный и не проверенный)
    current_volume = Volume.query.filter_by(
        case_id=case_id
    ).filter_by(is_verified=False).filter(Volume.pages_end < MAX_PAGES).order_by(Volume.number).first()
    
    if not current_volume:
        # Если нет текущего тома, создаем виртуальный
        max_volume = Volume.query.filter_by(case_id=case_id).order_by(Volume.number.desc()).first()
        next_volume_number = (max_volume.number + 1) if max_volume else 1
        current_pages = 0
        free_pages = MAX_PAGES
    else:
        current_pages = current_volume.total_pages
        free_pages = MAX_PAGES - current_pages
        next_volume_number = current_volume.number
    
    # Предварительный расчет
    preview_accepted = []
    preview_rejected = []
    current_total = current_pages
    
    for doc_data in documents_data:
        doc_id = doc_data.get('id')
        pages = doc_data.get('pages_count', doc_data.get('pages', 0))
        selection_index = documents_data.index(doc_data) + 1
        
        if not pages or pages <= 0:
            preview_rejected.append({
                'id': doc_id,
                'reason': 'Неверное количество страниц: ' + str(pages),
                'order': selection_index
            })
            continue
            
        if pages > MAX_PAGES:
            preview_rejected.append({
                'id': doc_id,
                'reason': f'Документ слишком большой: {pages} > {MAX_PAGES} стр.',
                'order': selection_index
            })
            continue
            
        if current_total + pages <= MAX_PAGES:
            start_page = current_total + 1
            end_page = current_total + pages
            
            preview_accepted.append({
                'id': doc_id,
                'pages': pages,
                'start_page': start_page,
                'end_page': end_page,
                'selection_order': selection_index,
                'title': doc_data.get('title', '')
            })
            current_total += pages
        else:
            preview_rejected.append({
                'id': doc_id,
                'reason': f'Недостаточно места. Доступно: {MAX_PAGES - current_total} стр., требуется: {pages} стр.',
                'order': selection_index
            })
    
    return jsonify({
        'preview': True,
        'volume_number': next_volume_number,
        'current_pages': current_pages,
        'free_pages': free_pages,
        'after_addition_pages': current_total,
        'will_be_full': current_total == MAX_PAGES,
        'accepted_count': len(preview_accepted),
        'rejected_count': len(preview_rejected),
        'accepted_documents': sorted(preview_accepted, key=lambda x: x['selection_order']),
        'rejected_documents': preview_rejected,
        'message': f'Предварительный расчет: {len(preview_accepted)} документов поместятся, {len(preview_rejected)} - нет'
    }), 200


@api_cases.route('/volumes/<int:volume_id>', methods=['GET'])
@login_required
def get_volume_docs(volume_id):
    vol = Volume.query.get_or_404(volume_id)
    case = vol.case
    if case.department_id != current_user.department_id and current_user.username != 'admin':
        return jsonify({'error': 'forbidden'}), 403

    docs = []
    # Сортируем документы по order_in_volume
    sorted_documents = sorted(vol.documents, key=lambda vd: vd.order_in_volume)
    for vd in sorted_documents:
        docs.append({
            'document_id': vd.document_id,
            'title': vd.document.title,
            'incoming_number': vd.document.incoming_number,
            'outgoing_number': vd.document.outgoing_number,
            'extra_info': vd.document.extra_info,
            'start_page': vd.start_page,
            'end_page': vd.end_page,
            'order': vd.order_in_volume,
        })
    
    documents_count = len(docs)
    
    return jsonify({
        'volume_id': vol.id,
        'volume_number': vol.number,
        'name': f'Том {vol.number}',
        'total_pages': vol.total_pages,
        'pages_range': f'{vol.pages_start}-{vol.pages_end}',
        'documents_count': documents_count,
        'is_full': vol.total_pages == MAX_PAGES,
        'is_verified': vol.is_verified,
        'can_edit': not vol.is_verified,  # Можно редактировать любые непроверенные тома
        'verified_at': vol.verified_at.isoformat() if vol.verified_at else None,
        'verified_by': vol.verified_by,
        'verifier_name': vol.verifier.username if vol.verifier else None,
        'documents': docs
    })


@api_cases.route('/volumes/<int:volume_id>/edit', methods=['PUT'])
@login_required
def edit_volume_documents(volume_id):
    """
    Редактирование документов в томе (перетаскивание, изменение названия, количества страниц, удаление)
    """
    vol = Volume.query.get_or_404(volume_id)
    case = vol.case
    
    # Проверка прав доступа
    if case.department_id != current_user.department_id and current_user.username != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    
    # Проверка, можно ли редактировать том
    if vol.is_verified:
        return jsonify({'error': 'Том уже проверен и не может быть отредактирован'}), 400
    
    payload = request.get_json() or {}
    documents_data = payload.get('documents', [])  # Массив документов в новом порядке
    removed_document_ids = payload.get('removed_documents', [])  # ID документов для удаления
    
    if not documents_data:
        return jsonify({'error': 'documents data required'}), 400
    
    # Проверяем, что все документы существуют
    doc_ids = [doc.get('id') for doc in documents_data]
    existing_docs = Document.query.filter(Document.id.in_(doc_ids)).all()
    if len(existing_docs) != len(doc_ids):
        return jsonify({'error': 'Некоторые документы не найдены'}), 400
    
    # Проверяем, что удаляемые документы есть в томе
    current_doc_ids = [vd.document_id for vd in vol.documents]
    for doc_id in removed_document_ids:
        if doc_id not in current_doc_ids:
            return jsonify({'error': f'Документ {doc_id} не найден в этом томе'}), 400
    
    # Обновляем данные документов и собираем информацию для пересчета
    entries = []
    for doc_data in documents_data:
        doc_id = doc_data.get('id')
        doc = next((d for d in existing_docs if d.id == doc_id), None)
        if not doc:
            return jsonify({'error': f'Документ {doc_id} не найден'}), 400
        
        # Обновляем данные документа если они переданы
        if 'title' in doc_data:
            doc.title = doc_data['title']
        if 'pages_count' in doc_data:
            new_pages = int(doc_data['pages_count'])
            if new_pages < 1 or new_pages > MAX_PAGES:
                return jsonify({'error': f'Количество страниц должно быть от 1 до {MAX_PAGES}'}), 400
            doc.pages_count = new_pages
        if 'extra_info' in doc_data:
            doc.extra_info = doc_data['extra_info']
        
        entries.append({
            'document_id': doc.id,
            'pages_count': doc.pages_count
        })
    
    # Пересчитываем страницы
    updated_entries, total_pages, rejected = recalc_entries(entries)
    
    # Проверяем, что не превышен лимит страниц
    if total_pages > MAX_PAGES:
        # Находим документы, которые не поместились
        rejected_docs_info = []
        for doc_id in rejected:
            doc_data = next((d for d in documents_data if d.get('id') == doc_id), {})
            rejected_docs_info.append({
                'id': doc_id,
                'title': doc_data.get('title', f'Документ {doc_id}'),
                'reason': f'Не помещается в том. После редактирования будет превышен лимит {MAX_PAGES} страниц'
            })
        
        return jsonify({
            'error': f'После редактирования будет превышен лимит страниц: {total_pages} > {MAX_PAGES}',
            'total_pages': total_pages,
            'rejected_documents': rejected_docs_info,
            'can_save': False,
            'message': 'Некоторые документы не поместятся в том после редактирования'
        }), 400
    
    # Удаляем старые связи документов с томом
    VolumeDocument.query.filter_by(volume_id=vol.id).delete()
    
    # Создаем новые связи
    for i, entry in enumerate(updated_entries, 1):
        vd = VolumeDocument(
            volume_id=vol.id,
            document_id=entry['document_id'],
            order_in_volume=i,
            start_page=entry['start_page'],
            end_page=entry['end_page']
        )
        db.session.add(vd)
    
    # Обновляем информацию о томе
    vol.pages_start = 1
    vol.pages_end = total_pages
    
    # Если том стал полностью заполненным (250 стр.), добавляем отметку
    if total_pages == MAX_PAGES:
        # Можно добавить дополнительную логику, например уведомление
        pass
    
    db.session.commit()
    
    return jsonify({
        'message': 'Том успешно отредактирован',
        'volume_id': vol.id,
        'volume_number': vol.number,
        'total_pages': total_pages,
        'documents_count': len(updated_entries),
        'removed_count': len(removed_document_ids),
        'documents': updated_entries,
        'is_full': total_pages == MAX_PAGES,
        'is_verified': vol.is_verified
    }), 200


@api_cases.route('/volumes/<int:volume_id>/verify', methods=['POST'])
@login_required
def verify_volume(volume_id):
    """
    Подтверждение проверки тома
    """
    vol = Volume.query.get_or_404(volume_id)
    case = vol.case
    
    # Проверка прав доступа
    if case.department_id != current_user.department_id and current_user.username != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    
    # Проверка условий для подтверждения
    if vol.is_verified:
        return jsonify({'error': 'Том уже проверен'}), 400
    
    # Помечаем том как проверенный
    vol.is_verified = True
    vol.verified_at = datetime.utcnow()
    vol.verified_by = current_user.id
    
    # Создаем новый пустой том для этого дела (если он еще не создан и текущий том полный)
    if vol.total_pages == MAX_PAGES:
        existing_next_volume = Volume.query.filter_by(
            case_id=case.id,
            is_verified=False
        ).filter(Volume.pages_end < MAX_PAGES).order_by(Volume.number).first()
        
        if not existing_next_volume:
            max_volume = Volume.query.filter_by(case_id=case.id).order_by(Volume.number.desc()).first()
            next_volume_number = max_volume.number + 1
            
            new_volume = Volume(
                case_id=case.id,
                number=next_volume_number,
                pages_start=1,
                pages_end=0,  # Пустой том
                department_id=case.department_id
            )
            db.session.add(new_volume)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Том успешно проверен и подтвержден',
        'volume_id': vol.id,
        'volume_number': vol.number,
        'verified_at': vol.verified_at.isoformat(),
        'verified_by': current_user.username,
        'verifier_id': current_user.id,
        'new_volume_created': vol.total_pages == MAX_PAGES and not existing_next_volume if 'existing_next_volume' in locals() else False
    }), 200


@api_cases.route('/volumes/<int:volume_id>/preview-edit', methods=['POST'])
@login_required
def preview_edit_volume(volume_id):
    """
    Предварительный расчет редактирования тома
    """
    vol = Volume.query.get_or_404(volume_id)
    case = vol.case
    
    # Проверка прав доступа
    if case.department_id != current_user.department_id and current_user.username != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    
    # Проверка, можно ли редактировать том
    if vol.is_verified:
        return jsonify({'error': 'Том уже проверен и не может быть отредактирован'}), 400
    
    payload = request.get_json() or {}
    documents_data = payload.get('documents', [])
    removed_document_ids = payload.get('removed_documents', [])
    
    if not documents_data:
        return jsonify({'error': 'documents data required'}), 400
    
    # Создаем массив записей для пересчета
    entries = []
    for doc_data in documents_data:
        doc_id = doc_data.get('id')
        pages = doc_data.get('pages_count', doc_data.get('pages', 0))
        
        if not pages or pages <= 0:
            return jsonify({'error': f'Неверное количество страниц для документа {doc_id}'}), 400
        
        if pages > MAX_PAGES:
            return jsonify({'error': f'Документ слишком большой: {pages} > {MAX_PAGES} стр.'}), 400
        
        entries.append({
            'document_id': doc_id,
            'pages_count': pages
        })
    
    # Пересчитываем страницы
    updated_entries, total_pages, rejected = recalc_entries(entries)
    
    # Формируем информацию об отклоненных документах
    rejected_docs_info = []
    for doc_id in rejected:
        doc_data = next((d for d in documents_data if d.get('id') == doc_id), {})
        rejected_docs_info.append({
            'id': doc_id,
            'title': doc_data.get('title', f'Документ {doc_id}'),
            'reason': f'Не помещается в том. После редактирования будет превышен лимит {MAX_PAGES} страниц'
        })
    
    return jsonify({
        'preview': True,
        'total_pages': total_pages,
        'is_full': total_pages == MAX_PAGES,
        'can_save': total_pages <= MAX_PAGES and len(rejected) == 0,
        'updated_entries': updated_entries,
        'rejected': rejected,
        'rejected_documents': rejected_docs_info,
        'removed_count': len(removed_document_ids),
        'message': f'После редактирования: {total_pages} страниц, {len(updated_entries)} документов. ' +
                  f'{"Том полностью заполнен" if total_pages == MAX_PAGES else f"Свободно {MAX_PAGES - total_pages} страниц"}'
    }), 200


@api_cases.route('/documents/batch-update', methods=['POST'])
@login_required
def update_documents_batch():
    """
    Обновление данных нескольких документов перед добавлением в дело.
    """
    payload = request.get_json() or {}
    documents_data = payload.get('documents', [])
    
    if not documents_data:
        return jsonify({'error': 'documents data required'}), 400
    
    updated_documents = []
    
    for doc_data in documents_data:
        doc_id = doc_data.get('id')
        if not doc_id:
            continue
            
        doc = Document.query.get(doc_id)
        if not doc:
            continue
            
        # Обновляем поля документа если они переданы
        if 'title' in doc_data:
            doc.title = doc_data['title']
        if 'pages_count' in doc_data:
            doc.pages_count = int(doc_data['pages_count'])
        if 'incoming_number' in doc_data:
            doc.incoming_number = doc_data['incoming_number']
        if 'outgoing_number' in doc_data:
            doc.outgoing_number = doc_data['outgoing_number']
        if 'extra_info' in doc_data:
            doc.extra_info = doc_data['extra_info']
        
        updated_documents.append({
            'id': doc.id,
            'title': doc.title,
            'pages_count': doc.pages_count,
            'incoming_number': doc.incoming_number,
            'outgoing_number': doc.outgoing_number,
            'extra_info': doc.extra_info
        })
    
    db.session.commit()
    
    return jsonify({
        'message': f'Обновлено {len(updated_documents)} документов',
        'documents': updated_documents
    }), 200


def check_documents_usage(document_ids, exclude_case_id=None):
    """
    Проверяет, используются ли документы в других делах.
    Возвращает список документов, которые уже используются.
    """
    used_documents = []
    
    for doc_id in document_ids:
        vd = VolumeDocument.query.filter_by(document_id=doc_id).first()
        if vd:
            volume = Volume.query.get(vd.volume_id)
            if volume:
                case = Case.query.get(volume.case_id)
                if case and (exclude_case_id is None or case.id != exclude_case_id):
                    used_documents.append({
                        'document_id': doc_id,
                        'volume_id': volume.id,
                        'volume_number': volume.number,
                        'case_id': case.id,
                        'case_name': case.name,
                        'pages_in_volume': f"{vd.start_page}-{vd.end_page}"
                    })
    
    return used_documents