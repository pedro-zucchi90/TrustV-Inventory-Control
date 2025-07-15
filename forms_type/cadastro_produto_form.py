from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange

class CadastroProdutoForm(FlaskForm):
    nome = StringField('Nome do Produto', validators=[DataRequired()])
    descricao = TextAreaField('Descrição')
    preco_compra = DecimalField('Preço de Compra', validators=[DataRequired(), NumberRange(min=0)])
    preco_venda = DecimalField('Preço de Venda', validators=[DataRequired(), NumberRange(min=0)])
    quantidade_estoque = IntegerField('Quantidade em Estoque', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Cadastrar') 