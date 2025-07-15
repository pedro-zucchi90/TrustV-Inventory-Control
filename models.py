from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco_compra = db.Column(db.Float, nullable=False)
    preco_venda = db.Column(db.Float, nullable=False)
    quantidade_estoque = db.Column(db.Integer, default=0)
    movimentacoes = db.relationship('Movimentacao', backref='produto', lazy=True)

    def __repr__(self):
        return f'<Produto {self.nome}>'

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), default='usuario')

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

class Movimentacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # 'compra' ou 'venda'
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    # produto = db.relationship('Produto', backref='movimentacoes')  # Remover esta linha

class Auditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    acao = db.Column(db.String(100), nullable=False)
    entidade = db.Column(db.String(100), nullable=False)
    entidade_id = db.Column(db.Integer, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    detalhes = db.Column(db.Text)
    usuario = db.relationship('Usuario', backref='auditorias') 