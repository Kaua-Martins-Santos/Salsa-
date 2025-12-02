# restaurante_sistema/views/login_view.py
import flet as ft
import database
import bcrypt
# Importa os componentes corretos da nossa biblioteca
from utils.components import StyledTextField, StyledButton

def LoginView(page: ft.Page, on_login_success, CORES):

    # Pega as cores corretas do tema atual
    cores = CORES[page.theme_mode.value.lower()]

    # --- Lógica de Login (Vem antes dos widgets que a usam) ---
    def autenticar(e):
        login = txt_login.value
        senha_digitada = txt_senha.value
        
        if not login or not senha_digitada:
            page.snack_bar = ft.SnackBar(
                ft.Text("Preencha login e senha."), 
                bgcolor=ft.Colors.ORANGE_500
            )
            page.snack_bar.open = True; page.update(); return
            
        conn, cursor = database.conectar()
        cursor.execute("SELECT * FROM usuarios WHERE login = ?", (login,))
        usuario = cursor.fetchone()
        
        usuario_valido = False
        if usuario:
            hash_salvo_str = usuario['senha']
            hash_salvo_bytes = hash_salvo_str.encode('utf-8')
            senha_digitada_bytes = senha_digitada.encode('utf-8')
            
            if bcrypt.checkpw(senha_digitada_bytes, hash_salvo_bytes):
                usuario_valido = True
                
        conn.close()
        
        if usuario_valido:
            on_login_success(dict(usuario))
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("Login ou senha inválidos."), 
                bgcolor=CORES["light"]["primaria"] # Vermelho Salsa Fixo
            )
            page.snack_bar.open = True; page.update()

    # --- Widgets Estilizados (Agora usando a biblioteca) ---
    
    txt_login = StyledTextField(
        label="Login", 
        cores=cores, 
        icon_name=ft.Icons.PERSON_OUTLINE
    )
    txt_senha = StyledTextField(
        label="Senha", 
        cores=cores, 
        icon_name=ft.Icons.LOCK_OUTLINE, 
        is_password=True,
        on_submit=autenticar # Permite login com Enter
    )
    
    btn_entrar = StyledButton(
        text="ENTRAR", 
        cores=cores, 
        icon=ft.Icons.LOGIN, 
        on_click=autenticar
    )
    
    # --- Layout da Tela de Login ---
    
    # Coluna do Formulário
    form_column = ft.Container(
        content=ft.Column(
            [
                ft.Text("Bem-vindo ao Salsa!", size=32, weight=ft.FontWeight.BOLD, color=cores["texto_primario"]),
                ft.Text("Faça login para gerenciar seu restaurante.", color=cores["texto_secundario"]),
                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                txt_login,
                txt_senha,
                ft.Container(height=20),
                ft.Row(
                    [btn_entrar],
                    alignment=ft.MainAxisAlignment.END
                )
            ],
            width=350,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=40,
        border_radius=20,
        bgcolor=cores["surface"],
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
            offset=ft.Offset(0, 5),
        )
    )
    
    # Coluna de Branding (Esquerda)
    branding_column = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.RESTAURANT_MENU, size=80, color=ft.Colors.WHITE),
                ft.Text(
                    "Salsa", 
                    size=50, 
                    weight=ft.FontWeight.BOLD, 
                    color=ft.Colors.WHITE
                ),
                ft.Text(
                    "Gestão Inteligente para Restaurantes",
                    size=16,
                    color=ft.Colors.WHITE70,
                    italic=True
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER, # <--- CORREÇÃO AQUI
            spacing=20
        ),
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[
                CORES["light"]["primaria"], # Vermelho Salsa
                ft.Colors.with_opacity(0.7, CORES["light"]["primaria"]),
            ]
        )
    )

    return ft.Row(
        controls=[
            branding_column,
            ft.Container(
                content=form_column,
                expand=True,
                alignment=ft.alignment.center,
                bgcolor=cores["background"]
            )
        ],
        expand=True
    )