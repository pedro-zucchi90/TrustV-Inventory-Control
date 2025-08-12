# TrustV Inventory Control

## Visão Geral
O TrustV Inventory Control é um sistema de gestão de inventário e controle fiscal, desenvolvido para empresas que precisam de precisão e segurança na apuração de custos e impostos, conforme as normas da Receita Federal do Brasil.

---

### Backend
- [Flask](https://flask.palletsprojects.com/)
- [Flask-Login](https://flask-login.readthedocs.io/)
- [Flask-WTF](https://flask-wtf.readthedocs.io/)
- [Flask-Bcrypt](https://flask-bcrypt.readthedocs.io/)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- [SQLite](https://www.sqlite.org/index.html)

### Frontend
<a href="https://developer.mozilla.org/pt-BR/docs/Web/HTML"><img src="https://img.shields.io/badge/HTML5-%23E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5"></a>
<a href="https://developer.mozilla.org/pt-BR/docs/Web/CSS"><img src="https://img.shields.io/badge/CSS3-%231572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3"></a>
<a href="https://developer.mozilla.org/pt-BR/docs/Web/JavaScript"><img src="https://img.shields.io/badge/JavaScript-%23F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript"></a>

### Bibliotecas e Recursos
<a href="https://fontawesome.com/"><img src="https://img.shields.io/badge/Font_Awesome-%23339AF0?style=for-the-badge&logo=fontawesome&logoColor=white" alt="Font Awesome"></a>
<a href="https://fonts.google.com/"><img src="https://img.shields.io/badge/Google_Fonts-%234285F4?style=for-the-badge&logo=google&logoColor=white" alt="Google Fonts"></a>
<a href="https://getbootstrap.com/"><img src="https://img.shields.io/badge/Bootstrap-%237952B3?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap"></a>
<a href="https://www.chartjs.org/"><img src="https://img.shields.io/badge/Chart.js-%23FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white" alt="Chart.js"></a>

### Recursos JavaScript Utilizados
<img src="https://img.shields.io/badge/ES6+-%23F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="ES6+">
<img src="https://img.shields.io/badge/DOM_Manipulation-%23F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="DOM Manipulation">
<img src="https://img.shields.io/badge/Event_Listeners-%23F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="Event Listeners">
<img src="https://img.shields.io/badge/Intersection_Observer-%23F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="Intersection Observer">

---

## Estrutura do Projeto

```
/CadastroProdutos
│
├── app.py                # Arquivo principal do Flask
├── /models/              # Modelos do banco (SQLAlchemy)
│   ├── __init__.py
│   ├── produto.py        # Modelos de Produto, Estoque, etc.
│   ├── usuario.py        # Modelos de Usuário, Roles, Permissões
│   ├── movimentacao.py   # Modelos de Movimentação
│   ├── auditoria.py      # Modelos de Auditoria
│   ├── devolucao.py      # Modelo de Devolução de Venda
│
├── /forms_type/          # Formulários WTForms
│   ├── __init__.py
│   ├── login_form.py
│   ├── cadastro_produto_form.py
│   ├── movimentacao_form.py
│   ├── devolucao_form.py
│
├── /templates/           # Templates HTML (Jinja2)
│   ├── base.html
│   ├── login.html
│   ├── index.html        # Dashboard
│   ├── produtos.html
│   ├── relatorio_fiscal.html
│   ├── auditoria.html
│   ├── movimentacoes.html
│   ├── registrar_movimentacao.html
│   ├── registrar_devolucao.html
│   ├── devolucoes.html
│   ├── relatorio_geral_completo.html
│   ├── editar_conta.html
│
├── /static/              # Arquivos estáticos (CSS, imagens)
│   ├── css/
│   │   └── custom.css    # Estilos customizados do sistema
│   ├── profile_pics/
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
- Exportação de relatórios fiscais (CSV e PDF)
- API para preço médio dos produtos e preço médio geral
- Sistema de devolução de vendas integrado ao estoque
- Interface web responsiva e moderna
- **Navegação facilitada entre movimentações e devoluções**: Agora é possível acessar rapidamente a tela de devoluções a partir da tela de movimentações, com ajuste do endpoint para evitar erros de navegação.
- **Melhorias de usabilidade**: Ajustes em botões, tabelas e navegação para tornar o sistema mais intuitivo e eficiente.

## Usabilidade e Visual
- **Botões de ação rápida**: Centralizados, com tamanho consistente, espaçamento equilibrado entre ícone e texto, e largura adaptável ao grid. O texto é automaticamente reduzido se for muito longo, mantendo o layout limpo.
- **Responsividade**: Todos os componentes se adaptam a diferentes tamanhos de tela, inclusive botões e tabelas.
- **Contraste e acessibilidade**: Cores e espaçamentos otimizados para leitura e navegação.
- **Ajuste automático de fonte**: Botões e textos importantes nunca quebram o layout, mesmo com nomes grandes.

## Como Executar
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Crie o arquivo `config.py` na raiz do projeto, com por exemplo:
   ```python
   import os

   basedir = os.path.abspath(os.path.dirname(__file__))
   class Config:
       SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
       SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'instance', 'database.db')}"
       SQLALCHEMY_TRACK_MODIFICATIONS = False
   ```
   > Você pode personalizar a chave secreta e o nome do banco conforme sua necessidade.

3. O arquivo `config_fiscal.py` define as regras fiscais (impostos, despesas e CMV) e pode ser adaptado conforme sua operação.  
   Exemplo de trecho personalizável:
   ```python
   TAXA_IMPOSTOS_VENDAS = 0.18  # 18%
   TAXA_DESPESAS_ADMINISTRATIVAS = 0.02  # 2%
   TAXA_DESPESAS_COMERCIAIS = 0.03  # 3%
   # ...funções de cálculo...
   ```
   > Edite esse arquivo à vontade para ajustar as taxas e fórmulas ao seu negócio.

4. Execute o app:
   ```bash
   python app.py
   ```
5. Acesse em http://localhost:5000

## Diferenciais Fiscais
- Apuração do imposto sobre o lucro real, conforme custo atualizado do produto
- Relatórios prontos para auditoria e exportação
- Alertas automáticos de divergência fiscal
- Auditoria completa de ações
- Sistema de devolução de vendas com ajuste automático de estoque

---
Desenvolvido por TrustV. 
