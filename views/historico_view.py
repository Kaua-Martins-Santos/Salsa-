# restaurante_sistema/views/historico_view.py
import flet as ft
import database
import json
from datetime import datetime
from utils.components import Title, StyledDataTable, BodyText

def HistoricoView(page: ft.Page, cores):

    tabela_transacoes = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Data/Hora")),
            ft.DataColumn(ft.Text("Tipo")),
            ft.DataColumn(ft.Text("Descrição/Itens")),
            ft.DataColumn(ft.Text("Método Pgto.")),
            ft.DataColumn(ft.Text("Valor (R$)"), numeric=True),
        ],
        rows=[],
        expand=True,
    )

    def formatar_data(data_str):
        if not data_str: return ""
        try:
            data_obj = datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S')
            return data_obj.strftime('%d/%m/%Y %H:%M')
        except (ValueError, TypeError):
            return data_str

    def carregar_transacoes(termo_busca=""):
        conn, cursor = database.conectar()
        
        if termo_busca:
            cursor.execute("""
                SELECT * FROM transacoes 
                WHERE descricao LIKE ? OR itens LIKE ?
                ORDER BY data_venda DESC
            """, (f'%{termo_busca}%', f'%{termo_busca}%'))
        else:
            cursor.execute("SELECT * FROM transacoes ORDER BY data_venda DESC")
            
        transacoes = cursor.fetchall()
        conn.close()
        
        tabela_transacoes.rows.clear()
        for t in transacoes:
            tipo = t['tipo'].upper()
            cor_valor = cores["verde"] if tipo == 'ENTRADA' else cores["primaria"]
            
            descricao = t['descricao']
            if tipo == 'ENTRADA' and not descricao:
                try:
                    if t['itens']:
                        itens = json.loads(t['itens'])
                        descricao = ", ".join([f"{item['quantidade']}x {item['nome']}" for item in itens])
                    else:
                        descricao = "Sem itens"
                except:
                    descricao = "Erro ao ler itens"

            tabela_transacoes.rows.append(
                ft.DataRow(
                    color=cores["surface"],
                    cells=[
                        ft.DataCell(ft.Text(formatar_data(t['data_venda']), color=cores["texto_secundario"])),
                        ft.DataCell(ft.Text(tipo, color=cor_valor, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(descricao or "", color=cores["texto_primario"], italic=True)),
                        ft.DataCell(ft.Text(t['metodo_pagamento'] or "N/A", color=cores["texto_secundario"])),
                        ft.DataCell(ft.Text(f"{t['total']:.2f}", color=cor_valor, weight=ft.FontWeight.BOLD)),
                    ]
                )
            )
        
        StyledDataTable(tabela_transacoes, cores)
        page.update()

    def obter_sugestoes(e):
        termo = e.data
        if len(termo) < 2:
            search_bar.controls = []
            search_bar.update(); return
            
        conn, cursor = database.conectar()
        cursor.execute("SELECT DISTINCT descricao FROM transacoes WHERE tipo = 'saida' AND descricao LIKE ? LIMIT 5", (f'{termo}%',))
        sugestoes = cursor.fetchall()
        conn.close()
        
        search_bar.controls = [
            ft.ListTile(
                title=ft.Text(s['descricao'], color=cores["texto_primario"]), 
                on_click=selecionar_sugestao,
                bgcolor=cores["surface"]
            ) 
            for s in sugestoes
        ]
        search_bar.update()

    def selecionar_sugestao(e):
        texto = e.control.title.value
        search_bar.value = texto
        search_bar.close_view(texto)
        carregar_transacoes(termo_busca=texto)

    def buscar_na_barra(e):
        carregar_transacoes(termo_busca=e.data) 

    search_bar = ft.SearchBar(
        view_elevation=4,
        bar_hint_text="Buscar por descrição ou item...",
        on_change=obter_sugestoes,
        on_submit=buscar_na_barra,
        controls=[],
        bar_bgcolor=cores["surface"],
        # CORREÇÃO: text_style -> bar_text_style
        bar_text_style=ft.TextStyle(color=cores["texto_primario"]),
    )
    
    carregar_transacoes()

    return ft.Column(
        controls=[
            Title("Histórico de Transações", cores),
            search_bar,
            BodyText("Todas as movimentações de entrada e saída do caixa.", cores, is_secondary=True),
            ft.Divider(height=10, color=ft.Colors.with_opacity(0.1, cores["texto_primario"])),
            ft.Container(
                content=ft.ListView(controls=[tabela_transacoes], expand=True),
                expand=True,
                border=ft.border.all(1, ft.Colors.with_opacity(0.1, cores["texto_primario"])),
                border_radius=10
            )
        ],
        expand=True,
        spacing=20
    )