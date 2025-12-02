# restaurante_sistema/views/configuracoes_view.py
import flet as ft
import database
from utils.components import Title, StyledTextField, StyledButton, BodyText, StyledTextButton

def ConfiguracoesView(page: ft.Page, cores):

    # --- DIÁLOGO DE CONFIRMAÇÃO ---
    dlg_confirmacao = ft.AlertDialog(
        modal=True,
        title=ft.Text("Sucesso!"),
        content=ft.Text("As configurações foram salvas."),
        actions=[
            StyledTextButton("OK", cores, on_click=lambda e: page.close(dlg_confirmacao)),
        ],
    )
    page.overlay.append(dlg_confirmacao)

    # --- WIDGETS DA TELA ---
    txt_nome_comerciante = StyledTextField(label="Nome do Restaurante / Comerciante", cores=cores)
    txt_chave_pix = StyledTextField(label="Sua Chave PIX (celular, e-mail, CPF/CNPJ, etc.)", cores=cores)
    txt_cidade = StyledTextField(label="Cidade (Ex: Sao Paulo)", cores=cores)

    def carregar_configuracoes():
        try:
            conn, cursor = database.conectar()
            cursor.execute("CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY CHECK (id = 1), nome_comerciante TEXT NOT NULL, chave_pix TEXT NOT NULL, cidade TEXT NOT NULL)")
            cursor.execute("SELECT * FROM configuracoes WHERE id = 1")
            configs = cursor.fetchone()
            conn.close()
            if configs:
                txt_nome_comerciante.value = configs['nome_comerciante']
                txt_chave_pix.value = configs['chave_pix']
                txt_cidade.value = configs['cidade']
                page.update()
        except Exception as ex:
            print(f"Erro ao carregar configurações: {ex}")

    def salvar_configuracoes(e):
        try:
            nome = txt_nome_comerciante.value
            chave = txt_chave_pix.value
            cidade = txt_cidade.value

            if not nome or not chave or not cidade:
                page.snack_bar = ft.SnackBar(ft.Text("Todos os campos são obrigatórios!"), bgcolor=ft.Colors.ORANGE_500)
                page.snack_bar.open = True; page.update(); return

            conn, cursor = database.conectar()
            cursor.execute("CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY CHECK (id = 1), nome_comerciante TEXT NOT NULL, chave_pix TEXT NOT NULL, cidade TEXT NOT NULL)")
            cursor.execute("INSERT OR REPLACE INTO configuracoes (id, nome_comerciante, chave_pix, cidade) VALUES (1, ?, ?, ?)", (nome, chave, cidade))
            conn.commit(); conn.close()
            
            page.dialog = dlg_confirmacao
            dlg_confirmacao.open = True
            page.update()

        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao salvar: {ex}"), bgcolor=cores["primaria"])
            page.snack_bar.open = True; page.update()

    carregar_configuracoes()

    # CORREÇÃO: Removido o argumento 'constraints' que estava causando o erro
    return ft.Container(
        content=ft.Column(
            controls=[
                Title("Configurações", cores),
                BodyText("Preencha os dados abaixo para a geração correta do QR Code PIX.", cores, is_secondary=True),
                ft.Divider(height=10, color=ft.Colors.with_opacity(0.1, cores["texto_primario"])),
                txt_nome_comerciante,
                txt_chave_pix,
                txt_cidade,
                ft.Container(height=20),
                StyledButton(
                    text="Salvar Configurações",
                    cores=cores,
                    icon=ft.Icons.SAVE,
                    on_click=salvar_configuracoes,
                )
            ],
            spacing=20, 
            expand=True,
        ),
        # constraints=ft.BoxConstraints(max_width=800), # LINHA REMOVIDA
        expand=True,
        alignment=ft.alignment.top_left
    )