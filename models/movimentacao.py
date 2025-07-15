from . import db
from datetime import datetime

class Movimentacao(db.Model):
    __tablename__ = 'movimentacao'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'compra', 'venda', 'devolucao'
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False)
    custo_unitario = db.Column(db.Float, nullable=True)  # custo do produto no momento da venda
    percentual_desconto = db.Column(db.Float, default=0.0)  # percentual de desconto aplicado
    desconto_venda = db.Column(db.Float, default=0.0)  # desconto sobre venda
    imposto_vendas = db.Column(db.Float, default=0.0)  # imposto sobre vendas
    cmv = db.Column(db.Float, default=0.0)  # Custo das Mercadorias Vendidas
    despesas_administrativas = db.Column(db.Float, default=0.0)  # despesas administrativas
    despesas_comerciais = db.Column(db.Float, default=0.0)  # despesas comerciais
    data = db.Column(db.DateTime, default=datetime.utcnow)
    produto = db.relationship('Produto', backref='movimentacoes') 