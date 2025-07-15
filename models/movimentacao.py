from . import db
from datetime import datetime

class Movimentacao(db.Model):
    __tablename__ = 'movimentacao'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'compra' ou 'venda'
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False)
    custo_unitario = db.Column(db.Float, nullable=True)  # custo do produto no momento da venda
    data = db.Column(db.DateTime, default=datetime.utcnow)
    produto = db.relationship('Produto', backref='movimentacoes') 