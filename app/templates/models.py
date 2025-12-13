from .extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import CheckConstraint


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

    department = db.relationship('Department')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(1024))
    incoming_number = db.Column(db.String(255))
    outgoing_number = db.Column(db.String(255))
    pages_count = db.Column(db.Integer)
    extra_info = db.Column(db.Text)


class Case(db.Model):
    __tablename__ = 'cases'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    department = db.relationship('Department')
    volumes = db.relationship('Volume', backref='case', cascade='all, delete-orphan')


class Volume(db.Model):
    __tablename__ = 'volumes'
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    pages_start = db.Column(db.Integer, nullable=False)
    pages_end = db.Column(db.Integer, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)  # Новое поле: проверен ли том
    verified_at = db.Column(db.DateTime)  # Когда был проверен
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Кто проверил
    
    documents = db.relationship('VolumeDocument', backref='volume', cascade='all, delete-orphan', order_by='VolumeDocument.order_in_volume')
    verifier = db.relationship('User', foreign_keys=[verified_by])

    @property
    def name(self):
        return f'Том {self.number}'

    @property
    def total_pages(self):
        return self.pages_end - self.pages_start + 1
    
    @property
    def documents_count(self):
        """Количество документов в томе"""
        return len(self.documents)
    
    @property
    def is_full(self):
        """Полон ли том (250 страниц)"""
        return self.total_pages == 250


class VolumeDocument(db.Model):
    __tablename__ = 'volume_documents'
    id = db.Column(db.Integer, primary_key=True)
    volume_id = db.Column(db.Integer, db.ForeignKey('volumes.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    order_in_volume = db.Column(db.Integer, nullable=False)
    start_page = db.Column(db.Integer, nullable=False)
    end_page = db.Column(db.Integer, nullable=False)

    document = db.relationship('Document')