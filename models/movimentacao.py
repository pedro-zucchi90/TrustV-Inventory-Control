# Modelo Movimentacao: representa uma movimentação de estoque (compra, venda ou devolução)
from . import db
from datetime import datetime

class Movimentacao(db.Model):
    __tablename__ = 'movimentacao'  # Nome da tabela no banco de dados
    id = db.Column(db.Integer, primary_key=True)  # Identificador único da movimentação
    tipo = db.Column(db.String(20), nullable=False)  # Tipo: 'compra', 'venda', 'devolucao'
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)  # Produto relacionado
    quantidade = db.Column(db.Integer, nullable=False)  # Quantidade movimentada
    valor_unitario = db.Column(db.Float, nullable=False)  # Valor unitário da movimentação
    custo_unitario = db.Column(db.Float, nullable=True)  # Custo do produto no momento da venda
    percentual_desconto = db.Column(db.Float, default=0.0)  # Percentual de desconto aplicado (venda)
    desconto_venda = db.Column(db.Float, default=0.0)  # Valor do desconto aplicado (venda)
    imposto_vendas = db.Column(db.Float, default=0.0)  # Valor dos impostos sobre a venda
    cmv = db.Column(db.Float, default=0.0)  # Custo das Mercadorias Vendidas
    despesas_administrativas = db.Column(db.Float, default=0.0)  # Despesas administrativas
    despesas_comerciais = db.Column(db.Float, default=0.0)  # Despesas comerciais
    data = db.Column(db.DateTime, default=datetime.utcnow)  # Data/hora da movimentação
    produto = db.relationship('Produto', backref='movimentacoes')  # Relacionamento com Produto 
    # Escopo por usuário (multi-tenant simples)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)