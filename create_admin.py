"""
Script simples para criar usuário administrador do sistema (site_admin)
Uso: python create_admin.py
"""

import os
import sys

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        from app import app, db
        from models.usuario import Usuario
        
        print("🚀 Criando usuário administrador do sistema...")
        
        with app.app_context():
            # Verifica se o site_admin já existe
            admin = Usuario.query.filter_by(email='site.admin@trustv.local').first()
            if admin:
                print("ℹ️  Usuário site_admin já existe")
                print(f"   Email: {admin.email}")
                print(f"   Role: {admin.role}")
                print(f"   Nome: {admin.nome}")
                return
            
            # Cria o usuário administrador do sistema
            admin = Usuario(
                nome='Site Admin',
                email='site.admin@trustv.local.com',
                role='site_admin',
                empresa_id=None  # site_admin não pertence a uma empresa específica
            )
            admin.set_password('admin123')
            
            db.session.add(admin)
            db.session.commit()
            
            print("✅ Usuário administrador do sistema criado com sucesso!")
            print("   📧 Email: site.admin@trustv.local.com")
            print("   🔑 Senha: admin123")
            print("   👤 Nome: Site Admin")
            print("   🔐 Role: site_admin (acesso total ao sistema)")
            print("   🏢 Empresa: Nenhuma (acesso global)")
            print("\n⚠️  IMPORTANTE: Altere a senha após o primeiro login!")
            print("\n💡 Este usuário tem acesso total ao sistema, incluindo:")
            print("   • Configuração de compartilhamento entre empresas")
            print("   • Todas as funcionalidades administrativas")
            print("   • Acesso a todas as empresas do sistema")
            
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("Certifique-se de que todas as dependências estão instaladas")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == '__main__':
    main()
