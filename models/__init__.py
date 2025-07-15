from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .produto import Produto
from .usuario import Usuario
from .movimentacao import Movimentacao
from .auditoria import Auditoria 