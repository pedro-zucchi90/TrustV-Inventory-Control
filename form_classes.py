from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, SubmitField, TextAreaField, PasswordField, SelectField
from wtforms.validators import DataRequired, NumberRange, EqualTo, Length
from flask_wtf.file import FileField, FileAllowed

class CadastroProdutoForm(FlaskForm):
    nome = StringField('Nome do Produto', validators=[DataRequired()])
    descricao = TextAreaField('Descrição')
    preco_compra = DecimalField('Preço de Compra', validators=[DataRequired(), NumberRange(min=0)])
    preco_venda = DecimalField('Preço de Venda', validators=[DataRequired(), NumberRange(min=0)])
    quantidade_estoque = IntegerField('Quantidade em Estoque', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Cadastrar')

class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class MovimentacaoForm(FlaskForm):
    produto_id = SelectField('Produto', coerce=int, validators=[DataRequired()])
    tipo = SelectField('Tipo', choices=[('compra', 'Compra'), ('venda', 'Venda')], validators=[DataRequired()])
    quantidade = IntegerField('Quantidade', validators=[DataRequired(), NumberRange(min=1)])
    valor_unitario = DecimalField('Valor Unitário', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Registrar')

class CadastroUsuarioForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6, message='A senha deve ter pelo menos 6 caracteres.')])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha', message='As senhas não coincidem.')])
    submit = SubmitField('Registrar')

class EditarUsuarioForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired()])
    foto_perfil = FileField('Foto de Perfil', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens são permitidas!')])
    senha = PasswordField('Nova Senha')
    confirmar_senha = PasswordField('Confirmar Nova Senha', validators=[EqualTo('senha', message='As senhas não coincidem.')])
    submit = SubmitField('Salvar Alterações')