from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class DevolucaoForm(FlaskForm):
    movimentacao_id = SelectField('Venda Original', coerce=int, validators=[DataRequired()])
    quantidade_devolvida = IntegerField('Quantidade Devolvida', validators=[DataRequired(), NumberRange(min=1)])
    motivo_devolucao = TextAreaField('Motivo da Devolução', validators=[DataRequired()], render_kw={"rows": 3, "placeholder": "Descreva o motivo da devolução..."})
    submit = SubmitField('Registrar Devolução') 