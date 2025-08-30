


from flask import Flask, render_template, redirect, url_for, flash, request, Response, jsonify, make_response
import csv
from flask_sqlalchemy import SQLAlchemy
from models import db, Produto
from forms_type import CadastroProdutoForm, LoginForm, MovimentacaoForm, DevolucaoForm
from config import Config
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import Usuario
from models import Auditoria
from models import Devolucao
from models import Empresa
import os
from werkzeug.utils import secure_filename
from models import Movimentacao
from datetime import datetime
from sqlalchemy import extract, inspect, text
from forms import CadastroUsuarioForm, EditarUsuarioForm, EmpresaForm  # Formulário de Empresa para CRUD do site_admin
from functools import wraps
# Removido WeasyPrint
import pdfkit
from config_fiscal import (
    calcular_impostos_vendas, 
    calcular_desconto_venda, 
    calcular_despesas_administrativas, 
    calcular_despesas_comerciais, 
    calcular_cmv
)
from sqlalchemy.orm import scoped_session
from models import Empresa, CompartilhamentoEmpresa, CompartilhamentoUsuario  # Modelos de domínio para empresas e compartilhamento

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


def role_required(*roles):
    """Restringe acesso por papel (role). 'site_admin' tem acesso total."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            # site_admin tem acesso total
            if getattr(current_user, 'role', None) == 'site_admin':
                return view_func(*args, **kwargs)
            if current_user.role not in roles:
                flash('Você não tem permissão para acessar esta funcionalidade.', 'danger')
                # Redireciona contador para relatórios
                if getattr(current_user, 'role', None) == 'contador':
                    return redirect(url_for('relatorio_fiscal'))
                return redirect(url_for('index'))
            return view_func(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data).first()
        if usuario and usuario.check_password(form.senha.data):
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')
            if usuario.role == 'site_admin':
                return redirect(url_for('config_compartilhamento'))
            if usuario.role == 'contador':
                return redirect(url_for('relatorio_fiscal'))
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
@role_required('administrador', 'vendedor')
def index():
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
    def custo_medio(produto):
        compras = [m for m in produto.movimentacoes if m.tipo == 'compra']
        total_qtd = sum(m.quantidade for m in compras)
        total_valor = sum(m.quantidade * m.valor_unitario for m in compras)
        return (total_valor / total_qtd) if total_qtd > 0 else 0
    total_estoque = sum(p.quantidade_estoque for p in produtos)
    valor_estoque = sum(max(p.quantidade_estoque, 0) * p.preco_compra for p in produtos)

    mes = datetime.now().month
    ano = datetime.now().year
    vendas_mes = (
        Movimentacao.query.filter(Movimentacao.tipo=='venda', Movimentacao.empresa_id.in_(empresas_visiveis_ids()))
        .filter(extract('month', Movimentacao.data) == mes, extract('year', Movimentacao.data) == ano)
        .all()
    )
    # Top 5 produtos mais vendidos (quantidade) no mês
    vendas_por_produto = {}
    for venda in vendas_mes:
        vendas_por_produto[venda.produto_id] = vendas_por_produto.get(venda.produto_id, 0) + (venda.quantidade or 0)
    vendas_top_lista = []
    for produto_id, quantidade_total in vendas_por_produto.items():
        produto_ref = Produto.query.get(produto_id)
        nome_produto = produto_ref.nome if produto_ref else f"Produto {produto_id}"
        vendas_top_lista.append((nome_produto, quantidade_total))
    vendas_top_lista.sort(key=lambda x: x[1], reverse=True)
    grafico_bar_vendas_labels = [n for n, _ in vendas_top_lista[:5]]
    grafico_bar_vendas_dados = [q for _, q in vendas_top_lista[:5]]
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

    ultimas_transacoes = (
        Movimentacao.query.filter(Movimentacao.empresa_id.in_(empresas_visiveis_ids()))
        .order_by(Movimentacao.data.desc()).limit(5).all()
    )

    from calendar import month_abbr
    labels = []
    data_lucro = []
    for i in range(5, -1, -1):
        mes_ref = (datetime.now().month - i - 1) % 12 + 1
        ano_ref = datetime.now().year if datetime.now().month - i > 0 else datetime.now().year - 1
        vendas = (
            Movimentacao.query.filter_by(tipo='venda', usuario_id=current_user.id)
            .filter(extract('month', Movimentacao.data) == mes_ref, extract('year', Movimentacao.data) == ano_ref)
            .all()
        )
        lucro = 0
        for venda in vendas:
            produto = Produto.query.get(venda.produto_id)
            custo = venda.custo_unitario if venda.custo_unitario is not None else custo_medio(produto)
            lucro += (venda.valor_unitario - custo) * venda.quantidade
        labels.append(month_abbr[mes_ref].capitalize())
        data_lucro.append(lucro)

    # Preparar dados para gráfico de pizza: distribuição do valor de estoque por produto (Top 5 + Outros)
    valores_produtos = []
    for p in produtos:
        try:
            valor = float(max(p.quantidade_estoque or 0, 0) * float(p.preco_compra or 0))
        except Exception:
            valor = 0.0
        valores_produtos.append((p.nome or f"Produto {p.id}", valor))
    valores_produtos.sort(key=lambda x: x[1], reverse=True)
    top5 = valores_produtos[:5]
    outros_total = sum(v for _, v in valores_produtos[5:])
    grafico_pizza_labels = [n for n, _ in top5] + (["Outros"] if outros_total > 0 else [])
    grafico_pizza_dados = [v for _, v in top5] + ([outros_total] if outros_total > 0 else [])

    return render_template('index.html',
        produtos=produtos,
        total_estoque=total_estoque,
        valor_estoque=valor_estoque,
        margem_lucro=margem_lucro,
        alertas=alertas,
        divergencias=divergencias,
        ultimas_transacoes=ultimas_transacoes,
        grafico_labels=labels,
        grafico_lucro=data_lucro,
        grafico_pizza_labels=grafico_pizza_labels,
        grafico_pizza_dados=grafico_pizza_dados,
        grafico_bar_vendas_labels=grafico_bar_vendas_labels,
        grafico_bar_vendas_dados=grafico_bar_vendas_dados
    )

# Adicionar auditoria ao cadastrar produto
@app.route('/adicionar', methods=['GET', 'POST'])
@login_required
@role_required('administrador', 'vendedor')
def adicionar_produto():
    # Verificar se o usuário tem empresa_id definido
    empresa_id = getattr(current_user, 'empresa_id', None)
    if empresa_id is None:
        flash('Você precisa estar associado a uma empresa para cadastrar produtos.', 'warning')
        return redirect(url_for('index'))
    
    form = CadastroProdutoForm()
    if form.validate_on_submit():
        
        novo_produto = Produto(
            nome=form.nome.data,
            descricao=form.descricao.data,
            preco_compra=float(form.preco_compra.data),
            preco_venda=float(form.preco_venda.data),
            quantidade_estoque=form.quantidade_estoque.data,
            usuario_id=current_user.id,
            empresa_id=empresa_id
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
                custo_unitario=None,
                usuario_id=current_user.id,
                empresa_id=empresa_id
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
@role_required('administrador', 'vendedor')
def editar_produto(produto_id):
    # Verificar se o usuário tem empresa_id definido
    empresa_id = getattr(current_user, 'empresa_id', None)
    if empresa_id is None:
        flash('Você precisa estar associado a uma empresa para editar produtos.', 'warning')
        return redirect(url_for('index'))
    
    produto = Produto.query.filter_by(id=produto_id, empresa_id=empresa_id).first_or_404()
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
@role_required('administrador')
def deletar_produto(produto_id):
    # Verificar se o usuário tem empresa_id definido
    empresa_id = getattr(current_user, 'empresa_id', None)
    if empresa_id is None:
        flash('Você precisa estar associado a uma empresa para excluir produtos.', 'warning')
        return redirect(url_for('index'))
    
    produto = Produto.query.filter_by(id=produto_id, empresa_id=empresa_id).first_or_404()

    try:
        # Excluir devoluções relacionadas ao produto
        devolucoes_relacionadas = Devolucao.query.filter_by(produto_id=produto.id).all()
        total_devolucoes = len(devolucoes_relacionadas)
        for devolucao in devolucoes_relacionadas:
            db.session.delete(devolucao)

        # Excluir movimentações relacionadas ao produto
        movimentacoes_relacionadas = Movimentacao.query.filter_by(produto_id=produto.id).all()
        total_movimentacoes = len(movimentacoes_relacionadas)
        for movimentacao in movimentacoes_relacionadas:
            db.session.delete(movimentacao)

        # Excluir o produto
        db.session.delete(produto)
        db.session.commit()

        # Registrar auditoria resumindo a exclusão em cascata
        auditoria = Auditoria(
            usuario_id=current_user.id,
            acao='Exclusão',
            entidade='Produto',
            entidade_id=produto.id,
            detalhes=(
                f'Produto excluído: {produto.nome}. '
                f'Movimentações removidas: {total_movimentacoes}. '
                f'Devoluções removidas: {total_devolucoes}.'
            )
        )
        db.session.add(auditoria)
        db.session.commit()

        flash('Produto e registros relacionados removidos com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir produto: {e}', 'danger')

    return redirect(url_for('index'))

@app.route('/movimentacoes', methods=['GET'])
@login_required
def listar_movimentacoes():
    # Verificar se o usuário tem empresa_id definido
    empresa_id = getattr(current_user, 'empresa_id', None)
    if empresa_id is None:
        flash('Você precisa estar associado a uma empresa para visualizar movimentações.', 'warning')
        return redirect(url_for('index'))
    
    movimentacoes = (
        Movimentacao.query.filter_by(empresa_id=empresa_id)
        .order_by(Movimentacao.data.desc()).all()
    )
    return render_template('movimentacoes.html', movimentacoes=movimentacoes)

# Adicionar auditoria ao registrar movimentação
@app.route('/registrar_movimentacao', methods=['GET', 'POST'])
@login_required
@role_required('administrador', 'vendedor')
def registrar_movimentacao():
    tipo_param = request.args.get('tipo')
    form = MovimentacaoForm()
    if tipo_param in ['compra', 'venda'] and request.method == 'GET':
        form.tipo.data = tipo_param
    produtos_usuario = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
    form.produto_id.choices = [(p.id, p.nome) for p in produtos_usuario]
    if form.validate_on_submit():
        # Verificar se o usuário tem empresa_id definido
        empresa_id = getattr(current_user, 'empresa_id', None)
        if empresa_id is None:
            flash('Você precisa estar associado a uma empresa para registrar movimentações.', 'warning')
            return redirect(url_for('index'))
        
        produto = Produto.query.filter_by(id=form.produto_id.data, empresa_id=empresa_id).first_or_404()
        if form.tipo.data == 'venda':
            if form.quantidade.data > produto.quantidade_estoque:
                flash('Não é possível vender mais do que o estoque disponível!', 'danger')
                return redirect(url_for('registrar_movimentacao', tipo='venda'))
            if not form.valor_venda.data or float(form.valor_venda.data) <= 0:
                flash('Informe o valor de venda!', 'danger')
                return redirect(url_for('registrar_movimentacao', tipo='venda'))
            
            #FIFO para cálculo do custo
            quantidade_vendida = form.quantidade.data
            custo_total_venda = 0
            quantidade_restante = quantidade_vendida
            
            #buscar compras ordenadas por data (mais antigas primeiro) e preço (menor primeiro)
            compras = (
                Movimentacao.query.filter(
                    Movimentacao.produto_id==form.produto_id.data,
                    Movimentacao.tipo=='compra',
                    Movimentacao.empresa_id.in_(empresas_visiveis_ids())
                )
                .order_by(Movimentacao.data.asc())
                .all()
            )
            
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
        else:
            custo_unitario = None
            valor_unitario = float(form.valor_unitario.data)
        # Calcular automaticamente os campos fiscais
        desconto_venda = 0.0
        imposto_vendas = 0.0
        cmv = 0.0
        despesas_administrativas = 0.0
        despesas_comerciais = 0.0
        
        if form.tipo.data == 'venda':
            # Obter percentual de desconto do formulário
            percentual_desconto = float(form.percentual_desconto.data) if form.percentual_desconto.data else 0.0
            
            # Calcular campos fiscais usando as funções de configuração
            cmv = calcular_cmv(custo_unitario, form.quantidade.data)
            imposto_vendas = calcular_impostos_vendas(valor_unitario, form.quantidade.data)
            desconto_venda = calcular_desconto_venda(valor_unitario, form.quantidade.data, percentual_desconto)
            despesas_administrativas = calcular_despesas_administrativas(valor_unitario, form.quantidade.data)
            despesas_comerciais = calcular_despesas_comerciais(valor_unitario, form.quantidade.data)
        
        mov = Movimentacao(
            produto_id=form.produto_id.data,
            tipo=form.tipo.data,
            quantidade=form.quantidade.data,
            valor_unitario=valor_unitario,
            custo_unitario=custo_unitario,
            percentual_desconto=percentual_desconto if form.tipo.data == 'venda' else 0.0,
            desconto_venda=desconto_venda,
            imposto_vendas=imposto_vendas,
            cmv=cmv,
            despesas_administrativas=despesas_administrativas,
            despesas_comerciais=despesas_comerciais,
            usuario_id=current_user.id,
            empresa_id=empresa_id
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
    # Dados auxiliares para UI (estoque disponível e preços)
    produtos_info = {
        p.id: {
            'id': p.id,
            'nome': p.nome,
            'quantidade_estoque': int(p.quantidade_estoque or 0),
            'preco_compra': float(p.preco_compra or 0),
            'preco_venda': float(p.preco_venda or 0),
        }
        for p in produtos_usuario
    }
    return render_template('registrar_movimentacao.html', form=form, produtos_info=produtos_info)

@app.route('/relatorio_fiscal')
@login_required
@role_required('administrador', 'contador')
def relatorio_fiscal():
    # Margem de lucro do mês atual
    mes = datetime.now().month
    ano = datetime.now().year
    vendas = (
        Movimentacao.query.filter(Movimentacao.tipo=='venda', Movimentacao.empresa_id.in_(empresas_visiveis_ids()))
        .filter(extract('month', Movimentacao.data) == mes, extract('year', Movimentacao.data) == ano)
        .all()
    )
    margem_lucro = 0
    for venda in vendas:
        # Usar sempre o custo_unitario salvo na movimentação, nunca o preco_compra atual
        custo = venda.custo_unitario if venda.custo_unitario is not None else 0
        margem_lucro += (venda.valor_unitario - custo) * venda.quantidade
    
    # Cálculo dos novos campos fiscais
    total_descontos = sum(v.desconto_venda for v in vendas)
    total_impostos = sum(v.imposto_vendas for v in vendas)
    total_cmv = sum(v.cmv for v in vendas)
    despesas_administrativas = sum(v.despesas_administrativas for v in vendas)
    despesas_comerciais = sum(v.despesas_comerciais for v in vendas)
    
    return render_template('relatorio_fiscal.html', 
                         vendas=vendas, 
                         margem_lucro=margem_lucro,
                         total_descontos=total_descontos,
                         total_impostos=total_impostos,
                         total_cmv=total_cmv,
                         despesas_administrativas=despesas_administrativas,
                         despesas_comerciais=despesas_comerciais)

@app.route('/exportar_relatorio_fiscal')
@login_required
@role_required('administrador', 'contador')
def exportar_relatorio_fiscal():
    mes = datetime.now().month
    ano = datetime.now().year
    vendas = (
        Movimentacao.query.filter(Movimentacao.tipo=='venda', Movimentacao.empresa_id.in_(empresas_visiveis_ids()))
        .filter(extract('month', Movimentacao.data) == mes, extract('year', Movimentacao.data) == ano)
        .all()
    )
    def generate():
        data = [['Data', 'Tipo', 'Produto', 'Quantidade', 'Valor Unitário', 'Custo Unitário', '% Desconto', 'Desconto', 'Impostos', 'CMV', 'Margem de Lucro']]
        for venda in vendas:
            produto = Produto.query.get(venda.produto_id)
            custo = venda.custo_unitario if venda.custo_unitario is not None else 0
            linha = [
                venda.data.strftime('%d/%m/%Y %H:%M'),
                venda.tipo.title(),
                produto.nome,
                venda.quantidade,
                venda.valor_unitario,
                custo,
                f"{venda.percentual_desconto:.1f}%",
                venda.desconto_venda,
                venda.imposto_vendas,
                venda.cmv,
                (venda.valor_unitario - custo) * venda.quantidade
            ]
            data.append(linha)
        
        # Adicionar resumo fiscal
        total_descontos = sum(v.desconto_venda for v in vendas)
        total_impostos = sum(v.imposto_vendas for v in vendas)
        total_cmv = sum(v.cmv for v in vendas)
        despesas_administrativas = sum(v.despesas_administrativas for v in vendas)
        despesas_comerciais = sum(v.despesas_comerciais for v in vendas)
        
        data.append([])  # Linha em branco
        data.append(['RESUMO FISCAL'])
        data.append(['Total de Descontos', total_descontos])
        data.append(['Total de Impostos', total_impostos])
        data.append(['CMV Total', total_cmv])
        data.append(['Despesas Administrativas', despesas_administrativas])
        data.append(['Despesas Comerciais', despesas_comerciais])
        
        output = ''
        for row in data:
            output += ';'.join(map(str, row)) + '\n'
        return output
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=relatorio_fiscal.csv"})

def calcular_campos_fiscais_automaticamente():
    """Recalcula campos fiscais para TODAS as vendas, sem depender de usuário logado."""
    vendas = Movimentacao.query.filter_by(tipo='venda').all()

    for venda in vendas:
        venda.cmv = calcular_cmv(venda.custo_unitario, venda.quantidade)
        venda.imposto_vendas = calcular_impostos_vendas(venda.valor_unitario, venda.quantidade)
        venda.desconto_venda = calcular_desconto_venda(
            venda.valor_unitario, venda.quantidade, venda.percentual_desconto
        )
        venda.despesas_administrativas = calcular_despesas_administrativas(
            venda.valor_unitario, venda.quantidade
        )
        venda.despesas_comerciais = calcular_despesas_comerciais(
            venda.valor_unitario, venda.quantidade
        )

    db.session.commit()


def ensure_schema_columns():
    """Garante colunas multi-tenant nas tabelas existentes (SQLite ALTER TABLE ADD COLUMN)."""
    inspector = inspect(db.engine)

    # produto.usuario_id
    try:
        produto_cols = {col['name'] for col in inspector.get_columns('produto')}
        if 'usuario_id' not in produto_cols:
            db.session.execute(text('ALTER TABLE produto ADD COLUMN usuario_id INTEGER'))
            db.session.commit()
    except Exception:
        db.session.rollback()
        # Deixar seguir; erros serão exibidos ao usar

    # movimentacao.usuario_id
    try:
        mov_cols = {col['name'] for col in inspector.get_columns('movimentacao')}
        if 'usuario_id' not in mov_cols:
            db.session.execute(text('ALTER TABLE movimentacao ADD COLUMN usuario_id INTEGER'))
            db.session.commit()
    except Exception:
        db.session.rollback()
    # movimentacao.empresa_id
    try:
        mov_cols = {col['name'] for col in inspector.get_columns('movimentacao')}
        if 'empresa_id' not in mov_cols:
            db.session.execute(text('ALTER TABLE movimentacao ADD COLUMN empresa_id INTEGER'))
            db.session.commit()
    except Exception:
        db.session.rollback()
        
    # devolucao.usuario_id (opcional, para bases antigas)
    try:
        dev_cols = {col['name'] for col in inspector.get_columns('devolucao')}
        if 'usuario_id' not in dev_cols:
            db.session.execute(text('ALTER TABLE devolucao ADD COLUMN usuario_id INTEGER'))
            db.session.commit()
    except Exception:
        db.session.rollback()

    # produto.empresa_id
    try:
        produto_cols = {col['name'] for col in inspector.get_columns('produto')}
        if 'empresa_id' not in produto_cols:
            db.session.execute(text('ALTER TABLE produto ADD COLUMN empresa_id INTEGER'))
            db.session.commit()
    except Exception:
        db.session.rollback()

    # usuario.empresa_id
    try:
        usuario_cols = {col['name'] for col in inspector.get_columns('usuario')}
        if 'empresa_id' not in usuario_cols:
            db.session.execute(text('ALTER TABLE usuario ADD COLUMN empresa_id INTEGER'))
            db.session.commit()
        if 'role' not in usuario_cols:
            db.session.execute(text("ALTER TABLE usuario ADD COLUMN role VARCHAR(50) DEFAULT 'vendedor'"))
            db.session.commit()
    except Exception:
        db.session.rollback()

    # compartilhamento_empresa (criação de tabela se não existe)
    try:
        db.session.execute(text('SELECT 1 FROM compartilhamento_empresa LIMIT 1'))
    except Exception:
        try:
            db.session.execute(text(
                'CREATE TABLE IF NOT EXISTS compartilhamento_empresa ('
                'id INTEGER PRIMARY KEY, '
                'empresa_a_id INTEGER NOT NULL, '
                'empresa_b_id INTEGER NOT NULL, '
                'ativo BOOLEAN DEFAULT 1, '
                'CONSTRAINT uq_compartilhamento_empresas UNIQUE (empresa_a_id, empresa_b_id)'
                ')' 
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()

    # compartilhamento_usuario (criação de tabela se não existe)
    try:
        db.session.execute(text('SELECT 1 FROM compartilhamento_usuario LIMIT 1'))
    except Exception:
        try:
            db.session.execute(text(
                'CREATE TABLE IF NOT EXISTS compartilhamento_usuario ('
                'id INTEGER PRIMARY KEY, '
                'usuario_a_id INTEGER NOT NULL, '
                'usuario_b_id INTEGER NOT NULL, '
                "escopo VARCHAR(50) DEFAULT 'all', "
                'ativo BOOLEAN DEFAULT 1, '
                'CONSTRAINT uq_compartilhamento_usuarios UNIQUE (usuario_a_id, usuario_b_id)'
                ')'
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()

def empresas_visiveis_ids():
    """Retorna lista de empresa_ids visíveis para o usuário atual: própria + compartilhadas bidirecionalmente ativas."""
    if not current_user.is_authenticated:
        return []
    
    # Sempre incluir o empresa_id do usuário atual
    base_id = getattr(current_user, 'empresa_id', None)
    ids = set()
    
    # Se o usuário tem empresa_id, adicionar à lista
    if base_id is not None:
        ids.add(base_id)
    # Se não tem empresa_id, não adicionar nada - usuário sem empresa não pode acessar dados de outras empresas
    
    try:
        # Compartilhamentos entre empresas (só se base_id não for None)
        if base_id is not None:
            ativos_emp = CompartilhamentoEmpresa.query.filter_by(ativo=True).all()
            for c in ativos_emp:
                if c.empresa_a_id == base_id:
                    ids.add(c.empresa_b_id)
                if c.empresa_b_id == base_id:
                    ids.add(c.empresa_a_id)
            
            # Compartilhamentos por usuário também ampliam a visibilidade para a empresa do par
            ativos_usr = CompartilhamentoUsuario.query.filter_by(ativo=True).all()
            for cu in ativos_usr:
                if cu.usuario_a_id == current_user.id:
                    other = db.session.get(Usuario, cu.usuario_b_id)
                    if other and other.empresa_id:
                        ids.add(other.empresa_id)
                if cu.usuario_b_id == current_user.id:
                    other = db.session.get(Usuario, cu.usuario_a_id)
                    if other and other.empresa_id:
                        ids.add(other.empresa_id)
    except Exception as e:
        # Em caso de erro, pelo menos retornar o empresa_id base
        print(f"Erro ao buscar compartilhamentos: {e}")
    
    # Se não há IDs de empresa, retornar lista vazia
    # Usuário sem empresa não pode acessar dados de outras empresas
    
    result = list(ids)
    print(f"DEBUG: empresas_visiveis_ids() retornou: {result} para usuário {current_user.id}")
    return result

def seed_site_admin():
    """Cria usuário admin do site (não registrável) caso não exista."""
    from os import getenv
    email = getenv('SITE_ADMIN_EMAIL', 'site.admin@trustv.local')
    senha = getenv('SITE_ADMIN_PASSWORD', 'admin123')
    admin = Usuario.query.filter_by(email=email).first()
    if not admin:
        admin = Usuario(nome='Site Admin', email=email, role='site_admin', empresa_id=None)
        admin.set_password(senha)
        db.session.add(admin)
        db.session.commit()


def safe_add_column_ativo_empresa():
    """Migração leve: garante a coluna 'ativo' na tabela empresa.

    Executa ALTER TABLE idempotente no startup para ambientes sem Alembic.
    """
    try:
        insp = inspect(db.engine)
        cols = [c['name'] for c in insp.get_columns('empresa')]
        if 'ativo' not in cols:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE empresa ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT 1'))
    except Exception as e:
        # Evita quebrar startup se já existir/erro de permissão; log simples
        print('Aviso: não foi possível garantir coluna ativo em empresa:', e)

@app.route('/config/compartilhamento', methods=['GET', 'POST'])
@login_required
@role_required('site_admin')
def config_compartilhamento():
    """Tela de configuração de compartilhamento de dados entre empresas.

    - POST: ativa/desativa compartilhamento entre empresas específicas
    - GET: exibe status atual e lista de relacionamentos entre empresas
    
    NOTA: Apenas site_admin pode configurar compartilhamento
    """
    if request.method == 'POST':
        if 'config_compartilhamento_empresas' in request.form:
            # Configuração de compartilhamento entre empresas
            acao = request.form.get('acao_compartilhamento')
            empresa_a_id = request.form.get('empresa_a_id')
            empresa_b_id = request.form.get('empresa_b_id')
            
            if not empresa_a_id or not empresa_b_id:
                flash('Selecione ambas as empresas para configurar o compartilhamento.', 'warning')
                return redirect(url_for('config_compartilhamento'))
            
            if empresa_a_id == empresa_b_id:
                flash('Selecione empresas diferentes para configurar o compartilhamento.', 'warning')
                return redirect(url_for('config_compartilhamento'))
            
            try:
                if acao == 'ativar':
                    # Ativar compartilhamento entre as duas empresas
                    rel_empresa = CompartilhamentoEmpresa.query.filter_by(
                        empresa_a_id=empresa_a_id, 
                        empresa_b_id=empresa_b_id
                    ).first()
            
                    if not rel_empresa:
                        rel_empresa = CompartilhamentoEmpresa(
                            empresa_a_id=empresa_a_id,
                            empresa_b_id=empresa_b_id,
                            ativo=True
                        )
                        db.session.add(rel_empresa)
                    else:
                        rel_empresa.ativo = True
                    
                    # Criar relacionamentos entre usuários das duas empresas
                    usuarios_empresa_a = Usuario.query.filter_by(empresa_id=empresa_a_id).all()
                    usuarios_empresa_b = Usuario.query.filter_by(empresa_id=empresa_b_id).all()
                    
                    # Remover relacionamentos existentes entre essas empresas
                    usuario_ids_a = [u.id for u in usuarios_empresa_a]
                    usuario_ids_b = [u.id for u in usuarios_empresa_b]
                    
                    CompartilhamentoUsuario.query.filter(
                        CompartilhamentoUsuario.usuario_a_id.in_(usuario_ids_a + usuario_ids_b),
                        CompartilhamentoUsuario.usuario_b_id.in_(usuario_ids_a + usuario_ids_b)
                    ).delete(synchronize_session=False)
                    
                    # Criar relacionamentos bidirecionais entre usuários das duas empresas
                    for usuario_a in usuarios_empresa_a:
                        for usuario_b in usuarios_empresa_b:
                            rel = CompartilhamentoUsuario(
                                usuario_a_id=usuario_a.id,
                                usuario_b_id=usuario_b.id,
                                escopo='all',
                                ativo=True
                            )
                            db.session.add(rel)
                    
                    db.session.commit()
                    flash('✅ Compartilhamento entre empresas ativado com sucesso!', 'success')
                    
                elif acao == 'desativar':
                    # Desativar compartilhamento entre as duas empresas
                    rel_empresa = CompartilhamentoEmpresa.query.filter_by(
                        empresa_a_id=empresa_a_id, 
                        empresa_b_id=empresa_b_id
                    ).first()
                    
                    if rel_empresa:
                        rel_empresa.ativo = False
                    
                    # Remover relacionamentos entre usuários das duas empresas
                    usuarios_empresa_a = Usuario.query.filter_by(empresa_id=empresa_a_id).all()
                    usuarios_empresa_b = Usuario.query.filter_by(empresa_id=empresa_b_id).all()
                    
                    usuario_ids_a = [u.id for u in usuarios_empresa_a]
                    usuario_ids_b = [u.id for u in usuarios_empresa_b]
                    
                    CompartilhamentoUsuario.query.filter(
                        CompartilhamentoUsuario.usuario_a_id.in_(usuario_ids_a + usuario_ids_b),
                        CompartilhamentoUsuario.usuario_b_id.in_(usuario_ids_a + usuario_ids_b)
                    ).delete(synchronize_session=False)
                    
                    db.session.commit()
                    flash('❌ Compartilhamento entre empresas desativado.', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao configurar compartilhamento: {str(e)}', 'danger')
                print(f"Erro na configuração de compartilhamento: {e}")
        
        elif 'delete_rel_empresa' in request.form:
            # Remover relacionamento específico entre empresas
            rel_id = request.form.get('rel_id')
            if rel_id:
                try:
                    rel = CompartilhamentoEmpresa.query.get(rel_id)
                    if rel:
                        # Remover relacionamentos entre usuários das empresas
                        usuarios_empresa_a = Usuario.query.filter_by(empresa_id=rel.empresa_a_id).all()
                        usuarios_empresa_b = Usuario.query.filter_by(empresa_id=rel.empresa_b_id).all()
                        
                        usuario_ids_a = [u.id for u in usuarios_empresa_a]
                        usuario_ids_b = [u.id for u in usuarios_empresa_b]
                        
                        CompartilhamentoUsuario.query.filter(
                            CompartilhamentoUsuario.usuario_a_id.in_(usuario_ids_a + usuario_ids_b),
                            CompartilhamentoUsuario.usuario_b_id.in_(usuario_ids_a + usuario_ids_b)
                        ).delete(synchronize_session=False)
                        
                        db.session.delete(rel)
                        db.session.commit()
                        flash('Relacionamento entre empresas removido com sucesso.', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao remover relacionamento: {str(e)}', 'danger')
        
        return redirect(url_for('config_compartilhamento'))
    
    # Buscar dados para o template
    empresas = Empresa.query.filter_by(ativo=True).order_by(Empresa.nome).all()
    
    # Buscar relacionamentos existentes entre empresas
    relacoes_empresas = CompartilhamentoEmpresa.query.filter(
        CompartilhamentoEmpresa.empresa_a_id != CompartilhamentoEmpresa.empresa_b_id
    ).all()
    
    # Criar mapeamento de nomes de empresas
    empresa_id_to_nome = {e.id: e.nome for e in empresas}
    
    # Buscar dados de teste para verificar compartilhamento
    dados_compartilhamento = {}
    for rel in relacoes_empresas:
        if rel.ativo:
            # Buscar usuários das empresas relacionadas
            usuarios_empresa_a = Usuario.query.filter_by(empresa_id=rel.empresa_a_id).all()
            usuarios_empresa_b = Usuario.query.filter_by(empresa_id=rel.empresa_b_id).all()
            
            # Buscar alguns dados de exemplo para mostrar
            produtos_empresa_a = Produto.query.filter_by(empresa_id=rel.empresa_a_id).limit(3).all()
            produtos_empresa_b = Produto.query.filter_by(empresa_id=rel.empresa_b_id).limit(3).all()
            
            dados_compartilhamento[rel.id] = {
                'empresa_a': empresa_id_to_nome.get(rel.empresa_a_id),
                'empresa_b': empresa_id_to_nome.get(rel.empresa_b_id),
                'usuarios_empresa_a': len(usuarios_empresa_a),
                'usuarios_empresa_b': len(usuarios_empresa_b),
                'produtos_empresa_a': len(produtos_empresa_a),
                'produtos_empresa_b': len(produtos_empresa_b),
                'exemplo_produtos_a': [p.nome for p in produtos_empresa_a],
                'exemplo_produtos_b': [p.nome for p in produtos_empresa_b],
                'relacionamento': rel
            }
    
    return render_template('config_compartilhamento.html', 
                         empresas=empresas, 
                         relacoes_empresas=relacoes_empresas,
                         empresa_id_to_nome=empresa_id_to_nome,
                         dados_compartilhamento=dados_compartilhamento)

@app.context_processor
def inject_alertas_fiscais():
    alertas = []
    if current_user.is_authenticated:
        vendas = (
            Movimentacao.query.filter(Movimentacao.tipo=='venda', Movimentacao.empresa_id.in_(empresas_visiveis_ids()))
            .order_by(Movimentacao.data.desc()).limit(20).all()
        )
        for venda in vendas:
            produto = Produto.query.get(venda.produto_id)
            if venda.valor_unitario < produto.preco_compra:
                alertas.append(f"Venda do produto '{produto.nome}' abaixo do custo em {venda.data.strftime('%d/%m/%Y')}")
    return dict(alertas_fiscais=alertas)

@app.route('/recalcular_fiscais')
@login_required
@role_required('administrador')
def recalcular_fiscais():
    """Rota para recalcular campos fiscais manualmente"""
    try:
        calcular_campos_fiscais_automaticamente()
        flash('Campos fiscais recalculados com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao recalcular campos fiscais: {e}', 'danger')
    return redirect(url_for('relatorio_fiscal'))

@app.route('/auditoria')
@login_required
@role_required('administrador')
def auditoria():
    logs = Auditoria.query.order_by(Auditoria.data.desc()).limit(100).all()
    return render_template('auditoria.html', logs=logs)

@app.route('/api/preco_medio_produtos')
@login_required
@role_required('administrador', 'vendedor')
def api_preco_medio_produtos():
    # Verificar se o usuário tem empresa_id definido
    empresa_id = getattr(current_user, 'empresa_id', None)
    if empresa_id is None:
        return jsonify({'error': 'Usuário precisa estar associado a uma empresa'}), 403
    
    produtos = Produto.query.filter_by(empresa_id=empresa_id).all()
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
@role_required('administrador', 'vendedor')
def api_preco_medio_geral():
    # Verificar se o usuário tem empresa_id definido
    empresa_id = getattr(current_user, 'empresa_id', None)
    if empresa_id is None:
        return jsonify({'error': 'Usuário precisa estar associado a uma empresa'}), 403
    
    produtos = Produto.query.filter_by(empresa_id=empresa_id).all()
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
    form = CadastroUsuarioForm()
    if form.validate_on_submit():
        if Usuario.query.filter_by(email=form.email.data).first():
            flash('Este e-mail já está cadastrado.', 'danger')
            return redirect(url_for('registrar'))
        
        # Criar usuário sem empresa (empresa_id será None)
        # Apenas o administrador do sistema poderá relacionar usuários com empresas
        usuario = Usuario(
            nome=form.nome.data,
            email=form.email.data,
            role=(getattr(form, 'role', None).data if hasattr(form, 'role') else 'vendedor'),
            empresa_id=None  # Usuário criado sem empresa
        )
        usuario.set_password(form.senha.data)
        db.session.add(usuario)
        db.session.commit()
        flash('Conta criada com sucesso! Agora é só entrar.', 'success')
        return redirect(url_for('login'))
    else:
        print('Formulário NÃO validado:', form.errors)
    return render_template('registrar.html', form=form)

# ---------------------- Administração de Empresas (site_admin) ----------------------
@app.route('/empresas', methods=['GET', 'POST'])
@login_required
@role_required('site_admin')
def empresas():
    """Listagem e criação de empresas (somente para site_admin).

    - GET: lista empresas (ativas e inativas)
    - POST: cria nova empresa se nome ainda não existir
    """
    form = EmpresaForm()
    if form.validate_on_submit():
        existente = Empresa.query.filter_by(nome=form.nome.data).first()
        if existente:
            flash('Já existe uma empresa com este nome.', 'warning')
        else:
            nova = Empresa(nome=form.nome.data, cnpj=form.cnpj.data or None)
            db.session.add(nova)
            db.session.commit()
            flash('Empresa criada com sucesso.', 'success')
            return redirect(url_for('empresas'))
    empresas = Empresa.query.order_by(Empresa.nome.asc()).all()
    return render_template('empresas.html', form=form, empresas=empresas)


@app.route('/empresas/<int:empresa_id>/editar', methods=['GET', 'POST'])
@login_required
@role_required('site_admin')
def editar_empresa(empresa_id):
    """Edição de dados da empresa (somente para site_admin)."""
    empresa = db.session.get(Empresa, empresa_id)
    if not empresa:
        flash('Empresa não encontrada.', 'danger')
        return redirect(url_for('empresas'))
    form = EmpresaForm(obj=empresa)
    if form.validate_on_submit():
        # Verifica duplicidade de nome ao editar
        duplicada = Empresa.query.filter(Empresa.nome == form.nome.data, Empresa.id != empresa.id).first()
        if duplicada:
            flash('Já existe outra empresa com este nome.', 'warning')
        else:
            empresa.nome = form.nome.data
            empresa.cnpj = form.cnpj.data or None
            db.session.commit()
            flash('Empresa atualizada com sucesso.', 'success')
            return redirect(url_for('empresas'))
    return render_template('empresas.html', form=form, empresas=Empresa.query.order_by(Empresa.nome.asc()).all(), editar_id=empresa.id)


@app.route('/empresas/<int:empresa_id>/deletar', methods=['POST'])
@login_required
@role_required('site_admin')
def deletar_empresa(empresa_id):
    """Desativa (soft delete) uma empresa após verificar vínculos básicos."""
    empresa = db.session.get(Empresa, empresa_id)
    if not empresa:
        flash('Empresa não encontrada.', 'danger')
        return redirect(url_for('empresas'))

    # Verificações de vínculo: usuários, produtos, movimentações, compartilhamentos
    tem_usuario = db.session.execute(text('SELECT 1 FROM usuario WHERE empresa_id = :id LIMIT 1'), {'id': empresa.id}).first() is not None
    tem_produto = db.session.execute(text('SELECT 1 FROM produto WHERE empresa_id = :id LIMIT 1'), {'id': empresa.id}).first() is not None
    tem_mov = db.session.execute(text('SELECT 1 FROM movimentacao WHERE empresa_id = :id LIMIT 1'), {'id': empresa.id}).first() is not None
    tem_comp = db.session.execute(text('SELECT 1 FROM compartilhamento_empresa WHERE empresa_a_id = :id OR empresa_b_id = :id LIMIT 1'), {'id': empresa.id}).first() is not None

    if any([tem_usuario, tem_produto, tem_mov, tem_comp]):
        flash('Não é possível excluir: a empresa possui vínculos com dados.', 'warning')
        return redirect(url_for('editar_empresa', empresa_id=empresa.id))

    # Soft delete (desativação)
    empresa.ativo = False
    db.session.commit()
    flash('Empresa desativada com sucesso.', 'success')
    return redirect(url_for('empresas'))


@app.route('/empresas/<int:empresa_id>/reativar', methods=['POST'])
@login_required
@role_required('site_admin')
def reativar_empresa(empresa_id):
    """Reativa uma empresa desativada (soft delete)."""
    empresa = db.session.get(Empresa, empresa_id)
    if not empresa:
        flash('Empresa não encontrada.', 'danger')
        return redirect(url_for('empresas'))
    empresa.ativo = True
    db.session.commit()
    flash('Empresa reativada com sucesso.', 'success')
    return redirect(url_for('empresas'))


@app.route('/empresas/<int:empresa_id>/excluir_permanentemente', methods=['POST'])
@login_required
@role_required('site_admin')
def excluir_empresa_permanentemente(empresa_id):
    """Exclui permanentemente uma empresa (hard delete) após verificar vínculos."""
    empresa = db.session.get(Empresa, empresa_id)
    if not empresa:
        flash('Empresa não encontrada.', 'danger')
        return redirect(url_for('empresas'))

    # Verificações de vínculo: usuários, produtos, movimentações, compartilhamentos
    tem_usuario = db.session.execute(text('SELECT 1 FROM usuario WHERE empresa_id = :id LIMIT 1'), {'id': empresa.id}).first() is not None
    tem_produto = db.session.execute(text('SELECT 1 FROM produto WHERE empresa_id = :id LIMIT 1'), {'id': empresa.id}).first() is not None
    tem_mov = db.session.execute(text('SELECT 1 FROM movimentacao WHERE empresa_id = :id LIMIT 1'), {'id': empresa.id}).first() is not None
    tem_comp = db.session.execute(text('SELECT 1 FROM compartilhamento_empresa WHERE empresa_a_id = :id OR empresa_b_id = :id LIMIT 1'), {'id': empresa.id}).first() is not None

    if any([tem_usuario, tem_produto, tem_mov, tem_comp]):
        flash('Não é possível excluir permanentemente: a empresa possui vínculos com dados.', 'warning')
        return redirect(url_for('empresas'))

    # Hard delete (exclusão permanente)
    db.session.delete(empresa)
    db.session.commit()
    flash('Empresa excluída permanentemente com sucesso.', 'success')
    return redirect(url_for('empresas'))

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
@role_required('administrador', 'vendedor')
def api_dashboard():
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
    def custo_medio(produto):
        compras = [m for m in produto.movimentacoes if m.tipo == 'compra']
        total_qtd = sum(m.quantidade for m in compras)
        total_valor = sum(m.quantidade * m.valor_unitario for m in compras)
        return (total_valor / total_qtd) if total_qtd > 0 else 0
    total_estoque = sum(p.quantidade_estoque for p in produtos)
    valor_estoque = sum(max(p.quantidade_estoque, 0) * p.preco_compra for p in produtos)
    mes = datetime.now().month
    ano = datetime.now().year
    vendas = (
        Movimentacao.query.filter(Movimentacao.tipo=='venda', Movimentacao.empresa_id.in_(empresas_visiveis_ids()))
        .filter(extract('month', Movimentacao.data) == mes, extract('year', Movimentacao.data) == ano)
        .all()
    )
    margem_lucro = 0
    for venda in vendas:
        produto = Produto.query.get(venda.produto_id)
        custo = venda.custo_unitario if venda.custo_unitario is not None else custo_medio(produto)
        margem_lucro += (venda.valor_unitario - custo) * venda.quantidade
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
            'foto_perfil': current_user.foto_perfil,
            'role': getattr(current_user, 'role', None),
            'empresa_id': getattr(current_user, 'empresa_id', None)
        }
    })

@app.route('/api/produtos')
@login_required
@role_required('administrador', 'vendedor')
def api_produtos():
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
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
@role_required('administrador', 'vendedor')
def api_movimentacoes():
    movimentacoes = (
        Movimentacao.query.filter(Movimentacao.empresa_id.in_(empresas_visiveis_ids()))
        .order_by(Movimentacao.data.desc()).all()
    )
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
@role_required('administrador', 'vendedor')
def listar_produtos():
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
    return render_template('produtos.html', produtos=produtos)

@app.route('/inventario')
@login_required
@role_required('administrador', 'vendedor')
def inventario():
    return render_template('inventario.html')

@app.route('/previsao_demanda')
@login_required
@role_required('administrador', 'vendedor')
def previsao_demanda():
    return render_template('previsao_demanda.html')

@app.route('/estoque_niveis')
@login_required
@role_required('administrador', 'vendedor')
def estoque_niveis():
    return render_template('estoque_niveis.html')

@app.route('/fornecedores')
@login_required
@role_required('administrador', 'vendedor')
def fornecedores():
    return render_template('fornecedores.html')

@app.route('/qualidade')
@login_required
@role_required('administrador', 'vendedor')
def qualidade():
    return render_template('qualidade.html')

@app.route('/analise_dados')
@login_required
@role_required('administrador', 'vendedor')
def analise_dados():
    return render_template('analise_dados.html')

@app.route('/logistica_reversa')
@login_required
@role_required('administrador', 'vendedor')
def logistica_reversa():
    return render_template('logistica_reversa.html')

@app.route('/relatorio_estoque')
@login_required
@role_required('administrador', 'contador')
def relatorio_estoque():
    return render_template('relatorio_estoque.html')

@app.route('/relatorio_geral_completo')
@login_required
@role_required('administrador', 'contador')
def relatorio_geral_completo():
    return render_template('relatorio_geral_completo.html')

# 1. Inventário: Listar todos os itens em estoque
@app.route('/api/inventario', methods=['GET'])
@login_required
def api_inventario():
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
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
    
    # Verificar se o usuário tem empresa_id definido
    empresa_id = getattr(current_user, 'empresa_id', None)
    if empresa_id is None:
        return jsonify({'error': 'Usuário precisa estar associado a uma empresa'}), 403
    
    mov = Movimentacao(
        produto_id=data['produto_id'],
        tipo=data['tipo'],
        quantidade=data['quantidade'],
        valor_unitario=data['valor_unitario'],
        custo_unitario=data.get('custo_unitario'),
        usuario_id=current_user.id,
        empresa_id=empresa_id
    )
    produto = Produto.query.filter_by(id=data['produto_id'], empresa_id=empresa_id).first_or_404()
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
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
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
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
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
    # Verificar se o usuário tem empresa_id definido
    empresa_ids = empresas_visiveis_ids()
    if not empresa_ids:
        return jsonify({'error': 'Usuário precisa estar associado a uma empresa'}), 403
    
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresa_ids)).all()
    total_estoque = sum(p.quantidade_estoque for p in produtos)
    total_valor = sum(p.quantidade_estoque * p.preco_compra for p in produtos)
    return jsonify({'total_estoque': total_estoque, 'valor_estoque': total_valor})

# 8. Logística Reversa: Registrar devolução
@app.route('/api/devolucao', methods=['POST'])
@login_required
def api_registrar_devolucao():
    # Verificar se o usuário tem empresa_id definido
    empresa_id = getattr(current_user, 'empresa_id', None)
    if empresa_id is None:
        return jsonify({'error': 'Usuário precisa estar associado a uma empresa'}), 403
    
    data = request.json
    mov = Movimentacao(
        produto_id=data['produto_id'],
        tipo='devolucao',
        quantidade=data['quantidade'],
        valor_unitario=data['valor_unitario'],
        custo_unitario=None,
        usuario_id=current_user.id,
        empresa_id=empresa_id
    )
    produto = Produto.query.filter_by(id=data['produto_id'], empresa_id=empresa_id).first_or_404()
    produto.quantidade_estoque += data['quantidade']
    db.session.add(mov)
    db.session.commit()
    return jsonify({'status': 'ok', 'movimentacao_id': mov.id})


# 9. Relatórios: Relatório geral de estoque
@app.route('/api/relatorio_estoque', methods=['GET'])
@login_required
def api_relatorio_estoque():
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
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
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
    movimentacoes = Movimentacao.query.filter(Movimentacao.empresa_id.in_(empresas_visiveis_ids())).all()
    
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
    
    # Cálculo dos novos campos fiscais
    devolucoes_venda = sum(m.desconto_venda for m in movimentacoes if m.tipo == 'devolucao')
    descontos_venda = sum(m.desconto_venda for m in movimentacoes if m.tipo == 'venda')
    impostos_vendas = sum(m.imposto_vendas for m in movimentacoes if m.tipo == 'venda')
    cmv_total = sum(m.cmv for m in movimentacoes if m.tipo == 'venda')
    despesas_administrativas = sum(m.despesas_administrativas for m in movimentacoes)
    despesas_comerciais = sum(m.despesas_comerciais for m in movimentacoes)

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
        'categorias': categorias,
        'devolucoes_venda': round(devolucoes_venda, 2),
        'descontos_venda': round(descontos_venda, 2),
        'impostos_vendas': round(impostos_vendas, 2),
        'cmv_total': round(cmv_total, 2),
        'despesas_administrativas': round(despesas_administrativas, 2),
        'despesas_comerciais': round(despesas_comerciais, 2)
    })

@app.route('/relatorio_geral_completo/pdf')
@login_required
def relatorio_geral_pdf():
    produtos = Produto.query.filter(Produto.empresa_id.in_(empresas_visiveis_ids())).all()
    movimentacoes = Movimentacao.query.filter(Movimentacao.empresa_id.in_(empresas_visiveis_ids())).all()
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
    # Cálculo dos novos campos fiscais para PDF
    devolucoes_venda = sum(m.desconto_venda for m in movimentacoes if m.tipo == 'devolucao')
    descontos_venda = sum(m.desconto_venda for m in movimentacoes if m.tipo == 'venda')
    impostos_vendas = sum(m.imposto_vendas for m in movimentacoes if m.tipo == 'venda')
    cmv_total = sum(m.cmv for m in movimentacoes if m.tipo == 'venda')
    despesas_administrativas = sum(m.despesas_administrativas for m in movimentacoes)
    despesas_comerciais = sum(m.despesas_comerciais for m in movimentacoes)

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
        'categorias': categorias,
        'devolucoes_venda': round(devolucoes_venda, 2),
        'descontos_venda': round(descontos_venda, 2),
        'impostos_vendas': round(impostos_vendas, 2),
        'cmv_total': round(cmv_total, 2),
        'despesas_administrativas': round(despesas_administrativas, 2),
        'despesas_comerciais': round(despesas_comerciais, 2)
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

# ===== SISTEMA DE DEVOLUÇÃO =====

@app.route('/devolucoes')
@login_required
def listar_devolucoes():
    """Lista todas as devoluções registradas"""
    devolucoes = (
        Devolucao.query.join(Movimentacao, Devolucao.movimentacao_id == Movimentacao.id)
        .filter(Movimentacao.empresa_id.in_(empresas_visiveis_ids()))
        .order_by(Devolucao.data_devolucao.desc()).all()
    )
    total_devolvido = sum(d.valor_devolvido for d in devolucoes)
    total_quantidade = sum(d.quantidade_devolvida for d in devolucoes)
    
    return render_template('devolucoes.html', 
                         devolucoes=devolucoes,
                         total_devolvido=total_devolvido,
                         total_quantidade=total_quantidade)

@app.route('/registrar_devolucao', methods=['GET', 'POST'])
@login_required
def registrar_devolucao():
    """Registra uma nova devolução"""
    form = DevolucaoForm()
    
    # Carregar apenas vendas para o formulário
    vendas = (
        Movimentacao.query.filter(Movimentacao.tipo=='venda', Movimentacao.empresa_id.in_(empresas_visiveis_ids()))
        .order_by(Movimentacao.data.desc()).all()
    )
    form.movimentacao_id.choices = [(v.id, f"{v.produto.nome} - {v.data.strftime('%d/%m/%Y')} - Qtd: {v.quantidade}") for v in vendas]
    
    if form.validate_on_submit():
        # Buscar a movimentação original
        movimentacao = Movimentacao.query.filter(Movimentacao.id==form.movimentacao_id.data, Movimentacao.empresa_id.in_(empresas_visiveis_ids())).first()
        
        if not movimentacao:
            flash('Venda não encontrada!', 'danger')
            return redirect(url_for('registrar_devolucao'))
        
        # Validar quantidade
        if form.quantidade_devolvida.data > movimentacao.quantidade:
            flash('Quantidade devolvida não pode ser maior que a quantidade vendida!', 'danger')
            return redirect(url_for('registrar_devolucao'))
        
        # Calcular valor devolvido
        valor_devolvido = form.quantidade_devolvida.data * movimentacao.valor_unitario
        
        # Criar registro de devolução
        devolucao = Devolucao(
            movimentacao_id=movimentacao.id,
            produto_id=movimentacao.produto_id,
            quantidade_devolvida=form.quantidade_devolvida.data,
            motivo_devolucao=form.motivo_devolucao.data,
            valor_devolvido=valor_devolvido,
            usuario_id=current_user.id
        )
        
        # Atualizar estoque do produto
        produto = Produto.query.filter(Produto.id==movimentacao.produto_id, Produto.empresa_id.in_(empresas_visiveis_ids())).first_or_404()
        produto.quantidade_estoque += form.quantidade_devolvida.data
        
        # Registrar auditoria
        auditoria = Auditoria(
            usuario_id=current_user.id,
            acao='Devolução',
            entidade='Produto',
            entidade_id=produto.id,
            detalhes=f'Devolução de {form.quantidade_devolvida.data} unidade(s) do produto {produto.nome}. Motivo: {form.motivo_devolucao.data}'
        )
        
        db.session.add(devolucao)
        db.session.add(auditoria)
        db.session.commit()
        
        flash('Devolução registrada com sucesso!', 'success')
        return redirect(url_for('listar_devolucoes'))
    
    return render_template('registrar_devolucao.html', form=form)

@app.route('/api/movimentacao/<int:movimentacao_id>')
@login_required
def api_movimentacao_detalhes(movimentacao_id):
    """API para obter detalhes de uma movimentação específica"""
    movimentacao = Movimentacao.query.get(movimentacao_id)
    if not movimentacao:
        return jsonify({'error': 'Movimentação não encontrada'}), 404
    
    return jsonify({
        'produto': movimentacao.produto.nome,
        'quantidade': movimentacao.quantidade,
        'valor_unitario': movimentacao.valor_unitario,
        'data': movimentacao.data.strftime('%d/%m/%Y %H:%M')
    })

@app.route('/debug_produtos')
@login_required
def debug_produtos():
    """Rota de debug para verificar produtos e empresas visíveis"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Usuário não autenticado'})
    
    # Debug da função empresas_visiveis_ids
    empresas_ids = empresas_visiveis_ids()
    
    # Todos os produtos sem filtro
    todos_produtos = Produto.query.all()
    
    # Produtos filtrados pela função
    produtos_filtrados = Produto.query.filter(Produto.empresa_id.in_(empresas_ids)).all()
    
    # Informações do usuário atual
    usuario_info = {
        'id': current_user.id,
        'nome': current_user.nome,
        'empresa_id': getattr(current_user, 'empresa_id', None),
        'role': getattr(current_user, 'role', None)
    }
    
    return jsonify({
        'usuario': usuario_info,
        'empresas_visiveis_ids': empresas_ids,
        'total_produtos_sem_filtro': len(todos_produtos),
        'total_produtos_filtrados': len(produtos_filtrados),
        'produtos_sem_filtro': [
            {
                'id': p.id,
                'nome': p.nome,
                'empresa_id': p.empresa_id,
                'quantidade_estoque': p.quantidade_estoque
            } for p in todos_produtos
        ],
        'produtos_filtrados': [
            {
                'id': p.id,
                'nome': p.nome,
                'empresa_id': p.empresa_id,
                'quantidade_estoque': p.quantidade_estoque
            } for p in produtos_filtrados
        ]
    })

@app.route('/corrigir_produtos_empresa')
@login_required
@role_required('administrador')
def corrigir_produtos_empresa():
    """Corrige produtos existentes que não tenham empresa_id definido"""
    try:
        # Buscar produtos sem empresa_id
        produtos_sem_empresa = Produto.query.filter_by(empresa_id=None).all()
        
        if not produtos_sem_empresa:
            flash('Todos os produtos já têm empresa_id definido.', 'info')
            return redirect(url_for('index'))
        
        # Verificar se o usuário tem empresa_id definido
        empresa_id = getattr(current_user, 'empresa_id', None)
        if empresa_id is None:
            flash('Você precisa estar associado a uma empresa para corrigir produtos.', 'warning')
            return redirect(url_for('index'))
        
        # Atualizar produtos
        for produto in produtos_sem_empresa:
            produto.empresa_id = empresa_id
        
        db.session.commit()
        
        flash(f'{len(produtos_sem_empresa)} produtos foram corrigidos com empresa_id={empresa_id}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao corrigir produtos: {e}', 'danger')
    
    return redirect(url_for('index'))

# ---------------------- Administração de Usuários (site_admin) ----------------------
@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
@role_required('site_admin')
def usuarios():
    """Listagem e gerenciamento de usuários (somente para site_admin).

    - GET: lista todos os usuários
    - POST: atualiza empresa_id de um usuário
    """
    if request.method == 'POST':
        usuario_id = request.form.get('usuario_id')
        empresa_id = request.form.get('empresa_id')
        
        if usuario_id and empresa_id:
            usuario = Usuario.query.get(usuario_id)
            empresa = Empresa.query.get(empresa_id)
            
            if usuario and empresa:
                usuario.empresa_id = empresa.id
                db.session.commit()
                flash(f'Usuário {usuario.nome} associado à empresa {empresa.nome}.', 'success')
            else:
                flash('Usuário ou empresa não encontrados.', 'danger')
        elif usuario_id and empresa_id == '':
            # Remover empresa do usuário
            usuario = Usuario.query.get(usuario_id)
            if usuario:
                usuario.empresa_id = None
                db.session.commit()
                flash(f'Usuário {usuario.nome} removido da empresa.', 'success')
    
    usuarios = Usuario.query.order_by(Usuario.nome.asc()).all()
    empresas = Empresa.query.order_by(Empresa.nome.asc()).all()
    
    return render_template('usuarios.html', usuarios=usuarios, empresas=empresas)

@app.route('/teste_compartilhamento')
@login_required
@role_required('site_admin')
def teste_compartilhamento():
    """Rota para testar o compartilhamento em tempo real"""
    
    # Buscar todas as empresas ativas
    empresas = Empresa.query.filter_by(ativo=True).order_by(Empresa.nome).all()
    
    # Buscar todos os relacionamentos ativos entre empresas
    relacoes_ativas = CompartilhamentoEmpresa.query.filter(
        CompartilhamentoEmpresa.empresa_a_id != CompartilhamentoEmpresa.empresa_b_id,
        CompartilhamentoEmpresa.ativo == True
    ).all()
    
    # Buscar dados compartilhados para cada relacionamento
    dados_compartilhados = {}
    for rel in relacoes_ativas:
        # Buscar dados das empresas relacionadas
        produtos_empresa_a = Produto.query.filter_by(empresa_id=rel.empresa_a_id).limit(5).all()
        produtos_empresa_b = Produto.query.filter_by(empresa_id=rel.empresa_b_id).limit(5).all()
        
        movimentacoes_empresa_a = Movimentacao.query.filter_by(empresa_id=rel.empresa_a_id).limit(5).all()
        movimentacoes_empresa_b = Movimentacao.query.filter_by(empresa_id=rel.empresa_b_id).limit(5).all()
        
        dados_compartilhados[rel.id] = {
            'empresa_a': Empresa.query.get(rel.empresa_a_id),
            'empresa_b': Empresa.query.get(rel.empresa_b_id),
            'produtos_a': produtos_empresa_a,
            'produtos_b': produtos_empresa_b,
            'movimentacoes_a': movimentacoes_empresa_a,
            'movimentacoes_b': movimentacoes_empresa_b,
            'total_produtos_a': Produto.query.filter_by(empresa_id=rel.empresa_a_id).count(),
            'total_produtos_b': Produto.query.filter_by(empresa_id=rel.empresa_b_id).count(),
            'total_movimentacoes_a': Movimentacao.query.filter_by(empresa_id=rel.empresa_a_id).count(),
            'total_movimentacoes_b': Movimentacao.query.filter_by(empresa_id=rel.empresa_b_id).count(),
            'relacionamento': rel
        }
    
    return render_template('teste_compartilhamento.html',
                         empresas=empresas,
                         dados_compartilhados=dados_compartilhados)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        safe_add_column_ativo_empresa()
        ensure_schema_columns()
        seed_site_admin()
        try:
            calcular_campos_fiscais_automaticamente()
        except Exception as e:
            print(f"Erro ao calcular campos fiscais: {e}")
    app.run(debug=True)
