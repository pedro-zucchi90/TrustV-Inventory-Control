from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), default='usuario')
    foto_perfil = db.Column(db.String(255), nullable=True, default=None)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha) 