from . import db


class CompartilhamentoEmpresa(db.Model):
    __tablename__ = 'compartilhamento_empresa'
    id = db.Column(db.Integer, primary_key=True)
    empresa_a_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    empresa_b_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.UniqueConstraint('empresa_a_id', 'empresa_b_id', name='uq_compartilhamento_empresas'),
    )

    def __repr__(self):
        return f'<Compartilhamento {self.empresa_a_id}<->{self.empresa_b_id} ativo={self.ativo}>'


