from flask import Flask, render_template, redirect, url_for, flash, request, Response, jsonify, make_response
import csv
from flask_sqlalchemy import SQLAlchemy
from models import db, Produto
from forms_type import CadastroProdutoForm, LoginForm, MovimentacaoForm
from config import Config
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import Usuario
from models import Auditoria
import os
from werkzeug.utils import secure_filename
from models import Movimentacao
from datetime import datetime
from sqlalchemy import extract
from forms import CadastroUsuarioForm, EditarUsuarioForm
# Removido WeasyPrint
import pdfkit

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data).first()
        if usuario and usuario.check_password(form.senha.data):
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('E-mail ou senha incorretos.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@app.route('/index')
@login_required
def index():
    produtos = Produto.query.all()
    def custo_medio(produto):
        compras = [m for m in produto.movimentacoes if m.tipo == 'compra']
        total_qtd = sum(m.quantidade for m in compras)
        total_valor = sum(m.quantidade * m.valor_unitario for m in compras)
        return (total_valor / total_qtd) if total_qtd > 0 else 0
    total_estoque = sum(p.quantidade_estoque for p in produtos)
    valor_estoque = sum(max(p.quantidade_estoque, 0) * p.preco_compra for p in produtos)

    mes = datetime.now().month
    ano = datetime.now().year
    vendas_mes = Movimentacao.query.filter_by(tipo='venda').filter(extract('month', Movimentacao.data)==mes, extract('year', Movimentacao.data)==ano).all()
    margem_lucro = 0
    for venda in vendas_mes:
        # Usar sempre o custo_unitario salvo na movimentação, nunca o preco_compra atual
        custo = venda.custo_unitario if venda.custo_unitario is not None else 0
        margem_lucro += (venda.valor_unitario - custo) * venda.quantidade

    alertas = []
    for venda in vendas_mes:
        produto = Produto.query.get(venda.produto_id)
        if venda.valor_unitario < custo_medio(produto):
            alertas.append({
                'produto': produto.nome,
                'data': venda.data.strftime('%d/%m/%Y'),
                'id': produto.id
            })

    divergencias = []
    for produto in produtos:
        # Divergência de venda abaixo do custo médio
        vendas_produto = [m for m in produto.movimentacoes if m.tipo == 'venda']
        for venda in vendas_produto:
            if venda.valor_unitario < custo_medio(produto):
                compras = [m for m in produto.movimentacoes if m.tipo == 'compra']
                total_qtd = sum(m.quantidade for m in compras)
                total_valor = sum(m.quantidade * m.valor_unitario for m in compras)
                custo_medio_prod = (total_valor / total_qtd) if total_qtd > 0 else 0
                divergencias.append({
                    'produto': produto.nome,
                    'id': produto.id,
                    'custo_ultima': produto.preco_compra,
                    'custo_medio': custo_medio_prod,
                    'preco_venda': produto.preco_venda,
                    'tipo': 'venda_abaixo_custo',
                    'diferenca_compra': None
                })
                break
        # Divergência de preço de compra (última compra diferente da penúltima)
        compras_produto = [m for m in produto.movimentacoes if m.tipo == 'compra']
        compras_produto = sorted(compras_produto, key=lambda x: x.data, reverse=True)
        if len(compras_produto) >= 2:
            ultima = compras_produto[0]
            penultima = compras_produto[1]
            if abs(ultima.valor_unitario - penultima.valor_unitario) > 0.01:
                divergencias.append({
                    'produto': produto.nome,
                    'id': produto.id,
                    'custo_ultima': ultima.valor_unitario,
                    'custo_penultima': penultima.valor_unitario,
                    'custo_medio': custo_medio(produto),
                    'preco_venda': produto.preco_venda,
                    'tipo': 'compra_diferente',
                    'diferenca_compra': ultima.valor_unitario - penultima.valor_unitario
                })

    ultimas_transacoes = Movimentacao.query.order_by(Movimentacao.data.desc()).limit(5).all()

    from calendar import month_abbr
    labels = []
    data_lucro = []
    for i in range(5, -1, -1):
        mes_ref = (datetime.now().month - i - 1) % 12 + 1
        ano_ref = datetime.now().year if datetime.now().month - i > 0 else datetime.now().year - 1
        vendas = Movimentacao.query.filter_by(tipo='venda').filter(extract('month', Movimentacao.data)==mes_ref, extract('year', Movimentacao.data)==ano_ref).all()
        lucro = 0
        for venda in vendas:
            produto = Produto.query.get(venda.produto_id)
            custo = venda.custo_unitario if venda.custo_unitario is not None else custo_medio(produto)
            lucro += (venda.valor_unitario - custo) * venda.quantidade
        labels.append(month_abbr[mes_ref].capitalize())
        data_lucro.append(lucro)

    return render_template('index.html',
        produtos=produtos,
        total_estoque=total_estoque,
        valor_estoque=valor_estoque,
        margem_lucro=margem_lucro,
        alertas=alertas,
        divergencias=divergencias,
        ultimas_transacoes=ultimas_transacoes,
        grafico_labels=labels,
        grafico_lucro=data_lucro
    )

# Adicionar auditoria ao cadastrar produto
@app.route('/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_produto():
    form = CadastroProdutoForm()
    if form.validate_on_submit():
        novo_produto = Produto(
            nome=form.nome.data,
            descricao=form.descricao.data,
            preco_compra=float(form.preco_compra.data),
            preco_venda=float(form.preco_venda.data),
            quantidade_estoque=form.quantidade_estoque.data
        )
        db.session.add(novo_produto)
        db.session.commit()
        # Adiciona movimentação de compra automática para o estoque inicial
        if novo_produto.quantidade_estoque > 0:
            movimentacao_inicial = Movimentacao(
                produto_id=novo_produto.id,
                tipo='compra',
                quantidade=novo_produto.quantidade_estoque,
                valor_unitario=novo_produto.preco_compra,
                custo_unitario=None
            )
            db.session.add(movimentacao_inicial)
            db.session.commit()
        auditoria = Auditoria(
            usuario_id=current_user.id,
            acao='Cadastro',
            entidade='Produto',
            entidade_id=novo_produto.id,
            detalhes=f'Produto cadastrado: {novo_produto.nome}'
        )
        db.session.add(auditoria)
        db.session.commit()
        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('add_product.html', form=form)

# Adicionar auditoria ao editar produto
@app.route('/editar/<int:produto_id>', methods=['GET', 'POST'])
@login_required
def editar_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    form = CadastroProdutoForm(obj=produto)
    if form.validate_on_submit():
        produto.nome = form.nome.data
        produto.descricao = form.descricao.data
        produto.preco_compra = float(form.preco_compra.data)
        produto.preco_venda = float(form.preco_venda.data)
        produto.quantidade_estoque = form.quantidade_estoque.data
        db.session.commit()
        auditoria = Auditoria(
            usuario_id=current_user.id,
            acao='Edição',
            entidade='Produto',
            entidade_id=produto.id,
            detalhes=f'Produto editado: {produto.nome}'
        )
        db.session.add(auditoria)
        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('edit_product.html', form=form, produto=produto)

# Adicionar auditoria ao excluir produto
@app.route('/deletar/<int:produto_id>', methods=['POST'])
@login_required
def deletar_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    db.session.delete(produto)
    db.session.commit()
    auditoria = Auditoria(
        usuario_id=current_user.id,
        acao='Exclusão',
        entidade='Produto',
        entidade_id=produto.id,
        detalhes=f'Produto excluído: {produto.nome}'
    )
    db.session.add(auditoria)
    db.session.commit()
    flash('Produto removido com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/movimentacoes', methods=['GET'])
@login_required
def listar_movimentacoes():
    movimentacoes = Movimentacao.query.order_by(Movimentacao.data.desc()).all()
    return render_template('movimentacoes.html', movimentacoes=movimentacoes)

# Adicionar auditoria ao registrar movimentação
@app.route('/registrar_movimentacao', methods=['GET', 'POST'])
@login_required
def registrar_movimentacao():
    tipo_param = request.args.get('tipo')
    form = MovimentacaoForm()
    if tipo_param in ['compra', 'venda'] and request.method == 'GET':
        form.tipo.data = tipo_param
    form.produto_id.choices = [(p.id, p.nome) for p in Produto.query.all()]
    if form.validate_on_submit():
        produto = Produto.query.get(form.produto_id.data)
        if form.tipo.data == 'venda':
            if form.quantidade.data > produto.quantidade_estoque:
                flash('Não é possível vender mais do que o estoque disponível!', 'danger')
                return redirect(url_for('registrar_movimentacao', tipo='venda'))
            if not form.valor_venda.data or float(form.valor_venda.data) <= 0:
                flash('Informe o valor de venda!', 'danger')
                return redirect(url_for('registrar_movimentacao', tipo='venda'))
            
            # Implementar FIFO para cálculo do custo
            quantidade_vendida = form.quantidade.data
            custo_total_venda = 0
            quantidade_restante = quantidade_vendida
            
            # Buscar compras ordenadas por data (mais antigas primeiro) e preço (menor primeiro)
            compras = Movimentacao.query.filter_by(
                produto_id=form.produto_id.data, 
                tipo='compra'
            ).order_by(Movimentacao.valor_unitario.asc(), Movimentacao.data.asc()).all()
            
            for compra in compras:
                if quantidade_restante <= 0:
                    break
                    
                # Calcular quanto usar desta compra
                quantidade_usar = min(quantidade_restante, compra.quantidade)
                custo_total_venda += quantidade_usar * compra.valor_unitario
                quantidade_restante -= quantidade_usar
            
            # Se ainda há quantidade restante, usar o preço de compra atual
            if quantidade_restante > 0:
                custo_total_venda += quantidade_restante * produto.preco_compra
            
            # Calcular custo unitário médio da venda
            custo_unitario = custo_total_venda / quantidade_vendida if quantidade_vendida > 0 else 0
            
            valor_unitario = float(form.valor_venda.data)
            print(f'Registrando VENDA FIFO: produto={produto.nome}, quantidade={quantidade_vendida}, custo_total={custo_total_venda}, custo_unitario={custo_unitario}')
        else:
            custo_unitario = None
            valor_unitario = float(form.valor_unitario.data)
        mov = Movimentacao(
            produto_id=form.produto_id.data,
            tipo=form.tipo.data,
            quantidade=form.quantidade.data,
            valor_unitario=valor_unitario,
            custo_unitario=custo_unitario
        )
        if form.tipo.data == 'compra':
            produto.quantidade_estoque += form.quantidade.data
            produto.preco_compra = float(form.valor_unitario.data)
        elif form.tipo.data == 'venda':
            produto.quantidade_estoque -= form.quantidade.data
        db.session.add(mov)
        db.session.commit()
        auditoria = Auditoria(
            usuario_id=current_user.id,
            acao='Movimentação',
            entidade='Produto',
            entidade_id=produto.id,
            detalhes=f'{mov.tipo.capitalize()} de {mov.quantidade} unidade(s) do produto {produto.nome} por R$ {mov.valor_unitario}'
        )
        db.session.add(auditoria)
        db.session.commit()
        flash('Movimentação registrada com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('registrar_movimentacao.html', form=form)

@app.route('/relatorio_fiscal')
@login_required
def relatorio_fiscal():
    # Margem de lucro do mês atual
    mes = datetime.now().month
    ano = datetime.now().year
    vendas = Movimentacao.query.filter_by(tipo='venda').filter(extract('month', Movimentacao.data)==mes, extract('year', Movimentacao.data)==ano).all()
    margem_lucro = 0
    for venda in vendas:
        # Usar sempre o custo_unitario salvo na movimentação, nunca o preco_compra atual
        custo = venda.custo_unitario if venda.custo_unitario is not None else 0
        margem_lucro += (venda.valor_unitario - custo) * venda.quantidade
    return render_template('relatorio_fiscal.html', vendas=vendas, margem_lucro=margem_lucro)

@app.route('/exportar_relatorio_fiscal')
@login_required
def exportar_relatorio_fiscal():
    mes = datetime.now().month
    ano = datetime.now().year
    vendas = Movimentacao.query.filter_by(tipo='venda').filter(extract('month', Movimentacao.data)==mes, extract('year', Movimentacao.data)==ano).all()
    def generate():
        data = [['Data', 'Produto', 'Quantidade', 'Valor Unitário (Venda)', 'Custo Salvo', 'Margem de Lucro']]
        for venda in vendas:
            produto = Produto.query.get(venda.produto_id)
            custo = venda.custo_unitario if venda.custo_unitario is not None else 0
            linha = [
                venda.data.strftime('%d/%m/%Y %H:%M'),
                produto.nome,
                venda.quantidade,
                venda.valor_unitario,
                custo,
                (venda.valor_unitario - custo) * venda.quantidade
            ]
            data.append(linha)
        output = ''
        for row in data:
            output += ';'.join(map(str, row)) + '\n'
        return output
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=relatorio_fiscal.csv"})

@app.context_processor
def inject_alertas_fiscais():
    alertas = []
    vendas = Movimentacao.query.filter_by(tipo='venda').order_by(Movimentacao.data.desc()).limit(20).all()
    for venda in vendas:
        produto = Produto.query.get(venda.produto_id)
        if venda.valor_unitario < produto.preco_compra:
            alertas.append(f"Venda do produto '{produto.nome}' abaixo do custo em {venda.data.strftime('%d/%m/%Y')}")
    return dict(alertas_fiscais=alertas)

@app.route('/auditoria')
@login_required
def auditoria():
    logs = Auditoria.query.order_by(Auditoria.data.desc()).limit(100).all()
    return render_template('auditoria.html', logs=logs)

@app.route('/api/preco_medio_produtos')
@login_required
def api_preco_medio_produtos():
    produtos = Produto.query.all()
    resultado = []
    for produto in produtos:
        compras = [m for m in produto.movimentacoes if m.tipo == 'compra']
        total_qtd = sum(m.quantidade for m in compras)
        total_valor = sum(m.quantidade * m.valor_unitario for m in compras)
        preco_medio = (total_valor / total_qtd) if total_qtd > 0 else 0
        resultado.append({
            'id': produto.id,
            'nome': produto.nome,
            'preco_medio': round(preco_medio, 2),
            'quantidade_estoque': produto.quantidade_estoque
        })
    return jsonify(resultado)

@app.route('/api/preco_medio_geral')
@login_required
def api_preco_medio_geral():
    produtos = Produto.query.all()
    total_qtd = 0
    total_valor = 0
    for produto in produtos:
        compras = [m for m in produto.movimentacoes if m.tipo == 'compra']
        total_qtd += sum(m.quantidade for m in compras)
        total_valor += sum(m.quantidade * m.valor_unitario for m in compras)
    preco_medio_geral = (total_valor / total_qtd) if total_qtd > 0 else 0
    return jsonify({'preco_medio_geral': round(preco_medio_geral, 2)})

@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    print('Entrou na view de registro')
    form = CadastroUsuarioForm()
    if form.validate_on_submit():
        print('Formulário validado')
        if Usuario.query.filter_by(email=form.email.data).first():
            print('E-mail já cadastrado')
            flash('Este e-mail já está cadastrado.', 'danger')
            return redirect(url_for('registrar'))
        usuario = Usuario(
            nome=form.nome.data,
            email=form.email.data
        )
        usuario.set_password(form.senha.data)
        db.session.add(usuario)
        db.session.commit()
        print('Usuário cadastrado com sucesso')
        flash('Conta criada com sucesso! Agora é só entrar.', 'success')
        return redirect(url_for('login'))
    else:
        print('Formulário NÃO validado:', form.errors)
    return render_template('registrar.html', form=form)

@app.route('/editar_conta', methods=['GET', 'POST'])
@login_required
def editar_conta():
    form = EditarUsuarioForm(obj=current_user)
    if form.validate_on_submit():
        current_user.nome = form.nome.data
        current_user.email = form.email.data
        if form.senha.data:
            current_user.set_password(form.senha.data)
        if form.foto_perfil.data:
            filename = secure_filename(form.foto_perfil.data.filename)
            caminho = os.path.join('static/profile_pics', filename)
            form.foto_perfil.data.save(caminho)
            current_user.foto_perfil = f'profile_pics/{filename}'
        db.session.commit()
        flash('Conta atualizada com sucesso!', 'success')
        return redirect(url_for('editar_conta'))
    return render_template('editar_conta.html', form=form)

@app.route('/api/dashboard')
@login_required
def api_dashboard():
    print('Calculando dashboard...')
    produtos = Produto.query.filter_by().all()
    def custo_medio(produto):
        compras = [m for m in produto.movimentacoes if m.tipo == 'compra']
        total_qtd = sum(m.quantidade for m in compras)
        total_valor = sum(m.quantidade * m.valor_unitario for m in compras)
        return (total_valor / total_qtd) if total_qtd > 0 else 0
    total_estoque = sum(p.quantidade_estoque for p in produtos)
    valor_estoque = sum(max(p.quantidade_estoque, 0) * p.preco_compra for p in produtos)
    print(f'Valor em estoque (custo médio): {valor_estoque}')
    mes = datetime.now().month
    ano = datetime.now().year
    vendas = Movimentacao.query.filter_by(tipo='venda').filter(extract('month', Movimentacao.data)==mes, extract('year', Movimentacao.data)==ano).all()
    margem_lucro = 0
    for venda in vendas:
        produto = Produto.query.get(venda.produto_id)
        custo = venda.custo_unitario if venda.custo_unitario is not None else custo_medio(produto)
        print(f'venda: {venda.valor_unitario}, custo: {custo}, qtd: {venda.quantidade}')
        margem_lucro += (venda.valor_unitario - custo) * venda.quantidade
    print(f'Margem de lucro do mês: {margem_lucro}')
    alertas = []
    for venda in vendas:
        produto = Produto.query.get(venda.produto_id)
        if venda.valor_unitario < custo_medio(produto):
            alertas.append(f"Venda do produto '{produto.nome}' abaixo do custo em {venda.data.strftime('%d/%m/%Y')}")
    return jsonify({
        'estoque_atual': total_estoque,
        'valor_estoque': valor_estoque,
        'margem_lucro_mes': margem_lucro,
        'alertas_fiscais': alertas,
        'usuario': {
            'nome': current_user.nome,
            'email': current_user.email,
            'foto_perfil': current_user.foto_perfil
        }
    })

@app.route('/api/produtos')
@login_required
def api_produtos():
    produtos = Produto.query.all()
    return jsonify([
        {
            'id': p.id,
            'nome': p.nome,
            'descricao': p.descricao,
            'preco_compra': p.preco_compra,
            'preco_venda': p.preco_venda,
            'quantidade_estoque': p.quantidade_estoque
        } for p in produtos
    ])

@app.route('/api/movimentacoes')
@login_required
def api_movimentacoes():
    movimentacoes = Movimentacao.query.order_by(Movimentacao.data.desc()).all()
    return jsonify([
        {
            'id': m.id,
            'tipo': m.tipo,
            'produto': Produto.query.get(m.produto_id).nome,
            'quantidade': m.quantidade,
            'valor_unitario': m.valor_unitario,
            'data': m.data.strftime('%d/%m/%Y %H:%M')
        } for m in movimentacoes
    ])

@app.route('/api/usuario')
@login_required
def api_usuario():
    return jsonify({
        'nome': current_user.nome,
        'email': current_user.email,
        'foto_perfil': current_user.foto_perfil
    })

@app.route('/debug_usuarios')
def debug_usuarios():
    usuarios = Usuario.query.all()
    return '<br>'.join([f'{u.id} - {u.nome} - {u.email}' for u in usuarios])

@app.route('/produtos')
@login_required
def listar_produtos():
    produtos = Produto.query.all()
    return render_template('produtos.html', produtos=produtos)

@app.route('/inventario')
@login_required
def inventario():
    return render_template('inventario.html')

@app.route('/previsao_demanda')
@login_required
def previsao_demanda():
    return render_template('previsao_demanda.html')

@app.route('/estoque_niveis')
@login_required
def estoque_niveis():
    return render_template('estoque_niveis.html')

@app.route('/fornecedores')
@login_required
def fornecedores():
    return render_template('fornecedores.html')

@app.route('/qualidade')
@login_required
def qualidade():
    return render_template('qualidade.html')

@app.route('/analise_dados')
@login_required
def analise_dados():
    return render_template('analise_dados.html')

@app.route('/logistica_reversa')
@login_required
def logistica_reversa():
    return render_template('logistica_reversa.html')

@app.route('/relatorio_estoque')
@login_required
def relatorio_estoque():
    return render_template('relatorio_estoque.html')

@app.route('/relatorio_geral_completo')
@login_required
def relatorio_geral_completo():
    return render_template('relatorio_geral_completo.html')

# 1. Inventário: Listar todos os itens em estoque
@app.route('/api/inventario', methods=['GET'])
@login_required
def api_inventario():
    produtos = Produto.query.all()
    min_estoque = 5  # Exemplo de mínimo
    max_estoque = 100  # Exemplo de máximo
    return jsonify([
        {
            'id': p.id,
            'nome': p.nome,
            'descricao': p.descricao,
            'quantidade_estoque': p.quantidade_estoque,
            'preco_compra': p.preco_compra,
            'preco_venda': p.preco_venda,
            'nivel_estoque': 'baixo' if p.quantidade_estoque < min_estoque else ('alto' if p.quantidade_estoque > max_estoque else 'ok')
        } for p in produtos
    ])

# 2. Entradas e Saídas: Registrar movimentação
@app.route('/api/movimentacao', methods=['POST'])
@login_required
def api_registrar_movimentacao():
    data = request.json
    mov = Movimentacao(
        produto_id=data['produto_id'],
        tipo=data['tipo'],
        quantidade=data['quantidade'],
        valor_unitario=data['valor_unitario'],
        custo_unitario=data.get('custo_unitario')
    )
    produto = Produto.query.get(data['produto_id'])
    if data['tipo'] == 'compra':
        produto.quantidade_estoque += data['quantidade']
        produto.preco_compra = data['valor_unitario']
    elif data['tipo'] == 'venda':
        produto.quantidade_estoque -= data['quantidade']
    db.session.add(mov)
    db.session.commit()
    return jsonify({'status': 'ok', 'movimentacao_id': mov.id})

# 3. Níveis de Estoque: Consultar níveis e alertas
@app.route('/api/estoque_niveis', methods=['GET'])
@login_required
def api_estoque_niveis():
    produtos = Produto.query.all()
    min_estoque = 5  # Exemplo de mínimo
    max_estoque = 100  # Exemplo de máximo
    return jsonify([
        {
            'id': p.id,
            'nome': p.nome,
            'quantidade_estoque': p.quantidade_estoque,
            'alerta': 'baixo' if p.quantidade_estoque < min_estoque else ('alto' if p.quantidade_estoque > max_estoque else 'ok')
        } for p in produtos
    ])

# 4. Previsão de Demanda (simples, baseada em média dos últimos 3 meses)
@app.route('/api/previsao_demanda', methods=['GET'])
@login_required
def api_previsao_demanda():
    from datetime import timedelta
    produtos = Produto.query.all()
    previsao = []
    for p in produtos:
        vendas = [m for m in p.movimentacoes if m.tipo == 'venda']
        vendas = sorted(vendas, key=lambda x: x.data, reverse=True)
        ultimos_90 = [m for m in vendas if (datetime.now() - m.data).days <= 90]
        total = sum(m.quantidade for m in ultimos_90)
        media_mes = total / 3 if total else 0
        previsao.append({'id': p.id, 'nome': p.nome, 'previsao_mensal': round(media_mes, 2)})
    return jsonify(previsao)

# 5. Gestão de Fornecedores (CRUD simplificado)
# (Necessário criar modelo Fornecedor para completo, aqui exemplo básico)
@app.route('/api/fornecedores', methods=['GET'])
@login_required
def api_listar_fornecedores():
    # Exemplo estático
    fornecedores = [
        {'id': 1, 'nome': 'Fornecedor A', 'contato': 'a@email.com'},
        {'id': 2, 'nome': 'Fornecedor B', 'contato': 'b@email.com'}
    ]
    return jsonify(fornecedores)

# 6. Controle de Qualidade: Marcar item como danificado/vencido
@app.route('/api/produto/<int:produto_id>/qualidade', methods=['POST'])
@login_required
def api_marcar_qualidade(produto_id):
    data = request.json
    # Aqui você pode salvar um status de qualidade no banco (exemplo simplificado)
    # Exemplo: Produto.query.get(produto_id).qualidade = data['status']
    return jsonify({'status': 'ok', 'produto_id': produto_id, 'qualidade': data['status']})

# 7. Análise de Dados: Métricas e tendências
@app.route('/api/analise_estoque', methods=['GET'])
@login_required
def api_analise_estoque():
    produtos = Produto.query.all()
    total_estoque = sum(p.quantidade_estoque for p in produtos)
    total_valor = sum(p.quantidade_estoque * p.preco_compra for p in produtos)
    return jsonify({'total_estoque': total_estoque, 'valor_estoque': total_valor})

# 8. Logística Reversa: Registrar devolução
@app.route('/api/devolucao', methods=['POST'])
@login_required
def api_registrar_devolucao():
    data = request.json
    mov = Movimentacao(
        produto_id=data['produto_id'],
        tipo='devolucao',
        quantidade=data['quantidade'],
        valor_unitario=data['valor_unitario'],
        custo_unitario=None
    )
    produto = Produto.query.get(data['produto_id'])
    produto.quantidade_estoque += data['quantidade']
    db.session.add(mov)
    db.session.commit()
    return jsonify({'status': 'ok', 'movimentacao_id': mov.id})


# 9. Relatórios: Relatório geral de estoque
@app.route('/api/relatorio_estoque', methods=['GET'])
@login_required
def api_relatorio_estoque():
    produtos = Produto.query.all()
    relatorio = [
        {
            'id': p.id,
            'nome': p.nome,
            'quantidade_estoque': p.quantidade_estoque,
            'preco_compra': p.preco_compra,
            'preco_venda': p.preco_venda,
            'custo_total': p.quantidade_estoque * p.preco_compra
        } for p in produtos
    ]
    return jsonify(relatorio)

# Relatório Geral Completo
@app.route('/api/relatorio_geral_completo', methods=['GET'])
@login_required
def api_relatorio_geral_completo():
    produtos = Produto.query.all()
    movimentacoes = Movimentacao.query.all()
    
    # Métricas básicas
    total_produtos = len(produtos)
    total_estoque = sum(p.quantidade_estoque for p in produtos)
    valor_total_estoque = sum(p.quantidade_estoque * p.preco_compra for p in produtos)
    
    # Análise de vendas do mês atual
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    vendas_mes = [m for m in movimentacoes if m.tipo == 'venda' and m.data.month == mes_atual and m.data.year == ano_atual]
    
    total_vendas_mes = len(vendas_mes)
    quantidade_vendida_mes = sum(v.quantidade for v in vendas_mes)
    valor_vendas_mes = sum(v.valor_unitario * v.quantidade for v in vendas_mes)
    margem_lucro_mes = sum((v.valor_unitario - (v.custo_unitario or 0)) * v.quantidade for v in vendas_mes)
    
    # Produtos mais vendidos (últimos 30 dias)
    from datetime import timedelta
    data_30_dias = datetime.now() - timedelta(days=30)
    vendas_30_dias = [m for m in movimentacoes if m.tipo == 'venda' and m.data >= data_30_dias]
    
    produtos_mais_vendidos = {}
    for venda in vendas_30_dias:
        produto_nome = venda.produto.nome
        if produto_nome not in produtos_mais_vendidos:
            produtos_mais_vendidos[produto_nome] = 0
        produtos_mais_vendidos[produto_nome] += venda.quantidade
    
    produtos_mais_vendidos = sorted(produtos_mais_vendidos.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Alertas de estoque
    alertas_estoque = []
    for produto in produtos:
        if produto.quantidade_estoque < 5:  # Estoque baixo
            alertas_estoque.append({
                'produto': produto.nome,
                'quantidade': produto.quantidade_estoque,
                'tipo': 'estoque_baixo'
            })
        elif produto.quantidade_estoque > 100:  # Estoque alto
            alertas_estoque.append({
                'produto': produto.nome,
                'quantidade': produto.quantidade_estoque,
                'tipo': 'estoque_alto'
            })
    
    # Análise de margem de lucro
    produtos_margem = []
    for produto in produtos:
        if produto.preco_venda > 0 and produto.preco_compra > 0:
            margem = ((produto.preco_venda - produto.preco_compra) / produto.preco_venda) * 100
            produtos_margem.append({
                'nome': produto.nome,
                'margem': round(margem, 2),
                'preco_compra': produto.preco_compra,
                'preco_venda': produto.preco_venda
            })
    
    produtos_margem = sorted(produtos_margem, key=lambda x: x['margem'], reverse=True)
    
    # Movimentações recentes
    movimentacoes_recentes = Movimentacao.query.order_by(Movimentacao.data.desc()).limit(10).all()
    
    # Resumo por categoria de produto (exemplo)
    categorias = {}
    for produto in produtos:
        # Simular categorias baseadas no nome (você pode implementar categorias reais)
        categoria = produto.nome.split()[0] if produto.nome else 'Outros'
        if categoria not in categorias:
            categorias[categoria] = {'quantidade': 0, 'valor': 0}
        categorias[categoria]['quantidade'] += produto.quantidade_estoque
        categorias[categoria]['valor'] += produto.quantidade_estoque * produto.preco_compra
    
    return jsonify({
        'resumo_geral': {
            'total_produtos': total_produtos,
            'total_estoque': total_estoque,
            'valor_total_estoque': round(valor_total_estoque, 2),
            'data_relatorio': datetime.now().strftime('%d/%m/%Y %H:%M')
        },
        'vendas_mes_atual': {
            'total_vendas': total_vendas_mes,
            'quantidade_vendida': quantidade_vendida_mes,
            'valor_vendas': round(valor_vendas_mes, 2),
            'margem_lucro': round(margem_lucro_mes, 2),
            'margem_media': round((margem_lucro_mes / valor_vendas_mes * 100) if valor_vendas_mes > 0 else 0, 2)
        },
        'produtos_mais_vendidos': [
            {'nome': nome, 'quantidade': qtd} for nome, qtd in produtos_mais_vendidos
        ],
        'alertas': {
            'estoque_baixo': [a for a in alertas_estoque if a['tipo'] == 'estoque_baixo'],
            'estoque_alto': [a for a in alertas_estoque if a['tipo'] == 'estoque_alto'],
            'total_alertas': len(alertas_estoque)
        },
        'produtos_margem': produtos_margem[:10],  # Top 10 margens
        'movimentacoes_recentes': [
            {
                'data': m.data.strftime('%d/%m/%Y %H:%M'),
                'tipo': m.tipo,
                'produto': m.produto.nome,
                'quantidade': m.quantidade,
                'valor_unitario': m.valor_unitario
            } for m in movimentacoes_recentes
        ],
        'categorias': categorias
    })

@app.route('/relatorio_geral_completo/pdf')
@login_required
def relatorio_geral_pdf():
    produtos = Produto.query.all()
    movimentacoes = Movimentacao.query.all()
    from datetime import datetime, timedelta
    # --- Lógica igual ao endpoint /api/relatorio_geral_completo ---
    total_produtos = len(produtos)
    total_estoque = sum(p.quantidade_estoque for p in produtos)
    valor_total_estoque = sum(p.quantidade_estoque * p.preco_compra for p in produtos)
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    vendas_mes = [m for m in movimentacoes if m.tipo == 'venda' and m.data.month == mes_atual and m.data.year == ano_atual]
    total_vendas_mes = len(vendas_mes)
    quantidade_vendida_mes = sum(v.quantidade for v in vendas_mes)
    valor_vendas_mes = sum(v.valor_unitario * v.quantidade for v in vendas_mes)
    margem_lucro_mes = sum((v.valor_unitario - (v.custo_unitario or 0)) * v.quantidade for v in vendas_mes)
    data_30_dias = datetime.now() - timedelta(days=30)
    vendas_30_dias = [m for m in movimentacoes if m.tipo == 'venda' and m.data >= data_30_dias]
    produtos_mais_vendidos = {}
    for venda in vendas_30_dias:
        produto_nome = venda.produto.nome
        if produto_nome not in produtos_mais_vendidos:
            produtos_mais_vendidos[produto_nome] = 0
        produtos_mais_vendidos[produto_nome] += venda.quantidade
    produtos_mais_vendidos = [{'nome': nome, 'quantidade': qtd} for nome, qtd in sorted(produtos_mais_vendidos.items(), key=lambda x: x[1], reverse=True)[:5]]
    alertas_estoque = []
    for produto in produtos:
        if produto.quantidade_estoque < 5:
            alertas_estoque.append({'produto': produto.nome, 'quantidade': produto.quantidade_estoque, 'tipo': 'estoque_baixo'})
        elif produto.quantidade_estoque > 100:
            alertas_estoque.append({'produto': produto.nome, 'quantidade': produto.quantidade_estoque, 'tipo': 'estoque_alto'})
    produtos_margem = []
    for produto in produtos:
        if produto.preco_venda > 0 and produto.preco_compra > 0:
            margem = ((produto.preco_venda - produto.preco_compra) / produto.preco_venda) * 100
            produtos_margem.append({'nome': produto.nome, 'margem': round(margem, 2), 'preco_compra': produto.preco_compra, 'preco_venda': produto.preco_venda})
    produtos_margem = sorted(produtos_margem, key=lambda x: x['margem'], reverse=True)[:10]
    movimentacoes_recentes = Movimentacao.query.order_by(Movimentacao.data.desc()).limit(10).all()
    categorias = {}
    for produto in produtos:
        categoria = produto.nome.split()[0] if produto.nome else 'Outros'
        if categoria not in categorias:
            categorias[categoria] = {'quantidade': 0, 'valor': 0}
        categorias[categoria]['quantidade'] += produto.quantidade_estoque
        categorias[categoria]['valor'] += produto.quantidade_estoque * produto.preco_compra
    # --- Montar contexto ---
    context = {
        'resumo_geral': {
            'total_produtos': total_produtos,
            'total_estoque': total_estoque,
            'valor_total_estoque': round(valor_total_estoque, 2),
            'data_relatorio': datetime.now().strftime('%d/%m/%Y %H:%M')
        },
        'vendas_mes_atual': {
            'total_vendas': total_vendas_mes,
            'quantidade_vendida': quantidade_vendida_mes,
            'valor_vendas': round(valor_vendas_mes, 2),
            'margem_lucro': round(margem_lucro_mes, 2),
            'margem_media': round((margem_lucro_mes / valor_vendas_mes * 100) if valor_vendas_mes > 0 else 0, 2)
        },
        'produtos_mais_vendidos': produtos_mais_vendidos,
        'alertas': {
            'estoque_baixo': [a for a in alertas_estoque if a['tipo'] == 'estoque_baixo'],
            'estoque_alto': [a for a in alertas_estoque if a['tipo'] == 'estoque_alto'],
            'total_alertas': len(alertas_estoque)
        },
        'produtos_margem': produtos_margem,
        'movimentacoes_recentes': [
            {
                'data': m.data.strftime('%d/%m/%Y %H:%M'),
                'tipo': m.tipo,
                'produto': m.produto.nome,
                'quantidade': m.quantidade,
                'valor_unitario': m.valor_unitario
            } for m in movimentacoes_recentes
        ],
        'categorias': categorias
    }
    html = render_template('relatorio_geral_pdf.html', **context)
    # Caminho manual do wkhtmltopdf para Windows
    wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    import os
    if not os.path.exists(wkhtmltopdf_path):
        return 'wkhtmltopdf não encontrado em: ' + wkhtmltopdf_path, 500
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    pdf = pdfkit.from_string(html, False, configuration=config, options={
        'encoding': 'UTF-8',
        'page-size': 'A4',
        'margin-top': '10mm',
        'margin-bottom': '10mm',
        'margin-left': '10mm',
        'margin-right': '10mm',
        'no-outline': None,
        'enable-local-file-access': None,
        'disable-smart-shrinking': None,
        'print-media-type': None,
        'no-stop-slow-scripts': None,
        'javascript-delay': '1000',
        'custom-header': [
            ('Accept-Encoding', 'gzip')
        ]
    })
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=relatorio_geral_completo.pdf'
    return response

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)