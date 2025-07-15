# Formulários principais do sistema (usuário, edição de conta, etc)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

# Importar formulários específicos para produtos, login, movimentação e devolução
from forms_type.cadastro_produto_form import CadastroProdutoForm
from forms_type.login_form import LoginForm
from forms_type.movimentacao_form import MovimentacaoForm
from forms_type.devolucao_form import DevolucaoForm

class CadastroUsuarioForm(FlaskForm):
    """Formulário para cadastro de novo usuário"""
    nome = StringField('Nome', validators=[DataRequired(), Length(min=2, max=50)])  # Nome completo
    email = StringField('E-mail', validators=[DataRequired(), Email()])  # E-mail válido
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])  # Senha (mínimo 6 caracteres)
    confirmar_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha', message='As senhas devem coincidir.')])  # Confirmação
    submit = SubmitField('Registrar')  # Botão de envio

class EditarUsuarioForm(FlaskForm):
    """Formulário para edição dos dados do usuário logado"""
    nome = StringField('Nome', validators=[DataRequired(), Length(min=2, max=50)])  # Nome completo
    email = StringField('E-mail', validators=[DataRequired(), Email()])  # E-mail válido
    senha = PasswordField('Nova Senha', validators=[Optional(), Length(min=6)])  # Nova senha (opcional)
    confirmar_senha = PasswordField('Confirmar Nova Senha', validators=[Optional(), EqualTo('senha', message='As senhas devem coincidir.')])  # Confirmação
    foto_perfil = FileField('Foto de Perfil', validators=[Optional()])  # Upload de foto de perfil
    submit = SubmitField('Salvar Alterações')  # Botão de envio 