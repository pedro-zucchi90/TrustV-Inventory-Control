from . import db


class Empresa(db.Model):
    __tablename__ = 'empresa'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), unique=True, nullable=False)
    cnpj = db.Column(db.String(32), nullable=True)

    def __repr__(self):
        return f'<Empresa {self.nome}>'


