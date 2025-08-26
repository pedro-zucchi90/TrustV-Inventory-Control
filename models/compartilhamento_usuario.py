"""Modelos de compartilhamento entre usuários.

Permite que usuários compartilhem dados com escopo configurável (ex.: 'all').
Vínculo único por par de usuários via UniqueConstraint.
"""
from . import db


class CompartilhamentoUsuario(db.Model):
    __tablename__ = 'compartilhamento_usuario'
    id = db.Column(db.Integer, primary_key=True)
    usuario_a_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)  # Usuário base
    usuario_b_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)  # Usuário com acesso
    escopo = db.Column(db.String(50), default='all')  # Escopo de dados compartilhados
    ativo = db.Column(db.Boolean, default=True)  # Ativo/inativo

    __table_args__ = (
        db.UniqueConstraint('usuario_a_id', 'usuario_b_id', name='uq_compartilhamento_usuarios'),
    )

    def __repr__(self):
        return f'<CompartUsr {self.usuario_a_id}<->{self.usuario_b_id} escopo={self.escopo} ativo={self.ativo}>'


