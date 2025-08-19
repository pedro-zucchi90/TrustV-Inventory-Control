# Modelo Devolucao: representa uma devolução de venda, integrando com movimentação e produto
from . import db
from datetime import datetime

class Devolucao(db.Model):
    __tablename__ = 'devolucao'  # Nome da tabela no banco de dados
    id = db.Column(db.Integer, primary_key=True)  # Identificador único da devolução
    movimentacao_id = db.Column(db.Integer, db.ForeignKey('movimentacao.id'), nullable=False)  # Venda original
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)  # Produto devolvido
    quantidade_devolvida = db.Column(db.Integer, nullable=False)  # Quantidade devolvida
    motivo_devolucao = db.Column(db.String(200), nullable=False)  # Motivo da devolução
    valor_devolvido = db.Column(db.Float, nullable=False)  # Valor total devolvido
    data_devolucao = db.Column(db.DateTime, default=datetime.utcnow)  # Data/hora da devolução
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)  # Usuário que registrou
    
    # Relacionamentos
    movimentacao = db.relationship('Movimentacao', backref='devolucoes')  # Venda original
    produto = db.relationship('Produto', backref='devolucoes')  # Produto devolvido
    usuario = db.relationship('Usuario', backref='devolucoes_registradas')  # Usuário que registrou 