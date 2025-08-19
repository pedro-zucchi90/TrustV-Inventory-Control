# Formulário para registrar movimentações de estoque (compra/venda)
from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, DecimalField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional

class MovimentacaoForm(FlaskForm):
    produto_id = SelectField('Produto', coerce=int, validators=[DataRequired()])  # Produto selecionado
    tipo = SelectField('Tipo', choices=[('compra', 'Compra'), ('venda', 'Venda')], validators=[DataRequired()])  # Tipo de movimentação
    quantidade = IntegerField('Quantidade', validators=[DataRequired(), NumberRange(min=1)])  # Quantidade movimentada
    valor_unitario = DecimalField('Valor Unitário (apenas para compras)', validators=[Optional(), NumberRange(min=0)])  # Valor unitário (compra)
    valor_venda = DecimalField('Valor de Venda (apenas para vendas)', validators=[Optional(), NumberRange(min=0)])  # Valor unitário (venda)
    percentual_desconto = DecimalField('Percentual de Desconto (%)', validators=[Optional(), NumberRange(min=0, max=100)], default=0)  # Desconto (venda)
    submit = SubmitField('Registrar')  # Botão de registro 