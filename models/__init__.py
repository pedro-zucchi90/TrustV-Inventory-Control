# Inicialização do SQLAlchemy e importação dos modelos do sistema
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # Instância global do banco de dados

# Importação dos modelos para registro no SQLAlchemy
from .produto import Produto
from .usuario import Usuario
from .movimentacao import Movimentacao
from .auditoria import Auditoria
from .devolucao import Devolucao 
from .empresa import Empresa
from .compartilhamento import CompartilhamentoEmpresa
from .compartilhamento_usuario import CompartilhamentoUsuario