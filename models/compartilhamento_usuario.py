from . import db


class CompartilhamentoUsuario(db.Model):
    __tablename__ = 'compartilhamento_usuario'
    id = db.Column(db.Integer, primary_key=True)
    usuario_a_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    usuario_b_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    escopo = db.Column(db.String(50), default='all')
    ativo = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.UniqueConstraint('usuario_a_id', 'usuario_b_id', name='uq_compartilhamento_usuarios'),
    )

    def __repr__(self):
        return f'<CompartUsr {self.usuario_a_id}<->{self.usuario_b_id} escopo={self.escopo} ativo={self.ativo}>'


