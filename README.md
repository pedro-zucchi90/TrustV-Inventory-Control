# TrustV Inventory Control

## Visão Geral
O TrustV Inventory Control é um sistema de gestão de inventário e controle fiscal, desenvolvido para empresas que precisam de precisão e segurança na apuração de custos e impostos, conforme as normas da Receita Federal do Brasil.

## Estrutura do Projeto

```
/trustv_inventory_control
│
├── app.py                # Arquivo principal do Flask
├── /models/              # Modelos do banco (SQLAlchemy)
│   ├── __init__.py
│   ├── produto.py        # Modelos de Produto, Estoque, etc.
│   ├── usuario.py        # Modelos de Usuário, Roles, Permissões
│   ├── movimentacao.py   # Modelos de Movimentação
│   ├── auditoria.py      # Modelos de Auditoria
│
├── /forms/               # Formulários WTForms
│   ├── __init__.py
│   ├── login_form.py
│   ├── cadastro_produto_form.py
│   ├── movimentacao_form.py
│
├── /templates/           # Templates HTML (Jinja2)
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── produtos.html
│   ├── relatorio_fiscal.html
│   ├── auditoria.html
│   ├── movimentacoes.html
│   ├── registrar_movimentacao.html
│
├── /static/              # Arquivos estáticos (CSS, JS, fonts)
│   ├── css/
│   │   └── custom.css
│   ├── fonts/
│
├── config.py             # Configurações do app (banco, secret key, etc)
├── requirements.txt      # Dependências Python
└── README.md
```

## Funcionalidades
- Cadastro e gestão de produtos
- Controle de estoque com métodos de custeio (FIFO, preço médio)
- Cálculo automático do lucro tributável
- Relatórios fiscais e alertas de divergência
- Autenticação de usuários (Flask-Login)
- Auditoria e rastreamento de alterações
- Exportação de relatórios fiscais (CSV)
- API para preço médio dos produtos e preço médio geral
- Interface web responsiva

## Como Executar
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute o app:
   ```bash
   python app.py
   ```
3. Acesse em http://localhost:5000

## Diferenciais Fiscais
- Apuração do imposto sobre o lucro real, conforme custo atualizado do produto
- Relatórios prontos para auditoria e exportação
- Alertas automáticos de divergência fiscal
- Auditoria completa de ações

---
Desenvolvido por TrustV. 