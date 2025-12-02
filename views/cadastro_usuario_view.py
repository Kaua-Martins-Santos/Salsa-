# restaurante_sistema/views/cadastro_usuario_view.py
import flet as ft
import database
import bcrypt
from utils.components import (
    StyledTextField, StyledButton, StyledCard, 
    Title, SubTitle, StyledDataTable
)

def CadastroUsuarioView(page: ft.Page, cores):

    # --- WIDGETS DO FORMULÁRIO ---
    txt_nome = StyledTextField(label="Nome Completo", cores=cores)
    txt_login = StyledTextField(label="Login/Usuário (Ex: 'caixa1')", cores=cores)
    txt_senha = StyledTextField(label="Senha Inicial", cores=cores, is_password=True)
    dd_permissao = ft.Dropdown(
        label="Nível de Permissão",
        options=[
            ft.dropdown.Option("CAIXA", text="Caixa (Apenas Vendas/Comandas)"),
            ft.dropdown.Option("GERENTE", text="Gerente (Acesso Total)"),
        ],
        value="CAIXA",
        border_radius=10,
        border_color=cores["texto_secundario"],
        focused_border_color=cores["primaria"],
        color=cores["texto_primario"]
    )

    tabela_usuarios = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Nome")),
            ft.DataColumn(ft.Text("Login")),
            ft.DataColumn(ft.Text("Permissão")),
            ft.DataColumn(ft.Text("Ações")),
        ],
        rows=[]
    )
    
    def carregar_usuarios():
        conn, cursor = database.conectar()
        cursor.execute("SELECT id, nome, login, permissao FROM usuarios ORDER BY nome")
        usuarios = cursor.fetchall()
        conn.close()
        
        tabela_usuarios.rows.clear()
        for u in usuarios:
            def criar_callback_excluir(usuario):
                return lambda e: excluir_usuario(usuario)

            tabela_usuarios.rows.append(ft.DataRow(
                color=cores["surface"],
                cells=[
                    ft.DataCell(ft.Text(u['id'], color=cores["texto_secundario"])),
                    ft.DataCell(ft.Text(u['nome'], color=cores["texto_primario"])),
                    ft.DataCell(ft.Text(u['login'], color=cores["texto_primario"])),
                    ft.DataCell(ft.Text(u['permissao'], color=cores["texto_primario"])),
                    ft.DataCell(ft.Row([
                        ft.IconButton(icon=ft.Icons.DELETE_SWEEP_OUTLINED, icon_color=cores["primaria"], on_click=criar_callback_excluir(u), tooltip="Excluir Usuário"),
                    ])),
                ]
            ))
        StyledDataTable(tabela_usuarios, cores)
        page.update()

    def limpar_formulario():
        txt_nome.value, txt_login.value, txt_senha.value = "", "", ""
        dd_permissao.value = "CAIXA"
        page.update()

    def salvar_usuario(e):
        nome = txt_nome.value
        login = txt_login.value
        senha_digitada = txt_senha.value
        permissao = dd_permissao.value

        if not nome or not login or not senha_digitada or not permissao:
            page.snack_bar = ft.SnackBar(ft.Text("Todos os campos são obrigatórios!"), bgcolor=ft.Colors.ORANGE_500)
            page.snack_bar.open = True; page.update(); return
            
        try:
            conn, cursor = database.conectar()
            senha_bytes = senha_digitada.encode('utf-8')
            sal = bcrypt.gensalt()
            hash_senha = bcrypt.hashpw(senha_bytes, sal)
            hash_str = hash_senha.decode('utf-8')
            
            cursor.execute("INSERT INTO usuarios (nome, login, senha, permissao) VALUES (?, ?, ?, ?)", 
                           (nome, login, hash_str, permissao))
            
            conn.commit(); conn.close()
            page.snack_bar = ft.SnackBar(ft.Text(f"Usuário '{nome}' cadastrado!"), bgcolor=cores["verde"])
            page.snack_bar.open = True
            limpar_formulario(); carregar_usuarios()
        except Exception as ex:
            msg = "Erro: O login informado já está em uso." if "UNIQUE constraint failed" in str(ex) else f"Erro ao cadastrar: {ex}"
            page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=cores["primaria"])
            page.snack_bar.open = True; page.update()

    def excluir_usuario(usuario):
        if usuario['permissao'] == 'GERENTE' and usuario['login'] == 'admin':
            page.snack_bar = ft.SnackBar(ft.Text("Não é possível excluir o administrador padrão."), bgcolor=cores["primaria"])
            page.snack_bar.open = True; page.update(); return

        conn, cursor = database.conectar()
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario['id'],))
        conn.commit(); conn.close()
        page.snack_bar = ft.SnackBar(ft.Text(f"Usuário '{usuario['nome']}' removido!"), bgcolor=cores["primaria"])
        page.snack_bar.open = True
        carregar_usuarios()

    btn_salvar = StyledButton(text="Cadastrar Novo Usuário", cores=cores, on_click=salvar_usuario, icon=ft.Icons.PERSON_ADD_ALT_1, expand=True)

    carregar_usuarios()

    coluna_cadastro = StyledCard(
        content=ft.Container(
            content=ft.Column([
                SubTitle("Cadastrar Novo Usuário", cores),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                txt_nome,
                txt_login,
                txt_senha,
                dd_permissao,
                ft.Container(height=20),
                ft.Row(controls=[btn_salvar], alignment=ft.MainAxisAlignment.CENTER)
            ], scroll=ft.ScrollMode.ADAPTIVE),
        ),
        cores=cores,
        expand=2
    )
    
    coluna_lista = ft.Column(
        controls=[
            Title("Usuários Cadastrados", cores),
            ft.Container(
                content=ft.ListView(controls=[tabela_usuarios]),
                expand=True,
                border=ft.border.all(1, ft.Colors.with_opacity(0.1, cores["texto_primario"])),
                border_radius=10
            )
        ],
        expand=3,
        spacing=20
    )

    return ft.Row(
        controls=[coluna_cadastro, ft.VerticalDivider(width=1, color=ft.Colors.with_opacity(0.1, cores["texto_primario"])), coluna_lista],
        vertical_alignment=ft.CrossAxisAlignment.START, expand=True, spacing=25
    )