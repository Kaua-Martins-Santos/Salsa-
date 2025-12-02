# restaurante_sistema/views/caixa_view.py
import flet as ft
import database
from datetime import datetime
import json
import base64
from io import BytesIO
import unicodedata
import qrcode
import traceback
from utils.components import (
    StyledTextField, StyledButton, StyledTextButton, 
    StyledCard, Title, SubTitle, StyledDataTable, BodyText
)

# A classe QuantityControl não precisa ser "Styled" pois é interna
class QuantityControl(ft.Row):
    def __init__(self, on_add_click, cores):
        super().__init__()
        self.on_add_click = on_add_click
        self.txt_qtd = ft.TextField(
            value="1", width=50, text_align=ft.TextAlign.CENTER, 
            input_filter=ft.NumbersOnlyInputFilter(),
            border_color=cores["texto_secundario"],
            text_style=ft.TextStyle(color=cores["texto_primario"])
        )
        self.alignment = ft.MainAxisAlignment.CENTER
        self.controls = [
            ft.IconButton(ft.Icons.REMOVE, on_click=self.minus_click, icon_color=cores["primaria"]), 
            self.txt_qtd, 
            ft.IconButton(ft.Icons.ADD, on_click=self.plus_click, icon_color=cores["verde"]),
            StyledButton("Add", cores, icon=ft.Icons.ADD_SHOPPING_CART, on_click=self.add_click, height=40)
        ]
    def minus_click(self, e): self.txt_qtd.value = str(max(1, int(self.txt_qtd.value or "1") - 1)); self.update()
    def plus_click(self, e): self.txt_qtd.value = str(int(self.txt_qtd.value or "0") + 1); self.update()
    def add_click(self, e): self.on_add_click(int(self.txt_qtd.value))


class CaixaView:

    # (Lógica _gerar_pix_payload não muda)
    @staticmethod
    def _gerar_pix_payload(chave_pix, nome_comerciante, cidade, valor, txid="***"):
        def formatar_campo(id_campo, valor_campo):
            tamanho = str(len(valor_campo)).zfill(2)
            return f"{id_campo}{tamanho}{valor_campo}"
        nome_sanitizado = "".join(
            c for c in unicodedata.normalize('NFD', nome_comerciante)
            if unicodedata.category(c) != 'Mn'
        ).upper()
        cidade_sanitizada = "".join(
            c for c in unicodedata.normalize('NFD', cidade)
            if unicodedata.category(c) != 'Mn'
        ).upper()
        nome_final = "".join(c for c in nome_sanitizado if c.isalnum() or c == ' ')[:25].strip()
        cidade_final = "".join(c for c in cidade_sanitizada if c.isalnum() or c == ' ')[:15].strip()
        valor_formatado = f"{valor:.2f}"
        payload = ""
        payload += formatar_campo("00", "01")
        gui = formatar_campo("00", "br.gov.bcb.pix")
        chave = formatar_campo("01", chave_pix)
        merchant_account_info = gui + chave
        payload += formatar_campo("26", merchant_account_info)
        payload += formatar_campo("52", "0000")
        payload += formatar_campo("53", "986")
        payload += formatar_campo("54", valor_formatado)
        payload += formatar_campo("58", "BR")
        payload += formatar_campo("59", nome_final)
        payload += formatar_campo("60", cidade_final)
        txid_campo = formatar_campo("05", txid)
        payload += formatar_campo("62", txid_campo)
        payload_com_crc_placeholder = payload + "6304"
        polinomio = 0x1021
        resultado = 0xFFFF
        for byte in payload_com_crc_placeholder.encode('utf-8'):
            resultado ^= (byte << 8)
            for _ in range(8):
                if (resultado & 0x8000):
                    resultado = (resultado << 1) ^ polinomio
                else:
                    resultado <<= 1
        crc16 = hex(resultado & 0xFFFF)[2:].upper().zfill(4)
        return payload_com_crc_placeholder + crc16
    
    def __init__(self, page: ft.Page, cores):
        self.page = page
        self.cores = cores # Armazena as cores
        self.carrinho_de_compras = []
        self.pedido_id_comanda = None
        self.mesa_id_comanda = None
        self.tabela_produtos = ft.DataTable(columns=[
            ft.DataColumn(ft.Text("Produto")), 
            ft.DataColumn(ft.Text("Preço")), 
            ft.DataColumn(ft.Text("Ações"))
        ], rows=[])
        self.lista_itens_carrinho = ft.ListView(expand=True, spacing=10)
        self.total_venda_texto = ft.Text("Total: R$ 0.00", size=24, weight=ft.FontWeight.BOLD, color=cores["texto_primario"])
        self.saldo_caixa_texto = ft.Text("Saldo do Caixa: R$ 0.00", size=18, color=cores["texto_secundario"])
        
        self.search_field_venda = StyledTextField(
            label="Buscar produto...", 
            cores=cores, 
            on_change=self.buscar_produtos_venda, 
            icon_name=ft.Icons.SEARCH # <--- CORREÇÃO AQUI
        )
        
        # Widgets do PIX
        self.nome_comerciante_pix = ft.Text(weight=ft.FontWeight.BOLD, size=18, color=cores["texto_primario"])
        self.chave_pix_info = ft.Text(weight=ft.FontWeight.BOLD, size=16, color=cores["texto_primario"])
        self.qr_code_pix = ft.Image(width=250, height=250)
        self.copia_e_cola_pix = StyledTextField(label="PIX Copia e Cola", cores=cores, read_only=True, multiline=True)
        
        self.dialog_pagamento = ft.AlertDialog(modal=True, title=ft.Text("Selecione o Método de Pagamento"), actions=[], actions_alignment=ft.MainAxisAlignment.SPACE_EVENLY)
        
        # Campos de Saída/Resgate
        self.txt_valor_saida = StyledTextField(label="Valor da Saída (R$)", prefix_text="R$", cores=cores)
        self.txt_descricao_saida = StyledTextField(label="Descrição da Despesa", cores=cores)
        self.txt_valor_resgate = StyledTextField(label="Valor a ser Retirado (R$)", prefix_text="R$", cores=cores)

        # Diálogos
        self.dialog_pix = self._criar_dialogo_pix()
        self.dialog_saida_caixa = self._criar_dialogo_saida()
        self.dialog_resgate_caixa = self._criar_dialogo_resgate()
        
        self.relatorio_vendas = self._criar_relatorio_vendas_widgets()
        
        self.page.overlay.extend([self.dialog_pix, self.dialog_pagamento, self.dialog_saida_caixa, self.dialog_resgate_caixa])
        self.carregar_produtos_disponiveis()
        self.calcular_e_atualizar_saldo_caixa()
        self.atualizar_relatorio_vendas()
        
        comanda_data_pending = getattr(self.page, 'comanda_data_pending', None)
        if comanda_data_pending:
            self.carrinho_de_compras = comanda_data_pending['itens']
            self.pedido_id_comanda = comanda_data_pending['pedido_id']
            self.mesa_id_comanda = comanda_data_pending['mesa_id']
            delattr(self.page, 'comanda_data_pending')
            self.atualizar_carrinho_display()
            self.abrir_dialog_pagamento(None)

    def _criar_dialogo_pix(self):
        def finalizar_venda_pix(e):
            self.fechar_dialogo(self.dialog_pix)
            self.executar_finalizacao(e, "PIX")

        return ft.AlertDialog(
            modal=True, 
            title=ft.Text("Pagamento via PIX"), 
            content=ft.Column([
                ft.Text("Chave PIX:"), self.chave_pix_info, ft.Divider(), 
                self.qr_code_pix, 
                ft.Text("Pague para:", size=12), self.nome_comerciante_pix, 
                self.copia_e_cola_pix
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True, scroll=ft.ScrollMode.ADAPTIVE), 
            actions=[
                StyledTextButton("Cancelar", self.cores, on_click=lambda e: self.fechar_dialogo(self.dialog_pix)), 
                StyledButton("Pagamento Confirmado", self.cores, on_click=finalizar_venda_pix, bgcolor=self.cores["verde"])
            ], 
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

    def _criar_dialogo_saida(self):
        return ft.AlertDialog(
            modal=True, 
            title=ft.Text("Registrar Saída de Caixa"), 
            content=ft.Column([self.txt_valor_saida, self.txt_descricao_saida]), 
            actions=[
                StyledTextButton("Cancelar", self.cores, on_click=lambda e: self.fechar_dialogo(self.dialog_saida_caixa)), 
                StyledButton("Confirmar", self.cores, on_click=self.on_confirmar_saida_click)
            ], 
            actions_alignment=ft.MainAxisAlignment.END
        )

    def _criar_dialogo_resgate(self):
        return ft.AlertDialog(
            modal=True, 
            title=ft.Text("Resgate/Sangria de Caixa"), 
            content=ft.Column([ft.Text("Este valor será registrado como uma retirada do caixa."), self.txt_valor_resgate]), 
            actions=[
                StyledTextButton("Cancelar", self.cores, on_click=lambda e: self.fechar_dialogo(self.dialog_resgate_caixa)), 
                StyledButton("Confirmar", self.cores, on_click=self.on_confirmar_resgate_click)
            ], 
            actions_alignment=ft.MainAxisAlignment.END
        )

    def fechar_dialogo(self, dialogo):
        dialogo.open = False; self.page.update()

    def _criar_relatorio_vendas_widgets(self):
        self.vendas_debito_texto = ft.Text("R$ 0.00", size=18, weight=ft.FontWeight.BOLD, color=self.cores["texto_primario"])
        self.vendas_credito_texto = ft.Text("R$ 0.00", size=18, weight=ft.FontWeight.BOLD, color=self.cores["texto_primario"])
        self.vendas_pix_texto = ft.Text("R$ 0.00", size=18, weight=ft.FontWeight.BOLD, color=self.cores["texto_primario"])
        
        def criar_linha(titulo, valor_widget, icone, cor_icone):
            return ft.Row([
                ft.Icon(icone, color=cor_icone), 
                BodyText(titulo, self.cores), 
                ft.Container(expand=True), 
                valor_widget
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        return StyledCard(
            content=ft.Container(content=ft.Column([
                SubTitle("Vendas do Dia", self.cores), 
                ft.Divider(height=10, color=ft.Colors.with_opacity(0.1, self.cores["texto_primario"])), 
                criar_linha("Débito", self.vendas_debito_texto, ft.Icons.CREDIT_CARD, ft.Colors.BLUE_500), 
                criar_linha("Crédito", self.vendas_credito_texto, ft.Icons.CREDIT_CARD, ft.Colors.PURPLE_500), 
                criar_linha("PIX", self.vendas_pix_texto, ft.Icons.QR_CODE, ft.Colors.TEAL_500)
            ], spacing=10)),
            cores=self.cores,
            padding=15
        )

    def mostrar_notificacao(self, mensagem, cor_bg):
        self.page.snack_bar = ft.SnackBar(ft.Text(mensagem), bgcolor=cor_bg)
        self.page.snack_bar.open = True; self.page.update()
    
    def _validar_e_obter_valor(self, campo_valor: ft.TextField) -> float | None:
        valor_str = campo_valor.value.replace(",", ".").strip()
        if not valor_str: self.mostrar_notificacao("O campo de valor não pode estar vazio.", cor_bg=ft.Colors.ORANGE_500); return None
        try:
            valor = float(valor_str)
            if valor > 0: return valor
            else: self.mostrar_notificacao("O valor deve ser positivo!", cor_bg=self.cores["primaria"]); return None
        except ValueError: self.mostrar_notificacao("Valor inválido. Use um formato numérico.", cor_bg=self.cores["primaria"]); return None

    def _registrar_transacao_saida_db(self, valor: float, descricao: str) -> bool:
        try:
            conn, cursor = database.conectar(); cursor.execute("INSERT INTO transacoes (data_venda, itens, total, metodo_pagamento, tipo, descricao) VALUES (?, ?, ?, ?, ?, ?)", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '[]', valor, 'SAIDA', 'saida', descricao)); conn.commit(); conn.close(); return True
        except Exception as ex: self.mostrar_notificacao(f"Erro no banco de dados: {ex}", cor_bg=self.cores["primaria"]); return False

    def on_confirmar_saida_click(self, e):
        valor = self._validar_e_obter_valor(self.txt_valor_saida); descricao = self.txt_descricao_saida.value.strip()
        if valor is None: return
        if not descricao: self.mostrar_notificacao("A descrição é obrigatória.", cor_bg=ft.Colors.ORANGE_500); return
        if self._registrar_transacao_saida_db(valor, descricao): 
            self.mostrar_notificacao(f"Saída de R$ {valor:.2f} registrada!", cor_bg=self.cores["verde"])
            self.calcular_e_atualizar_saldo_caixa(); self.fechar_dialogo(self.dialog_saida_caixa)
            self.txt_valor_saida.value = ""; self.txt_descricao_saida.value = ""; self.page.update()

    def on_confirmar_resgate_click(self, e):
        valor = self._validar_e_obter_valor(self.txt_valor_resgate)
        if valor is None: return
        if self._registrar_transacao_saida_db(valor, 'Resgate/Sangria de Caixa'): 
            self.mostrar_notificacao(f"Resgate de R$ {valor:.2f} registrado!", cor_bg=self.cores["verde"])
            self.calcular_e_atualizar_saldo_caixa(); self.fechar_dialogo(self.dialog_resgate_caixa)
            self.txt_valor_resgate.value = ""; self.page.update()

    @staticmethod
    def abrir_caixa_com_comanda(page: ft.Page, itens: list, pedido_id: int, mesa_id: int):
        page.comanda_data_pending = {'itens': itens, 'pedido_id': pedido_id, 'mesa_id': mesa_id}; page.go("/caixa")

    def atualizar_relatorio_vendas(self):
        conn, cursor = database.conectar(); cursor.execute("SELECT metodo_pagamento, SUM(total) as soma FROM transacoes WHERE tipo = 'entrada' AND date(data_venda) = date('now', 'localtime') GROUP BY metodo_pagamento"); vendas_dia = {row['metodo_pagamento']: row['soma'] for row in cursor.fetchall()}; conn.close()
        self.vendas_debito_texto.value = f"R$ {vendas_dia.get('Débito', 0.00):.2f}"; self.vendas_credito_texto.value = f"R$ {vendas_dia.get('Crédito', 0.00):.2f}"; self.vendas_pix_texto.value = f"R$ {vendas_dia.get('PIX', 0.00):.2f}"
        if self.page: self.page.update()

    def calcular_e_atualizar_saldo_caixa(self):
        conn, cursor = database.conectar(); cursor.execute("SELECT SUM(CASE WHEN tipo = 'entrada' THEN total ELSE -total END) as saldo FROM transacoes"); resultado = cursor.fetchone(); conn.close(); saldo = resultado['saldo'] if resultado and resultado['saldo'] is not None else 0; self.saldo_caixa_texto.value = f"Saldo do Caixa: R$ {saldo:.2f}"
        if self.page: self.page.update()

    def atualizar_carrinho_display(self):
        self.lista_itens_carrinho.controls.clear(); total_venda = 0
        for item in self.carrinho_de_compras:
            subtotal = item['quantidade'] * item['preco_venda']; total_venda += subtotal
            self.lista_itens_carrinho.controls.append(
                ft.ListTile(
                    title=ft.Text(f"{item['quantidade']}x {item['nome']}", color=self.cores["texto_primario"]), 
                    leading=ft.IconButton(
                        icon=ft.Icons.REMOVE_CIRCLE_OUTLINE, 
                        icon_color=self.cores["primaria"], 
                        tooltip="Remover Item", 
                        on_click=lambda e, item=item: self.remover_do_carrinho(item)
                    ), 
                    trailing=ft.Text(f"R$ {subtotal:.2f}", color=self.cores["texto_secundario"])
                )
            )
        self.total_venda_texto.value = f"Total: R$ {total_venda:.2f}"
        if self.page: self.page.update()

    def remover_do_carrinho(self, item_para_remover):
        self.carrinho_de_compras.remove(item_para_remover); self.atualizar_carrinho_display()

    def adicionar_ao_carrinho(self, produto, quantidade=1):
        for item in self.carrinho_de_compras:
            if item['id'] == produto['id']: item['quantidade'] += quantidade; break
        else: self.carrinho_de_compras.append({"id": produto['id'], "nome": produto['nome'], "quantidade": quantidade, "preco_venda": produto['valor_compra'] * 2})
        self.atualizar_carrinho_display()

    def carregar_produtos_disponiveis(self, termo_busca=None):
        conn, cursor = database.conectar(); query = "SELECT * FROM estoque WHERE quantidade > 0 AND nome LIKE ? ORDER BY nome" if termo_busca else "SELECT * FROM estoque WHERE quantidade > 0 ORDER BY nome"; params = (f'%{termo_busca}%',) if termo_busca else (); cursor.execute(query, params); produtos = cursor.fetchall(); conn.close()
        
        StyledDataTable(self.tabela_produtos, self.cores) # Aplica o estilo no cabeçalho
        self.tabela_produtos.rows.clear()
        
        for p in produtos:
            preco_venda = p['valor_compra'] * 2
            def criar_callback(produto): return lambda quantidade: self.adicionar_ao_carrinho(produto, quantidade)
            self.tabela_produtos.rows.append(
                ft.DataRow(
                    color=self.cores["surface"],
                    cells=[
                        ft.DataCell(ft.Text(p['nome'], weight=ft.FontWeight.BOLD, color=self.cores["texto_primario"])), 
                        ft.DataCell(ft.Text(f"R$ {preco_venda:.2f}", color=self.cores["texto_secundario"])), 
                        ft.DataCell(QuantityControl(on_add_click=criar_callback(p), cores=self.cores))
                    ]
                )
            )
        if self.page: self.page.update()

    def executar_finalizacao(self, e, metodo_pagamento):
        total_final = sum(item['quantidade'] * item['preco_venda'] for item in self.carrinho_de_compras)
        try:
            conn, cursor = database.conectar()
            for item in self.carrinho_de_compras: cursor.execute("UPDATE estoque SET quantidade = quantidade - ? WHERE id = ?", (item['quantidade'], item['id']))
            itens_json = json.dumps(self.carrinho_de_compras)
            if self.pedido_id_comanda and self.mesa_id_comanda: cursor.execute("UPDATE pedidos SET status = 'PAGO', data_fechamento = ? WHERE id = ?", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.pedido_id_comanda)); cursor.execute("UPDATE mesas SET status = 'LIVRE' WHERE id = ?", (self.mesa_id_comanda,))
            cursor.execute("INSERT INTO transacoes (data_venda, itens, total, metodo_pagamento, tipo) VALUES (?, ?, ?, ?, 'entrada')", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), itens_json, total_final, metodo_pagamento)); conn.commit(); conn.close()
            self.carrinho_de_compras.clear(); self.pedido_id_comanda = None; self.mesa_id_comanda = None
            self.atualizar_carrinho_display(); self.carregar_produtos_disponiveis(); self.calcular_e_atualizar_saldo_caixa(); self.atualizar_relatorio_vendas(); self.mostrar_notificacao(f"Venda finalizada com {metodo_pagamento}!", cor_bg=self.cores["verde"])
        except Exception as ex: self.mostrar_notificacao(f"Erro ao finalizar venda: {ex}", cor_bg=self.cores["primaria"])

    def pagar_com_pix(self, e):
        total_final = sum(item['quantidade'] * item['preco_venda'] for item in self.carrinho_de_compras)
        if total_final <= 0: return
        conn, cursor = database.conectar()
        cursor.execute("SELECT * FROM configuracoes WHERE id = 1")
        configs = cursor.fetchone(); conn.close()
        if not configs or not configs['chave_pix']:
            self.mostrar_notificacao("ERRO: Configure a Chave PIX na tela de Configurações!", cor_bg=self.cores["primaria"]); return
        self.page.close(self.dialog_pagamento)
        try:
            txid_unico = ""
            if self.pedido_id_comanda: txid_unico = f"PED{self.pedido_id_comanda}"
            else: txid_unico = f"CAIXA{datetime.now().strftime('%H%M%S')}"
            txid_unico_formatado = "".join(c for c in txid_unico if c.isalnum())[:25]
            if not txid_unico_formatado: txid_unico_formatado = "VENDA"
            
            print(f"\n--- INICIANDO DIAGNÓSTICO PIX (TXID: {txid_unico_formatado}) ---")
            print(f"1. DADOS BRUTOS DO BANCO: NOME: {configs['nome_comerciante']}, CIDADE: {configs['cidade']}, CHAVE: {configs['chave_pix']}, VALOR: {total_final:.2f}")
            
            br_code_gerado = self._gerar_pix_payload(
                chave_pix=configs['chave_pix'], nome_comerciante=configs['nome_comerciante'],
                cidade=configs['cidade'], valor=total_final, txid=txid_unico_formatado
            )
            print(f"2. PAYLOAD (COPIA E COLA) GERADO: {br_code_gerado}")
            print("--- DIAGNÓSTICO FINALIZADO ---\n")

            self.copia_e_cola_pix.value = br_code_gerado
            self.nome_comerciante_pix.value = configs['nome_comerciante']
            self.chave_pix_info.value = configs['chave_pix']
            img = qrcode.make(br_code_gerado); buf = BytesIO(); img.save(buf, format="PNG")
            base64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            self.qr_code_pix.src_base64 = base64_str
            self.page.dialog = self.dialog_pix; self.dialog_pix.open = True; self.page.update()
        except Exception as ex:
            print("\n!!!!!!!!!! OCORREU UM ERRO GRAVE AO GERAR O PIX !!!!!!!!!!"); traceback.print_exc(); print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            self.mostrar_notificacao(f"Erro crítico ao gerar PIX. Verifique o terminal.", cor_bg=self.cores["primaria"]); self.page.update()

    def fechar_dialogo_e_finalizar(self, e, metodo):
        self.page.close(self.dialog_pagamento); self.executar_finalizacao(e, metodo)

    def abrir_dialog_pagamento(self, e):
        if not self.carrinho_de_compras: self.mostrar_notificacao("O carrinho está vazio!", cor_bg=ft.Colors.ORANGE_500); return
        self.page.dialog = self.dialog_pagamento
        self.dialog_pagamento.actions = [
            StyledTextButton("Débito", self.cores, icon=ft.Icons.CREDIT_CARD, on_click=lambda e: self.fechar_dialogo_e_finalizar(e, "Débito")), 
            StyledTextButton("Crédito", self.cores, icon=ft.Icons.CREDIT_CARD, on_click=lambda e: self.fechar_dialogo_e_finalizar(e, "Crédito")), 
            StyledTextButton("PIX", self.cores, icon=ft.Icons.QR_CODE, on_click=self.pagar_com_pix)
        ]
        self.dialog_pagamento.open = True; self.page.update()

    def abrir_dialog_saida_caixa(self, e):
        self.txt_valor_saida.value = ""; self.txt_descricao_saida.value = ""; self.page.dialog = self.dialog_saida_caixa; self.dialog_saida_caixa.open = True; self.page.update()
    
    def abrir_dialog_resgate_caixa(self, e):
        self.txt_valor_resgate.value = ""; self.page.dialog = self.dialog_resgate_caixa; self.dialog_resgate_caixa.open = True; self.page.update()
    
    def buscar_produtos_venda(self, e):
        self.carregar_produtos_disponiveis(termo_busca=e.control.value)

    def build(self):
        coluna_menu = ft.Column(
            controls=[
                Title("Menu", self.cores), 
                self.search_field_venda, 
                ft.Container(
                    content=ft.ListView(controls=[self.tabela_produtos]),
                    expand=True,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.1, self.cores["texto_primario"])),
                    border_radius=10
                )
            ], 
            expand=3,
            spacing=20
        )
        
        coluna_carrinho = ft.Column(
            controls=[
                Title("Caixa", self.cores),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                ft.Container(
                    content=self.lista_itens_carrinho,
                    expand=True,
                    border=ft.border.all(1, ft.Colors.with_opacity(0.1, self.cores["texto_primario"])),
                    border_radius=10,
                    padding=5
                ),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                self.saldo_caixa_texto,
                self.total_venda_texto,
                ft.Container(height=10),
                StyledButton(
                    "Finalizar Venda", self.cores, 
                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE, 
                    on_click=self.abrir_dialog_pagamento, 
                    bgcolor=self.cores["verde"], 
                    expand=True
                ),
                ft.Container(height=20),
                StyledCard(
                    content=ft.Container(
                        content=ft.Column([
                            SubTitle("Gestão de Caixa", self.cores),
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.REMOVE_CIRCLE, color=self.cores["primaria"]),
                                title=BodyText("Registrar Saída (Despesa)", self.cores),
                                on_click=self.abrir_dialog_saida_caixa
                            ),
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.ATTACH_MONEY, color=ft.Colors.AMBER_500),
                                title=BodyText("Resgate / Sangria", self.cores),
                                on_click=self.abrir_dialog_resgate_caixa
                            ),
                        ]),
                        padding=ft.padding.symmetric(vertical=10)
                    ),
                    cores=self.cores,
                    padding=10
                ),
                self.relatorio_vendas,
            ],
            expand=2,
            spacing=10
        )
        
        return ft.Row(
            controls=[coluna_menu, ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.1, self.cores["texto_primario"])), coluna_carrinho], 
            vertical_alignment=ft.CrossAxisAlignment.START, 
            expand=True,
            spacing=25
        )

# Função principal que o app.py chama
def CaixaViewFunction(page: ft.Page, cores):
    view = CaixaView(page, cores)
    return view.build()