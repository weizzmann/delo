from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from ..models import Document, VolumeDocument, Volume, Case, Department
from ..extensions import db

api_documents = Blueprint('api_documents', __name__)


@api_documents.route('/documents', methods=['GET'])
@login_required
def get_documents():
    # Simple server-side pagination & search compatible with DataTables
    try:
        start = int(request.args.get('start', 0))
        length = int(request.args.get('length', 25))
    except ValueError:
        start = 0
        length = 25

    search = request.args.get('search[value]') or request.args.get('q')

    q = Document.query
    if search:
        term = f"%{search}%"
        q = q.filter((Document.title.ilike(term)) | 
                     (Document.incoming_number.ilike(term)) | 
                     (Document.outgoing_number.ilike(term)))

    total = q.count()
    items = q.offset(start).limit(length).all()

    data = []
    for d in items:
        # Проверяем, в каком деле и томе находится документ
        location_info = get_document_location(d.id)
        
        data.append({
            'id': d.id,
            'title': d.title,
            'incoming_number': d.incoming_number,
            'outgoing_number': d.outgoing_number,
            'pages_count': d.pages_count,
            'extra_info': d.extra_info,
            'location': location_info
        })

    return jsonify({
        'recordsTotal': total,
        'recordsFiltered': total,
        'data': data,
    })


@api_documents.route('/documents/batch', methods=['GET'])
@login_required
def get_documents_batch():
    """Получить информацию о нескольких документах по их ID (сохраняет порядок)"""
    ids_param = request.args.get('ids', '')
    if not ids_param:
        return jsonify({'error': 'ids parameter required'}), 400
    
    try:
        # Парсим ID документов в том порядке, в котором они переданы
        ids = [int(id_str.strip()) for id_str in ids_param.split(',') if id_str.strip()]
    except ValueError:
        return jsonify({'error': 'Invalid document IDs'}), 400
    
    if not ids:
        return jsonify({'error': 'No valid document IDs provided'}), 400
    
    # Получаем документы в порядке, указанном пользователем
    documents = []
    for doc_id in ids:
        doc = Document.query.get(doc_id)
        if doc:
            location_info = get_document_location(doc_id)
            documents.append({
                'id': doc.id,
                'title': doc.title,
                'incoming_number': doc.incoming_number,
                'outgoing_number': doc.outgoing_number,
                'pages_count': doc.pages_count,
                'extra_info': doc.extra_info,
                'location': location_info,
                'order': ids.index(doc_id) + 1  # Сохраняем порядок выбора
            })
        else:
            documents.append({
                'id': doc_id,
                'error': 'Document not found',
                'order': ids.index(doc_id) + 1
            })
    
    return jsonify({
        'documents': documents,
        'total': len(documents)
    })


def get_document_location(document_id):
    """
    Возвращает информацию о местоположении документа.
    Если документ не используется ни в одном деле - возвращает None.
    """
    vd = VolumeDocument.query.filter_by(document_id=document_id).first()
    if not vd:
        return None
    
    volume = Volume.query.get(vd.volume_id)
    if not volume:
        return None
    
    case = Case.query.get(volume.case_id)
    if not case:
        return None
    
    department = Department.query.get(case.department_id)
    
    return {
        'case_id': case.id,
        'case_name': case.name,
        'volume_id': volume.id,
        'volume_number': volume.number,
        'pages_in_volume': f"{vd.start_page}-{vd.end_page}",
        'department_id': department.id if department else None,
        'department_name': department.name if department else None
    }


@api_documents.route('/documents/<int:document_id>/location', methods=['GET'])
@login_required
def get_document_location_api(document_id):
    """API для получения информации о местоположении конкретного документа"""
    location = get_document_location(document_id)
    if location:
        return jsonify(location)
    else:
        return jsonify({'message': 'Документ не используется ни в одном деле'}), 404