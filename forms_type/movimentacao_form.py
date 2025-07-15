from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, DecimalField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional

class MovimentacaoForm(FlaskForm):
    produto_id = SelectField('Produto', coerce=int, validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[('compra', 'Compra'), ('venda', 'Venda')], validators=[DataRequired()])
    quantidade = IntegerField('Quantidade', validators=[DataRequired(), NumberRange(min=1)])
    valor_unitario = DecimalField('Valor Unitário (apenas para compras)', validators=[Optional(), NumberRange(min=0)])
    valor_venda = DecimalField('Valor de Venda (apenas para vendas)', validators=[Optional(), NumberRange(min=0)])
    percentual_desconto = DecimalField('Percentual de Desconto (%)', validators=[Optional(), NumberRange(min=0, max=100)], default=0)
    submit = SubmitField('Registrar') 