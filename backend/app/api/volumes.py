
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from ..services.volume_calculator import calculate_volume_structure
from ..models import Volume, VolumeDocument, Document
from ..extensions import db

api_volumes = Blueprint('api_volumes', __name__)


@api_volumes.route('/volumes/calculate-preview', methods=['POST'])
@login_required
def calculate_preview():
    payload = request.get_json() or {}
    ids = payload.get('document_ids') or []
    if not isinstance(ids, list):
        return jsonify({'error': 'document_ids must be a list'}), 400

    docs = Document.query.filter(Document.id.in_(ids)).all()
    pages_map = {d.id: d.pages_count for d in docs}

    result = calculate_volume_structure(ids, pages_map)
    
    # Форматируем результат для отображения
    formatted_volumes = []
    for vol in result['volumes']:
        formatted_volumes.append({
            'volume_number': vol['volume_number'],
            'total_pages': vol['total_pages'],
            'documents_count': len(vol['documents']),
            'is_full': vol['total_pages'] == 250,
            'documents': vol['documents']
        })
    
    return jsonify({
        'volumes': formatted_volumes,
        'rejected_document_ids': result['rejected_document_ids']
    })


@api_volumes.route('/volumes/<int:volume_id>', methods=['GET'])
@login_required
def get_volume_details(volume_id):
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
            'start_page': vd.start_page,  # Страница в томе (1-250)
            'end_page': vd.end_page,      # Страница в томе (1-250)
            'order': vd.order_in_volume,
        })
    
    # Подсчитываем количество документов
    documents_count = len(docs)
    
    return jsonify({
        'volume_id': vol.id,
        'volume_number': vol.number,
        'name': f'Том {vol.number}',
        'total_pages': vol.total_pages,
        'pages_range': f'{vol.pages_start}-{vol.pages_end}',
        'documents_count': documents_count,
        'documents': docs
    })