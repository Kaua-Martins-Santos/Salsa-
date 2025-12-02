# restaurante_sistema/views/comandas_view.py
import flet as ft
import database
import json
from datetime import datetime
from views.caixa_view import CaixaView
from utils.impressao import gerar_pedido_cozinha 
from utils.components import (
    StyledCard, Title, SubTitle, StyledButton, StyledTextButton, BodyText
)

class ComandasView:
    
    def __init__(self, page: ft.Page, cores):
        self.page = page
        self.cores = cores
        self.mesas = self.carregar_mesas()
        self.produtos_disponiveis = self.carregar_produtos_disponiveis()
        self.controle_mesas_display = ft.GridView(
            runs_count=5, spacing=10, run_spacing=10, max_extent=250,
            controls=self.renderizar_mesas(), expand=True
        )

        self.mesa_id_atual = None
        self.nome_mesa_atual = None
        self.pedido_id_atual = None
        self.lista_itens_edicao = ft.ListView(expand=True, spacing=10)
        self.total_comanda_texto = ft.Text("Total: R$ 0.00", size=20, weight=ft.FontWeight.BOLD, color=cores["texto_primario"])
        
        self.dialog_abrir_comanda = self.criar_dialogo_abrir_comanda()
        self.dialog_editar_comanda = self.criar_dialogo_edicao()
        
        self.page.overlay.extend([self.dialog_abrir_comanda, self.dialog_editar_comanda])

    # --- LÓGICA DE DADOS (Não muda) ---
    def carregar_mesas(self):
        conn, cursor = database.conectar()
        cursor.execute("SELECT * FROM mesas")
        mesas = cursor.fetchall()
        conn.close()
        return [dict(m) for m in mesas]

    def carregar_produtos_disponiveis(self):
        conn, cursor = database.conectar()
        cursor.execute("SELECT id, nome, valor_compra FROM estoque WHERE quantidade > 0 ORDER BY nome")
        produtos = cursor.fetchall()
        conn.close()
        return {p['id']: {'nome': p['nome'], 'preco_venda': p['valor_compra'] * 2} for p in produtos}
    
    def atualizar_status_mesa(self, mesa_id, novo_status):
        conn, cursor = database.conectar()
        cursor.execute("UPDATE mesas SET status = ? WHERE id = ?", (novo_status, mesa_id))
        conn.commit(); conn.close()
        for mesa in self.mesas:
            if mesa['id'] == mesa_id:
                mesa['status'] = novo_status
                break
        self.renderizar_e_atualizar_display()
        
    def carregar_pedido_aberto(self, mesa_id):
        conn, cursor = database.conectar()
        cursor.execute("SELECT * FROM pedidos WHERE mesa_id = ? AND status = 'ABERTO'", (mesa_id,))
        pedido = cursor.fetchone()
        conn.close()
        return dict(pedido) if pedido else None

    # --- RENDERIZAÇÃO DA TELA PRINCIPAL ---
    def renderizar_e_atualizar_display(self):
        self.mesas = self.carregar_mesas()
        self.controle_mesas_display.controls = self.renderizar_mesas()
        if self.page: self.page.update()

    def renderizar_mesas(self):
        mesas_cards = []
        for mesa in self.mesas:
            if mesa['status'] == 'LIVRE':
                cor_card = self.cores["verde"]
                cor_texto = ft.Colors.WHITE
                icone = ft.Icons.CHECK_CIRCLE_OUTLINE
                on_click = lambda e, m=mesa: self.abrir_nova_comanda_dialogo(e, m) 
                tooltip_texto = "Clique para abrir comanda"
            else: # OCUPADA
                cor_card = self.cores["primaria"]
                cor_texto = ft.Colors.WHITE
                icone = ft.Icons.FASTFOOD_OUTLINED
                on_click = lambda e, m=mesa: self.abrir_comanda_existente(e, m)
                tooltip_texto = "Clique para editar ou fechar comanda"

            card = StyledCard(
                content=ft.Container(
                    ft.Column([
                        ft.Icon(icone, color=cor_texto, size=30),
                        ft.Text(mesa['nome'], size=18, weight=ft.FontWeight.BOLD, color=cor_texto),
                        ft.Text(mesa['status'], size=14, color=ft.Colors.WHITE70),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    padding=15, alignment=ft.alignment.center,
                    on_click=on_click,
                    tooltip=tooltip_texto
                ),
                cores=self.cores,
                color=cor_card, # Sobrescreve a cor do card
                expand=True
            )
            mesas_cards.append(card)
        return mesas_cards

    # --- LÓGICA DE EDIÇÃO/FECHAMENTO ---
    def imprimir_pedido(self, e):
        comanda_data = self.dialog_editar_comanda.data
        itens = comanda_data['itens']
        if not itens:
            self.page.snack_bar = ft.SnackBar(ft.Text("A comanda está vazia!"), bgcolor=ft.Colors.ORANGE_500); self.page.snack_bar.open = True; self.page.update(); return
        sucesso, mensagem = gerar_pedido_cozinha(itens=itens, origem=self.nome_mesa_atual, destino=self.nome_mesa_atual)
        if sucesso: self.page.snack_bar = ft.SnackBar(ft.Text(f"Impressão OK! {mensagem}"), bgcolor=ft.Colors.BLUE_500)
        else: self.page.snack_bar = ft.SnackBar(ft.Text(f"Erro na Impressão: {mensagem}"), bgcolor=self.cores["primaria"])
        self.page.snack_bar.open = True; self.page.update()

    def atualizar_carrinho_edicao(self, comanda_itens):
        self.lista_itens_edicao.controls.clear()
        total_venda = 0
        for item in comanda_itens:
            subtotal = item['quantidade'] * item['preco_venda']
            total_venda += subtotal
            def remover_item_callback(e, item=item):
                comanda_itens.remove(item)
                self.salvar_e_recarregar_edicao(comanda_itens)
                
            self.lista_itens_edicao.controls.append(ft.ListTile(
                title=ft.Text(f"{item['quantidade']}x {item['nome']}", color=self.cores["texto_primario"]),
                trailing=ft.Text(f"R$ {subtotal:.2f}", color=self.cores["texto_secundario"]),
                leading=ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=self.cores["primaria"], tooltip="Remover Item", on_click=remover_item_callback)
            ))
        self.total_comanda_texto.value = f"Total: R$ {total_venda:.2f}"
        self.dialog_editar_comanda.data = {"itens": comanda_itens, "total": total_venda}
        if self.page: self.page.update()
        
    def salvar_e_recarregar_edicao(self, comanda_itens):
        total_atualizado = sum(item['quantidade'] * item['preco_venda'] for item in comanda_itens)
        conn, cursor = database.conectar()
        cursor.execute("UPDATE pedidos SET itens = ?, total = ? WHERE id = ?", (json.dumps(comanda_itens), total_atualizado, self.pedido_id_atual))
        conn.commit(); conn.close()
        self.atualizar_carrinho_edicao(comanda_itens)
        self.page.snack_bar = ft.SnackBar(ft.Text("Comanda atualizada!"), bgcolor=ft.Colors.BLUE_500); self.page.snack_bar.open = True; self.page.update()

    def adicionar_produto_edicao(self, e):
        produto_id = self.dropdown_produtos_edicao.value
        if not produto_id: return
        produto = self.produtos_disponiveis.get(int(produto_id))
        comanda_data = self.dialog_editar_comanda.data
        comanda_itens = comanda_data['itens']
        for item in comanda_itens:
            if item['id'] == int(produto_id):
                item['quantidade'] += 1; break
        else:
            comanda_itens.append({"id": int(produto_id), "nome": produto['nome'], "quantidade": 1, "preco_venda": produto['preco_venda']})
        self.salvar_e_recarregar_edicao(comanda_itens)

    def fechar_comanda(self, e):
        comanda_data = self.dialog_editar_comanda.data
        comanda_itens = comanda_data['itens']; total_final = comanda_data['total']
        if total_final <= 0:
            self.page.snack_bar = ft.SnackBar(ft.Text("A comanda está vazia!"), bgcolor=ft.Colors.ORANGE_500); self.page.snack_bar.open = True; self.page.update(); return
        self.page.close(self.dialog_editar_comanda)
        CaixaView.abrir_caixa_com_comanda(self.page, comanda_itens, self.pedido_id_atual, self.mesa_id_atual)

    def criar_dialogo_edicao(self):
        self.dropdown_produtos_edicao = ft.Dropdown(
            label="Adicionar Produto (x1)",
            options=[
                ft.dropdown.Option(str(id), text=f"{prod['nome']} (R$ {prod['preco_venda']:.2f})")
                for id, prod in self.produtos_disponiveis.items()
            ],
            expand=True,
            border_color=self.cores["texto_secundario"],
            focused_border_color=self.cores["primaria"],
        )
        
        return ft.AlertDialog(
            modal=True,
            title=SubTitle("Edição de Comanda", self.cores),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        BodyText("Adicionar Item:", self.cores),
                        ft.IconButton(icon=ft.Icons.PRINT_OUTLINED, icon_color=self.cores["texto_secundario"], on_click=self.imprimir_pedido, tooltip="Imprimir Pedido para Cozinha")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        self.dropdown_produtos_edicao,
                        ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=self.cores["verde"], on_click=self.adicionar_produto_edicao)
                    ]),
                    ft.Divider(height=10, color=ft.Colors.with_opacity(0.1, self.cores["texto_primario"])),
                    BodyText("Itens do Pedido:", self.cores),
                    self.lista_itens_edicao,
                    self.total_comanda_texto
                ], tight=True, scroll=ft.ScrollMode.ADAPTIVE, expand=True),
                height=500, width=400
            ),
            actions=[
                StyledTextButton("Cancelar", self.cores, on_click=lambda e: self.page.close(self.dialog_editar_comanda)),
                StyledButton("Fechar Comanda (Pagar)", self.cores, on_click=self.fechar_comanda)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

    def abrir_comanda_existente(self, e, mesa):
        pedido = self.carregar_pedido_aberto(mesa['id'])
        if not pedido:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Erro: Não há comanda aberta para {mesa['nome']}."), bgcolor=self.cores["primaria"]); self.page.snack_bar.open = True; self.page.update(); return
        self.mesa_id_atual = mesa['id']
        self.nome_mesa_atual = mesa['nome']
        self.pedido_id_atual = pedido['id']
        comanda_itens = json.loads(pedido['itens'])
        self.dialog_editar_comanda.title = SubTitle(f"Comanda: {mesa['nome']}", self.cores)
        self.atualizar_carrinho_edicao(comanda_itens)
        self.page.dialog = self.dialog_editar_comanda
        self.dialog_editar_comanda.open = True
        self.page.update()

    # --- LÓGICA DE ABRIR COMANDA ---
    def abrir_nova_comanda_dialogo(self, e, mesa):
        self.dialog_mesa_id.value = str(mesa['id'])
        self.txt_nome_comanda.value = f"Abrir Comanda: {mesa['nome']}"
        self.page.dialog = self.dialog_abrir_comanda
        self.dialog_abrir_comanda.open = True
        self.page.update()

    def criar_dialogo_abrir_comanda(self):
        self.dialog_mesa_id = ft.Text(visible=False)
        self.txt_nome_comanda = SubTitle("Abrir Comanda", self.cores)
        
        produtos_dropdown = ft.Dropdown(
            label="Adicionar 1º Produto", 
            options=[
                ft.dropdown.Option(str(id), text=f"{prod['nome']} (R$ {prod['preco_venda']:.2f})")
                for id, prod in self.produtos_disponiveis.items()
            ], 
            expand=True,
            border_color=self.cores["texto_secundario"],
            focused_border_color=self.cores["primaria"],
        )
        
        def fechar_dialogo(e): self.page.close(self.dialog_abrir_comanda)

        def abrir_comanda(e):
            mesa_id = int(self.dialog_mesa_id.value)
            produto_id = produtos_dropdown.value
            if not produto_id:
                self.page.snack_bar = ft.SnackBar(ft.Text("Selecione um produto para iniciar."), bgcolor=ft.Colors.ORANGE_500)
                self.page.snack_bar.open = True; self.page.update(); return
            
            produto = self.produtos_disponiveis.get(int(produto_id))
            itens_iniciais = [{"id": int(produto_id), "nome": produto['nome'], "quantidade": 1, "preco_venda": produto['preco_venda']}]
            total_inicial = produto['preco_venda']

            try:
                conn, cursor = database.conectar()
                cursor.execute(
                    "INSERT INTO pedidos (mesa_id, itens, total, data_abertura, status) VALUES (?, ?, ?, ?, 'ABERTO')",
                    (mesa_id, json.dumps(itens_iniciais), total_inicial, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                conn.commit()
                self.atualizar_status_mesa(mesa_id, 'OCUPADA')
                conn.close()
                fechar_dialogo(None)
                self.page.snack_bar = ft.SnackBar(ft.Text("Comanda aberta com sucesso!"), bgcolor=self.cores["verde"]); self.page.snack_bar.open = True; self.page.update()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao abrir comanda: {ex}"), bgcolor=self.cores["primaria"]); self.page.snack_bar.open = True; self.page.update()

        return ft.AlertDialog(
            modal=True,
            content=ft.Column([
                self.txt_nome_comanda, ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                self.dialog_mesa_id,
                BodyText("Selecione o primeiro produto do pedido:", self.cores),
                produtos_dropdown,
            ], tight=True, scroll=ft.ScrollMode.ADAPTIVE),
            actions=[
                StyledTextButton("Cancelar", self.cores, on_click=fechar_dialogo),
                StyledButton("Abrir Comanda", self.cores, on_click=abrir_comanda, bgcolor=self.cores["verde"]),
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

    # --- LAYOUT PRINCIPAL ---
    def build(self):
        return ft.Column(
            controls=[
                ft.Row([
                    Title("Controle de Comandas", self.cores),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        icon_color=self.cores["texto_secundario"],
                        on_click=lambda e: self.renderizar_e_atualizar_display(),
                        tooltip="Atualizar Status das Mesas"
                    )
                ]),
                BodyText("Clique em uma mesa para abrir ou editar a comanda.", self.cores, is_secondary=True),
                ft.Divider(height=10, color=ft.Colors.with_opacity(0.1, self.cores["texto_primario"])),
                self.controle_mesas_display,
            ],
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
            spacing=10
        )

# Função principal que o app.py chama
def ComandasViewFunction(page: ft.Page, cores):
    view = ComandasView(page, cores)
    return view.build()