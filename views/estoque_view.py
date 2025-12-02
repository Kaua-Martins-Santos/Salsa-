# restaurante_sistema/views/estoque_view.py
import flet as ft
from datetime import datetime
import database
from utils.components import (
    StyledTextField, StyledButton, StyledOutlinedButton, 
    StyledCard, Title, SubTitle, StyledDataTable, BodyText
)

def EstoqueView(page: ft.Page, date_picker: ft.DatePicker, cores):

    # --- WIDGETS DO FORMULÁRIO ---
    produto_id_atual = ft.Text(value=None, visible=False)
    txt_nome = StyledTextField(label="Nome do Produto", cores=cores)
    txt_qtd = StyledTextField(label="Quantidade", cores=cores)
    txt_unidade = StyledTextField(label="Unidade (kg, un, L)", cores=cores)
    txt_valor = StyledTextField(label="Valor Unitário", prefix_text="R$", cores=cores)
    txt_fornecedor = StyledTextField(label="Fornecedor", cores=cores)
    txt_estoque_min = StyledTextField(label="Estoque Mínimo", cores=cores)
    
    titulo_formulario = SubTitle("Adicionar Novo Produto", cores)
    
    data_validade_text = BodyText("Selecione a data de validade", cores, is_secondary=True)
    data_reposicao_text = BodyText("Selecione a data de reposição", cores, is_secondary=True)
    campo_data_selecionada = None

    def handle_date_change(e):
        global campo_data_selecionada
        if not date_picker.value:
            return
            
        selected_date = date_picker.value.strftime('%d-%m-%Y')
        if campo_data_selecionada == 'validade':
            data_validade_text.value = selected_date
            data_validade_text.color = cores["texto_primario"]
        elif campo_data_selecionada == 'reposicao':
            data_reposicao_text.value = selected_date
            data_reposicao_text.color = cores["texto_primario"]
        page.update()

    def abrir_datepicker(e, campo):
        global campo_data_selecionada
        campo_data_selecionada = campo
        date_picker.value = datetime.now()
        date_picker.open = True
        date_picker.update()

    date_picker.on_change = handle_date_change
    
    # Containers para os campos de data
    campo_validade_container = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, color=cores["texto_secundario"]), data_validade_text]),
        padding=15, border=ft.border.all(1, cores["texto_secundario"]), border_radius=10,
        on_click=lambda e: abrir_datepicker(e, 'validade'), tooltip="Selecionar Data de Validade"
    )
    campo_reposicao_container = ft.Container(
        content=ft.Row([ft.Icon(ft.Icons.CALENDAR_TODAY, color=cores["texto_secundario"]), data_reposicao_text]),
        padding=15, border=ft.border.all(1, cores["texto_secundario"]), border_radius=10,
        on_click=lambda e: abrir_datepicker(e, 'reposicao'), tooltip="Selecionar Data de Reposição"
    )

    def limpar_formulario():
        produto_id_atual.value = ""
        txt_nome.value, txt_qtd.value, txt_unidade.value = "", "", ""
        txt_valor.value, txt_estoque_min.value, txt_fornecedor.value = "", "", ""
        data_validade_text.value = "Selecione a data de validade"
        data_validade_text.color = cores["texto_secundario"]
        data_reposicao_text.value = "Selecione a data de reposição"
        data_reposicao_text.color = cores["texto_secundario"]
        titulo_formulario.value = "Adicionar Novo Produto"
        btn_salvar.text = "Salvar"
        btn_cancelar.visible = False
        page.update()

    def salvar_produto(e):
        try:
            if not txt_nome.value:
                page.snack_bar = ft.SnackBar(ft.Text("O nome do produto é obrigatório."), bgcolor=ft.Colors.ORANGE_500)
                page.snack_bar.open = True; page.update(); return
            
            data_validade_db = datetime.strptime(data_validade_text.value, '%d-%m-%Y').strftime('%Y-%m-%d') if data_validade_text.value != "Selecione a data de validade" else "N/A"
            data_reposicao_db = datetime.strptime(data_reposicao_text.value, '%d-%m-%Y').strftime('%Y-%m-%d') if data_reposicao_text.value != "Selecione a data de reposição" else None

            qtd_valor = float(txt_qtd.value.replace(",", ".")) if txt_qtd.value else 0
            valor_compra_valor = float(txt_valor.value.replace(",", ".")) if txt_valor.value else 0
            estoque_min_valor = float(txt_estoque_min.value.replace(",", ".")) if txt_estoque_min.value else 0
            fornecedor_valor = txt_fornecedor.value if txt_fornecedor.value else "N/A"
            
            conn, cursor = database.conectar()
            
            if produto_id_atual.value:
                cursor.execute("UPDATE estoque SET nome=?, quantidade=?, unidade=?, valor_compra=?, data_validade=?, estoque_minimo=?, fornecedor=?, data_reposicao=? WHERE id=?", 
                               (txt_nome.value, qtd_valor, txt_unidade.value, valor_compra_valor, data_validade_db, estoque_min_valor, fornecedor_valor, data_reposicao_db, produto_id_atual.value))
            else:
                cursor.execute("INSERT INTO estoque (nome, quantidade, unidade, valor_compra, data_compra, data_validade, fornecedor, estoque_minimo, data_reposicao) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                               (txt_nome.value, qtd_valor, txt_unidade.value, valor_compra_valor, datetime.now().strftime('%Y-%m-%d'), data_validade_db, fornecedor_valor, estoque_min_valor, data_reposicao_db))
            
            conn.commit(); conn.close()
            page.snack_bar = ft.SnackBar(ft.Text("Produto salvo com sucesso!"), bgcolor=cores["verde"]); page.snack_bar.open = True
            limpar_formulario(); atualizar_tabela_estoque()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao salvar: {ex}"), bgcolor=cores["primaria"]); page.snack_bar.open = True; page.update()

    def carregar_produto_no_formulario(produto):
        produto_id_atual.value = str(produto['id']); txt_nome.value = produto['nome']
        txt_qtd.value = str(produto['quantidade']); txt_unidade.value = produto['unidade']
        txt_valor.value = str(produto['valor_compra']); txt_estoque_min.value = str(produto['estoque_minimo'])
        txt_fornecedor.value = produto['fornecedor']
        
        if produto['data_validade'] and produto['data_validade'] != "N/A":
            try:
                data_validade_text.value = datetime.strptime(produto['data_validade'], '%Y-%m-%d').strftime('%d-%m-%Y')
                data_validade_text.color = cores["texto_primario"]
            except: pass
        else:
            data_validade_text.value = "Selecione a data de validade"
            data_validade_text.color = cores["texto_secundario"]
            
        if produto['data_reposicao']:
            try:
                data_reposicao_text.value = datetime.strptime(produto['data_reposicao'], '%Y-%m-%d').strftime('%d-%m-%Y')
                data_reposicao_text.color = cores["texto_primario"]
            except: pass
        else:
            data_reposicao_text.value = "Selecione a data de reposição"
            data_reposicao_text.color = cores["texto_secundario"]

        titulo_formulario.value = f"Editando: {produto['nome']}"
        btn_salvar.text = "Atualizar"; btn_cancelar.visible = True
        page.update()

    def excluir_produto(produto):
        conn, cursor = database.conectar(); cursor.execute("DELETE FROM estoque WHERE id = ?", (produto['id'],)); conn.commit(); conn.close()
        page.snack_bar = ft.SnackBar(ft.Text(f"Produto '{produto['nome']}' removido!"), bgcolor=cores["primaria"]); page.snack_bar.open = True
        if str(produto['id']) == produto_id_atual.value: limpar_formulario()
        atualizar_tabela_estoque()

    # --- WIDGETS E LÓGICA DE BUSCA ---
    def buscar_produtos(e):
        atualizar_tabela_estoque(termo_busca=e.control.value)

    search_field = StyledTextField(
        label="Buscar por nome...",
        cores=cores,
        on_change=buscar_produtos,
        icon_name=ft.Icons.SEARCH,
    )
    
    btn_salvar = StyledButton(text="Salvar", cores=cores, on_click=salvar_produto, icon=ft.Icons.SAVE_AS)
    btn_cancelar = StyledOutlinedButton(text="Cancelar", cores=cores, on_click=lambda e: limpar_formulario(), icon=ft.Icons.CANCEL_OUTLINED, visible=False)
    
    tabela_produtos = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")), ft.DataColumn(ft.Text("Nome")),
            ft.DataColumn(ft.Text("Estoque")), ft.DataColumn(ft.Text("Validade")),
            ft.DataColumn(ft.Text("Fornecedor")), ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[]
    )

    def atualizar_tabela_estoque(termo_busca=None):
        conn, cursor = database.conectar()
        if termo_busca:
            cursor.execute("SELECT * FROM estoque WHERE nome LIKE ? ORDER BY nome", (f'%{termo_busca}%',))
        else:
            cursor.execute("SELECT * FROM estoque ORDER BY nome")
        produtos = cursor.fetchall(); conn.close()
        
        tabela_produtos.rows.clear()
        for p in produtos:
            validade_exibicao = "N/A"
            if p['data_validade'] and p['data_validade'] != "N/A":
                try:
                    validade_exibicao = datetime.strptime(p['data_validade'], '%Y-%m-%d').strftime('%d-%m-%Y') 
                except: pass

            tabela_produtos.rows.append(ft.DataRow(
                color=cores["surface"],
                cells=[
                    ft.DataCell(ft.Text(str(p['id']), color=cores["texto_secundario"])),
                    # CORREÇÃO: FontWeight.W_500
                    ft.DataCell(ft.Text(p['nome'], weight=ft.FontWeight.W_500, color=cores["texto_primario"])),
                    ft.DataCell(ft.Text(f"{p['quantidade']:.2f} {p['unidade']}", color=cores["texto_primario"])), 
                    ft.DataCell(ft.Text(validade_exibicao, color=cores["texto_primario"])),
                    ft.DataCell(ft.Text(p['fornecedor'] or "-", color=cores["texto_secundario"])),
                    ft.DataCell(ft.Row([
                        ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=ft.Colors.BLUE_500, on_click=lambda e, p=p: carregar_produto_no_formulario(p), tooltip="Editar"),
                        ft.IconButton(icon=ft.Icons.DELETE_SWEEP_OUTLINED, icon_color=cores["primaria"], on_click=lambda e, p=p: excluir_produto(p), tooltip="Excluir"),
                    ])),
                ]
            ))
        
        StyledDataTable(tabela_produtos, cores)
        if page: page.update()

    # --- ESTRUTURA FINAL DO LAYOUT ---
    atualizar_tabela_estoque()
    
    coluna_inventario = ft.Column(
        controls=[
            Title("Inventário de Produtos", cores),
            search_field,
            ft.Container(
                content=ft.ListView(controls=[tabela_produtos], expand=True),
                expand=True,
                border=ft.border.all(1, ft.Colors.with_opacity(0.1, cores["texto_primario"])),
                border_radius=10
            )
        ],
        expand=3,
        spacing=20
    )
    
    coluna_formulario = StyledCard(
        content=ft.Container(
            content=ft.Column(
                [
                    titulo_formulario, produto_id_atual, ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    txt_nome, txt_qtd, txt_unidade, txt_valor, 
                    txt_fornecedor, campo_validade_container, campo_reposicao_container, txt_estoque_min,
                    ft.Row(controls=[btn_cancelar, btn_salvar], spacing=10, alignment=ft.MainAxisAlignment.END)
                ], 
                scroll=ft.ScrollMode.ADAPTIVE
            ),
        ),
        cores=cores,
        expand=2
    )

    return ft.Row(
        controls=[coluna_inventario, ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.1, cores["texto_primario"])), coluna_formulario],
        vertical_alignment=ft.CrossAxisAlignment.START, expand=True, spacing=25
    )