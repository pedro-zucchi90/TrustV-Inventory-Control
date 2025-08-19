# Formulário de login de usuário
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired()])  # E-mail do usuário
    senha = PasswordField('Senha', validators=[DataRequired()])  # Senha do usuário
    submit = SubmitField('Entrar')  # Botão de login 