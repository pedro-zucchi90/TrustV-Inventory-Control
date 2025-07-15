# Modelo Auditoria: registra ações dos usuários para rastreabilidade e segurança
from . import db
from datetime import datetime

class Auditoria(db.Model):
    __tablename__ = 'auditoria'  # Nome da tabela no banco de dados
    id = db.Column(db.Integer, primary_key=True)  # Identificador único do log
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))  # Usuário que realizou a ação
    acao = db.Column(db.String(100), nullable=False)  # Tipo de ação (Cadastro, Edição, Exclusão, etc)
    entidade = db.Column(db.String(100), nullable=False)  # Entidade afetada (Produto, Usuário, etc)
    entidade_id = db.Column(db.Integer, nullable=False)  # ID da entidade afetada
    data = db.Column(db.DateTime, default=datetime.utcnow)  # Data/hora da ação
    detalhes = db.Column(db.Text)  # Detalhes adicionais da ação
    usuario = db.relationship('Usuario', backref='auditorias')  # Relacionamento com o usuário 