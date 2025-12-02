# restaurante_sistema/views/dashboard_view.py
import flet as ft
import database
from datetime import datetime, timedelta
import json
from collections import Counter

from utils.components import StyledCard, Title

def DashboardView(cores): 
    
    # --- LÓGICA DE DADOS ---
    def get_dashboard_data():
        conn, cursor = database.conectar()
        alertas_estoque_baixo = []
        alertas_validade = []
        hoje = datetime.now()
        
        cursor.execute("SELECT id, valor_compra FROM estoque")
        custos_compra = {row['id']: row['valor_compra'] for row in cursor.fetchall()}
        
        cursor.execute("SELECT itens, total FROM transacoes WHERE tipo = 'entrada'")
        todas_transacoes = cursor.fetchall()
        
        lucro_bruto_total = 0
        total_vendas_total = 0
        
        for transacao in todas_transacoes:
            venda_total = transacao['total']
            custo_total = 0
            if transacao['itens']:
                try:
                    itens = json.loads(transacao['itens'])
                    for item in itens:
                        produto_id = item['id']
                        quantidade_vendida = item['quantidade']
                        custo_unitario = custos_compra.get(produto_id, 0)
                        custo_total += custo_unitario * quantidade_vendida
                except (json.JSONDecodeError, TypeError):
                    pass
            lucro_bruto_total += (venda_total - custo_total)
            total_vendas_total += venda_total

        cursor.execute("SELECT nome FROM estoque WHERE quantidade <= 0 ORDER BY nome")
        for row in cursor.fetchall():
            alertas_estoque_baixo.append(f"{row['nome']}: Acabou!")

        cursor.execute("SELECT nome, quantidade, unidade FROM estoque WHERE quantidade > 0 AND quantidade <= estoque_minimo ORDER BY nome")
        for row in cursor.fetchall():
            qtd_formatada = f"{row['quantidade']:.2f}".rstrip('0').rstrip('.')
            alertas_estoque_baixo.append(f"{row['nome']}: Restam apenas {qtd_formatada} {row['unidade']}.")

        data_limite = (hoje + timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("SELECT nome, data_validade FROM estoque WHERE data_validade != 'N/A' AND date(data_validade) BETWEEN date('now', 'localtime') AND date(?) ORDER BY data_validade", (data_limite,))
        for row in cursor.fetchall():
            data_venc = datetime.strptime(row['data_validade'], '%Y-%m-%d')
            dias_restantes = (data_venc.date() - hoje.date()).days
            
            if dias_restantes <= 0: msg_vencimento = "vence hoje!"
            elif dias_restantes == 1: msg_vencimento = "vence amanhã!"
            else: msg_vencimento = f"vence em {dias_restantes} dias ({data_venc.strftime('%d/%m')})."
            alertas_validade.append(f"{row['nome']} {msg_vencimento}")

        cursor.execute("SELECT SUM(total) as faturamento FROM transacoes WHERE tipo = 'entrada' AND date(data_venda) = date('now', 'localtime')")
        faturamento_dia = cursor.fetchone()['faturamento'] or 0

        cursor.execute("SELECT AVG(total) as ticket_medio FROM transacoes WHERE tipo = 'entrada' AND date(data_venda) = date('now', 'localtime')")
        ticket_medio = cursor.fetchone()['ticket_medio'] or 0

        cursor.execute("SELECT SUM(CASE WHEN tipo = 'entrada' THEN total ELSE -total END) as saldo FROM transacoes")
        saldo_caixa = cursor.fetchone()['saldo'] or 0
        
        contador_produtos = Counter()
        for venda in todas_transacoes:
            if venda['itens']:
                try:
                    itens = json.loads(venda['itens'])
                    for item in itens:
                        contador_produtos[item['nome']] += item['quantidade']
                except (json.JSONDecodeError, TypeError):
                    pass
        
        produtos_mais_vendidos = contador_produtos.most_common(5)

        conn.close()
        return faturamento_dia, ticket_medio, saldo_caixa, alertas_estoque_baixo, alertas_validade, produtos_mais_vendidos, lucro_bruto_total, total_vendas_total

    faturamento_dia, ticket_medio, saldo_caixa, alertas_estoque, alertas_validade, produtos_mais_vendidos, lucro_bruto_total, total_vendas_total = get_dashboard_data()
    
    def create_info_card(title, value, color_key):
        return StyledCard(
            content=ft.Container(
                content=ft.Column(
                    [
                        # CORREÇÃO: FontWeight.W_500
                        ft.Text(title, size=16, weight=ft.FontWeight.W_500, color=cores["texto_secundario"]),
                        ft.Text(value, size=32, weight=ft.FontWeight.BOLD, color=cores[color_key]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
            cores=cores,
            expand=True
        )

    faturamento_card = create_info_card("Faturamento do Dia", f"R$ {faturamento_dia:.2f}", "verde")
    lucro_card = create_info_card("Lucro Bruto (Total)", f"R$ {lucro_bruto_total:.2f}", "primaria")
    ticket_medio_card = create_info_card("Ticket Médio (Dia)", f"R$ {ticket_medio:.2f}", "texto_primario")
    saldo_caixa_card = create_info_card("Saldo em Caixa", f"R$ {saldo_caixa:.2f}", "texto_primario")
    
    cor_grafico = ft.Colors.with_opacity(0.8, cores["primaria"])
    cor_grade = ft.Colors.with_opacity(0.1, cores["texto_primario"])
    cor_texto_eixo = cores["texto_secundario"]

    top_produtos_chart = ft.BarChart(
        bar_groups=[
            ft.BarChartGroup(
                x=i,
                bar_rods=[ ft.BarChartRod(from_y=0, to_y=qtd, width=25, color=cor_grafico, border_radius=4, tooltip=f"{nome}: {int(qtd)}") ]
            ) for i, (nome, qtd) in enumerate(produtos_mais_vendidos)
        ] if produtos_mais_vendidos else [],
        tooltip_bgcolor=cores["surface"],
        border=ft.border.all(0, ft.Colors.TRANSPARENT),
        horizontal_grid_lines=ft.ChartGridLines(interval=10, color=cor_grade),
        bottom_axis=ft.ChartAxis(
            labels=[ ft.ChartAxisLabel(value=i, label=ft.Text(nome.split()[0], size=11, color=cor_texto_eixo)) for i, (nome, qtd) in enumerate(produtos_mais_vendidos) ],
            labels_size=40,
        ),
        # CORREÇÃO: Removido text_style/labels_style que causava erro
        left_axis=ft.ChartAxis(
            labels_size=60, 
            title=ft.Text("Qtd.", color=cor_texto_eixo), 
            title_size=12
        ),
        expand=True
    )

    top_produtos_card = StyledCard(
        content=ft.Container(
            padding=10, 
            content=ft.Column([
                ft.Text("Top 5 Produtos Mais Vendidos", size=18, weight=ft.FontWeight.BOLD, color=cores["texto_primario"]),
                ft.Container(
                    content=top_produtos_chart if produtos_mais_vendidos else ft.Text("Nenhuma venda registrada ainda.", text_align="center", color=cores["texto_secundario"]), 
                    expand=True, 
                    padding=ft.padding.only(top=20)
                )
            ]),
        ),
        cores=cores,
        expand=True,
    )
    
    def create_alert_card(title, icon, icon_color_key, alertas):
        alert_content = [
            ft.Row([
                ft.Icon(icon, color=cores[icon_color_key]), 
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=cores["texto_primario"])
            ]),
            ft.Divider(color=cor_grade, height=10),
        ]
        
        if alertas:
            alert_content.extend([ft.Text(alerta, color=cores["texto_secundario"]) for alerta in alertas])
        else:
            alert_content.append(ft.Text("Nenhum alerta.", color=cores["texto_secundario"], italic=True))

        return StyledCard(
            content=ft.Container(padding=15, content=ft.Column(alert_content, spacing=10)),
            cores=cores,
        )

    estoque_baixo_card = create_alert_card("Alertas de Estoque", ft.Icons.INVENTORY_2, "primaria", alertas_estoque)
    validade_card = create_alert_card("Próximos do Vencimento", ft.Icons.EVENT_BUSY, "primaria", alertas_validade)

    return ft.Column(
        controls=[
            Title("Dashboard", cores),
            ft.Row(controls=[faturamento_card, lucro_card]),
            ft.Row(controls=[ticket_medio_card, saldo_caixa_card]),
            ft.Row(controls=[top_produtos_card], expand=True),
            ft.Row(
                controls=[
                    ft.Container(content=estoque_baixo_card, expand=1),
                    ft.Container(content=validade_card, expand=1),
                ],
                spacing=20
            ),
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True,
    )