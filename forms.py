from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

class CadastroUsuarioForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha', message='As senhas devem coincidir.')])
    submit = SubmitField('Registrar')

class EditarUsuarioForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Nova Senha', validators=[Optional(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Nova Senha', validators=[Optional(), EqualTo('senha', message='As senhas devem coincidir.')])
    foto_perfil = FileField('Foto de Perfil', validators=[Optional()])
    submit = SubmitField('Salvar Alterações') 