# Modelos principais do sistema (versão alternativa, não utilizada diretamente)
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Produto(db.Model):
    """Modelo Produto: representa um item do estoque"""
    id = db.Column(db.Integer, primary_key=True)  # Identificador único
    nome = db.Column(db.String(150), nullable=False)  # Nome do produto
    descricao = db.Column(db.Text, nullable=True)  # Descrição
    preco_compra = db.Column(db.Float, nullable=False)  # Preço de compra
    preco_venda = db.Column(db.Float, nullable=False)  # Preço de venda
    quantidade_estoque = db.Column(db.Integer, default=0)  # Quantidade em estoque
    movimentacoes = db.relationship('Movimentacao', backref='produto', lazy=True)  # Movimentações relacionadas

    def __repr__(self):
        return f'<Produto {self.nome}>'

class Usuario(UserMixin, db.Model):
    """Modelo Usuario: representa um usuário do sistema"""
    id = db.Column(db.Integer, primary_key=True)  # Identificador único
    nome = db.Column(db.String(150), nullable=False)  # Nome
    email = db.Column(db.String(150), unique=True, nullable=False)  # E-mail
    senha_hash = db.Column(db.String(128), nullable=False)  # Hash da senha
    role = db.Column(db.String(50), default='usuario')  # Papel do usuário

    def set_password(self, senha):
        """Define a senha do usuário (armazenando o hash)"""
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        """Verifica se a senha informada confere com o hash armazenado"""
        return check_password_hash(self.senha_hash, senha)

class Movimentacao(db.Model):
    """Modelo Movimentacao: representa uma movimentação de estoque"""
    id = db.Column(db.Integer, primary_key=True)  # Identificador único
    tipo = db.Column(db.String(20), nullable=False)  # 'compra' ou 'venda'
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)  # Produto relacionado
    quantidade = db.Column(db.Integer, nullable=False)  # Quantidade movimentada
    valor_unitario = db.Column(db.Float, nullable=False)  # Valor unitário
    data = db.Column(db.DateTime, default=datetime.utcnow)  # Data/hora
    # produto = db.relationship('Produto', backref='movimentacoes')  # Remover esta linha

class Auditoria(db.Model):
    """Modelo Auditoria: registra ações dos usuários"""
    id = db.Column(db.Integer, primary_key=True)  # Identificador único
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))  # Usuário
    acao = db.Column(db.String(100), nullable=False)  # Tipo de ação
    entidade = db.Column(db.String(100), nullable=False)  # Entidade afetada
    entidade_id = db.Column(db.Integer, nullable=False)  # ID da entidade
    data = db.Column(db.DateTime, default=datetime.utcnow)  # Data/hora
    detalhes = db.Column(db.Text)  # Detalhes
    usuario = db.relationship('Usuario', backref='auditorias')  # Relacionamento 