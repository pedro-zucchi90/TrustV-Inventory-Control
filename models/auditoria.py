from . import db
from datetime import datetime

class Auditoria(db.Model):
    __tablename__ = 'auditoria'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    acao = db.Column(db.String(100), nullable=False)
    entidade = db.Column(db.String(100), nullable=False)
    entidade_id = db.Column(db.Integer, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    detalhes = db.Column(db.Text)
    usuario = db.relationship('Usuario', backref='auditorias') 