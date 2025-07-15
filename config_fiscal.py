# Taxa de impostos sobre vendas (ICMS + PIS/COFINS)
TAXA_IMPOSTOS_VENDAS = 0.18  # 18%

# Taxa de despesas administrativas
TAXA_DESPESAS_ADMINISTRATIVAS = 0.02  # 2%

# Taxa de despesas comerciais
TAXA_DESPESAS_COMERCIAIS = 0.03  # 3% 

# Configurações de CMV (Custo das Mercadorias Vendidas)
def calcular_impostos_vendas(valor_unitario, quantidade):
    """Calcula impostos sobre vendas"""
    return valor_unitario * quantidade * TAXA_IMPOSTOS_VENDAS

def calcular_desconto_venda(valor_unitario, quantidade, percentual_desconto=None):
    """Calcula desconto sobre venda baseado SOMENTE no percentual informado pelo usuário"""
    valor_total = valor_unitario * quantidade
    if percentual_desconto is not None and percentual_desconto > 0:
        return valor_total * (percentual_desconto / 100)
    return 0.0

def calcular_despesas_administrativas(valor_unitario, quantidade):
    """Calcula despesas administrativas"""
    return valor_unitario * quantidade * TAXA_DESPESAS_ADMINISTRATIVAS

def calcular_despesas_comerciais(valor_unitario, quantidade):
    """Calcula despesas comerciais"""
    return valor_unitario * quantidade * TAXA_DESPESAS_COMERCIAIS

def calcular_cmv(custo_unitario, quantidade):
    """Calcula CMV (Custo das Mercadorias Vendidas)"""
    return custo_unitario * quantidade if custo_unitario else 0.0 