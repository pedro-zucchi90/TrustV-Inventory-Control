# Modelo Usuario: representa um usuário do sistema (login, permissões, etc)
from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import ForeignKey

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'  # Nome da tabela no banco de dados
    id = db.Column(db.Integer, primary_key=True)  # Identificador único do usuário
    nome = db.Column(db.String(150), nullable=False)  # Nome completo do usuário
    email = db.Column(db.String(150), unique=True, nullable=False)  # E-mail (login)
    senha_hash = db.Column(db.String(128), nullable=False)  # Hash da senha do usuário
    role = db.Column(db.String(50), default='vendedor')  # Papel do usuário (site_admin, administrador, vendedor, contador)
    foto_perfil = db.Column(db.String(255), nullable=True, default=None)  # Caminho da foto de perfil
    empresa_id = db.Column(db.Integer, ForeignKey('empresa.id'), nullable=True)  # Empresa à qual o usuário pertence

    def set_password(self, senha):
        """Define a senha do usuário (armazenando o hash)"""
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        """Verifica se a senha informada confere com o hash armazenado"""
        return check_password_hash(self.senha_hash, senha) 