"""Modelos de compartilhamento entre empresas.

Registra pares de empresas que podem compartilhar dados entre si. O vínculo é
simétrico (A<->B) e único por par via UniqueConstraint.
"""
from . import db


class CompartilhamentoEmpresa(db.Model):
    __tablename__ = 'compartilhamento_empresa'
    id = db.Column(db.Integer, primary_key=True)
    empresa_a_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)  # Empresa base
    empresa_b_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)  # Empresa que recebe/acessa
    ativo = db.Column(db.Boolean, default=True)  # Ativo/inativo

    __table_args__ = (
        db.UniqueConstraint('empresa_a_id', 'empresa_b_id', name='uq_compartilhamento_empresas'),
    )

    def __repr__(self):
        return f'<Compartilhamento {self.empresa_a_id}<->{self.empresa_b_id} ativo={self.ativo}>'


