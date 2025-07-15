# Modelo Produto: representa um item do estoque no sistema
from . import db

class Produto(db.Model):
    __tablename__ = 'produto'  # Nome da tabela no banco de dados
    id = db.Column(db.Integer, primary_key=True)  # Identificador único do produto
    nome = db.Column(db.String(150), nullable=False)  # Nome do produto
    descricao = db.Column(db.Text, nullable=True)  # Descrição detalhada do produto
    preco_compra = db.Column(db.Float, nullable=False)  # Preço de compra do produto
    preco_venda = db.Column(db.Float, nullable=False)  # Preço de venda do produto
    quantidade_estoque = db.Column(db.Integer, default=0)  # Quantidade disponível em estoque

    def __repr__(self):
        return f'<Produto {self.nome}>'  # Representação legível para debug 