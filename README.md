# TrustV Inventory Control

![GitHub repo size](https://img.shields.io/github/repo-size/pedro-zucchi90/TrustV-Inventory-Control?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/pedro-zucchi90/TrustV-Inventory-Control?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-%23000?style=flat-square&logo=flask)

## Visão Geral
O **TrustV Inventory Control** é um sistema de gestão de inventário e controle fiscal, projetado para empresas que precisam de precisão e segurança na apuração de custos e impostos, conforme as normas da Receita Federal do Brasil.

---

## Tecnologias Utilizadas

### Backend
[![Flask](https://img.shields.io/badge/Flask-%23000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![Flask-Login](https://img.shields.io/badge/Flask_Login-%23000?style=for-the-badge&logo=flask)](https://flask-login.readthedocs.io/)
[![Flask-WTF](https://img.shields.io/badge/Flask_WTF-%23000?style=for-the-badge&logo=flask)](https://flask-wtf.readthedocs.io/)
[![Flask-Bcrypt](https://img.shields.io/badge/Flask_Bcrypt-%232C3E50?style=for-the-badge&logo=python&logoColor=white)](https://flask-bcrypt.readthedocs.io/)
[![Flask-SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-%23C68639?style=for-the-badge&logo=python&logoColor=white)](https://flask-sqlalchemy.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-%2307405e?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/index.html)

### Frontend
[![HTML5](https://img.shields.io/badge/HTML5-%23E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/pt-BR/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3-%231572B6?style=for-the-badge&logo=css3&logoColor=white)](https://developer.mozilla.org/pt-BR/docs/Web/CSS)
[![JavaScript](https://img.shields.io/badge/JavaScript-%23F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/pt-BR/docs/Web/JavaScript)

### Bibliotecas e Recursos
[![Font Awesome](https://img.shields.io/badge/Font_Awesome-%23339AF0?style=for-the-badge&logo=fontawesome&logoColor=white)](https://fontawesome.com/)
[![Google Fonts](https://img.shields.io/badge/Google_Fonts-%234285F4?style=for-the-badge&logo=google&logoColor=white)](https://fonts.google.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-%237952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Chart.js](https://img.shields.io/badge/Chart.js-%23FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)

---

## Estrutura do Projeto

```text
/CadastroProdutos
│
├── app.py                # Arquivo principal do Flask
├── /models/              # Modelos do banco (SQLAlchemy)
│   ├── produto.py
│   ├── usuario.py
│   ├── movimentacao.py
│   ├── auditoria.py
│   ├── devolucao.py
│
├── /forms_type/          # Formulários WTForms
│   ├── login_form.py
│   ├── cadastro_produto_form.py
│   ├── movimentacao_form.py
│   ├── devolucao_form.py
│
├── /templates/           # Templates HTML (Jinja2)
│   ├── base.html
│   ├── login.html
│   ├── index.html
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
│   │   └── custom.css
│   ├── profile_pics/
│
├── config.py             # Configurações do app
├── config_fiscal.py      # Regras fiscais customizáveis
├── requirements.txt
└── README.md
```

---

## Funcionalidades
- Cadastro e gestão de produtos
- Controle de estoque com métodos de custeio (FIFO, preço médio)
- Cálculo automático do lucro tributável
- Relatórios fiscais e alertas de divergência
- Autenticação de usuários (Flask-Login)
- Auditoria e rastreamento de alterações
- Exportação de relatórios fiscais (CSV/PDF)
- API para preço médio dos produtos e preço médio geral
- Sistema de devolução de vendas integrado ao estoque
- Interface web responsiva e moderna
- Navegação facilitada entre movimentações e devoluções
- Melhorias de usabilidade e acessibilidade

---

## Usabilidade e Visual
- **Botões de ação rápida** centralizados, tamanhos consistentes e layout adaptável.
- **Responsividade** para desktop e mobile.
- **Contraste e acessibilidade** otimizados.
- **Ajuste automático de fonte** para nomes e textos grandes.

---

## Como Executar

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. **Crie o arquivo `config.py` na raiz do projeto:**
   ```python
   import os

   basedir = os.path.abspath(os.path.dirname(__file__))
   class Config:
       SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
       SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'instance', 'database.db')}"
       SQLALCHEMY_TRACK_MODIFICATIONS = False
   ```
   > Você pode personalizar a chave secreta e o nome do banco conforme sua necessidade.

3. **Configuração fiscal personalizada**
   
   O arquivo `config_fiscal.py` centraliza as regras fiscais (impostos, despesas, CMV).  
   Edite livremente para adaptar o sistema à sua realidade.

   ```python
   TAXA_IMPOSTOS_VENDAS = 0.18  # 18%
   TAXA_DESPESAS_ADMINISTRATIVAS = 0.02  # 2%
   TAXA_DESPESAS_COMERCIAIS = 0.03  # 3%

   def calcular_impostos_vendas(valor_unitario, quantidade):
       return valor_unitario * quantidade * TAXA_IMPOSTOS_VENDAS
   # ... outras funções de cálculo ...
   ```

4. Execute o app:
   ```bash
   python app.py
   ```
5. Acesse em [http://localhost:5000](http://localhost:5000)

---

## Diferenciais Fiscais
- Apuração do imposto sobre o lucro real, conforme custo atualizado do produto
- Relatórios prontos para auditoria e exportação
- Alertas automáticos de divergência fiscal
- Auditoria completa de ações
- Sistema de devolução de vendas com ajuste automático de estoque

---

**Desenvolvido por TrustV.**
