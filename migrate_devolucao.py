from app import app, db
from models import Devolucao

def migrate_devolucao():
    with app.app_context():
        try:
            # Criar a tabela de devolução
            db.create_all()
            print("✅ Tabela de devolução criada com sucesso!")
            
            # Verificar se a tabela foi criada
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'devolucao' in tables:
                print("✅ Tabela 'devolucao' confirmada no banco de dados")
            else:
                print("❌ Erro: Tabela 'devolucao' não foi criada")
                
        except Exception as e:
            print(f"❌ Erro ao criar tabela de devolução: {e}")

if __name__ == '__main__':
    migrate_devolucao() 