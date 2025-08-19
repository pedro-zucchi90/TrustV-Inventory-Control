# Formulário para cadastro de produtos no sistema
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange

class CadastroProdutoForm(FlaskForm):
    nome = StringField('Nome do Produto', validators=[DataRequired()])  # Nome do produto
    descricao = TextAreaField('Descrição')  # Descrição detalhada
    preco_compra = DecimalField('Preço de Compra', validators=[DataRequired(), NumberRange(min=0)])  # Preço de compra
    preco_venda = DecimalField('Preço de Venda', validators=[DataRequired(), NumberRange(min=0)])  # Preço de venda
    quantidade_estoque = IntegerField('Quantidade em Estoque', validators=[DataRequired(), NumberRange(min=0)])  # Quantidade inicial
    submit = SubmitField('Cadastrar')  # Botão de cadastro 