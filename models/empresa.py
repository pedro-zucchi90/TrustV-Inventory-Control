from . import db


class Empresa(db.Model):
    """Modelo de Empresa: entidade que agrupa usuários e dados por organização.

    Observação: utiliza soft delete via coluna 'ativo' para desativação segura
    sem remover registros do banco, preservando histórico e integridade.
    """
    __tablename__ = 'empresa'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), unique=True, nullable=False)  # Nome fantasia/razão social (único)
    cnpj = db.Column(db.String(32), nullable=True)  # CNPJ opcional (texto livre para simplificar)
    ativo = db.Column(db.Boolean, default=True, nullable=False)  # Soft delete: True=ativa, False=inativa

    def __repr__(self):
        # Representação útil para logs e debug
        return f'<Empresa {self.nome} ativo={self.ativo}>'