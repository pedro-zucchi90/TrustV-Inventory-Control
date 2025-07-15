from . import db
from datetime import datetime

class Devolucao(db.Model):
    __tablename__ = 'devolucao'
    id = db.Column(db.Integer, primary_key=True)
    movimentacao_id = db.Column(db.Integer, db.ForeignKey('movimentacao.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade_devolvida = db.Column(db.Integer, nullable=False)
    motivo_devolucao = db.Column(db.String(200), nullable=False)
    valor_devolvido = db.Column(db.Float, nullable=False)  # valor total devolvido
    data_devolucao = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    # Relacionamentos
    movimentacao = db.relationship('Movimentacao', backref='devolucoes')
    produto = db.relationship('Produto', backref='devolucoes')
    usuario = db.relationship('Usuario', backref='devolucoes_registradas') 