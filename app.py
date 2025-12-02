# restaurante_sistema/app.py
import flet as ft
import requests  # NOVA IMPORTAÇÃO NECESSÁRIA
from views.dashboard_view import DashboardView
from views.estoque_view import EstoqueView
from views.caixa_view import CaixaViewFunction 
from views.configuracoes_view import ConfiguracoesView
from views.comandas_view import ComandasViewFunction
from views.login_view import LoginView 
from views.cadastro_usuario_view import CadastroUsuarioView
from views.historico_view import HistoricoView 
from datetime import datetime

# --- LÓGICA DE LICENÇA (NOVA) ---
def verificar_licenca(page):
    """
    Verifica se o cliente tem permissão para usar o software.
    Retorna True se permitido, False se bloqueado.
    """
    # URL DE CONTROLE: Substitua pelo seu link real (ex: arquivo JSON no Pastebin/GitHub ou sua API)
    # O JSON esperado é algo como: {"status": "ativo"} ou {"status": "bloqueado", "mensagem": "..."}
    URL_SUA_API = ""
    
    try:
        # Tenta conectar com timeout curto (3 segundos) para não travar a abertura
        response = requests.get(URL_SUA_API, timeout=3)
        
        if response.status_code == 200:
            dados = response.json()
            if dados.get("status") == "bloqueado":
                # SE ESTIVER BLOQUEADO: Limpa a tela e mostra aviso
                page.clean()
                page.bgcolor = "#1A1C1E"
                page.add(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.BLOCK, size=100, color=ft.Colors.RED),
                            ft.Text("ACESSO BLOQUEADO", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                            ft.Text(dados.get("mensagem", "Licença suspensa. Contate o suporte."), color=ft.Colors.WHITE),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        expand=True
                    )
                )
                page.update()
                return False # Bloqueia o carregamento do resto do app
                
    except Exception as e:
        # Se não tiver internet ou erro na API, por padrão deixamos passar (fail-open)
        # para não prejudicar o cliente se a internet cair.
        # Se quiser ser rigoroso e bloquear sem internet, mude para return False.
        print(f"Aviso de Licença: Não foi possível verificar ({e})")
        return True

    return True

# --- Paleta de Cores "Salsa" ---
CORES = {
    "light": {
        "primaria": "#D90429",
        "background": "#F8F7F4",
        "surface": "#FFFFFF",
        "texto_primario": "#1A1C1E",
        "texto_secundario": "#5F5F5F",
        "verde": "#2A9134",
    },
    "dark": {
        "primaria": "#FFB3AD",
        "background": "#1A1C1E",
        "surface": "#2F3033",
        "texto_primario": "#E3E2E6",
        "texto_secundario": "#A0A0A0",
        "verde": "#8ADC8E",
    }
}

def main(page: ft.Page):
    # --- PASSO 1: VERIFICAÇÃO DE LICENÇA ---
    if not verificar_licenca(page):
        return # Para a execução aqui se estiver bloqueado

    page.title = "Salsa - Gestão para Restaurantes"
    page.window_width = 1200
    page.window_height = 800
    page.padding = 0
    
    # --- Configuração de Fonte ---
    page.fonts = {
        "Poppins": "https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap"
    }
    page.theme = ft.Theme(font_family="Poppins")
    page.dark_theme = ft.Theme(font_family="Poppins")

    # --- VARIÁVEL DE ESTADO DE LOGIN ---
    usuario_logado = None 

    # DatePicker global para uso nas telas
    date_picker = ft.DatePicker(
        first_date=datetime(2023, 1, 1),
        help_text="Selecione a data"
    )
    page.overlay.append(date_picker)

    # --- Conteúdo Principal ---
    main_content = ft.Container(
        expand=True,
        padding=ft.padding.all(25),
        alignment=ft.alignment.top_left
    )
    
    # --- Roteamento e Estilo ---
    
    def aplicar_tema(modo):
        cores = CORES[modo]
        page.bgcolor = cores["background"]
        main_content.bgcolor = cores["background"]
        
        if page.appbar:
            page.appbar.bgcolor = cores["surface"]
            page.appbar.title.color = cores["texto_primario"]
            # Ajuste seguro para ícones da AppBar
            if page.appbar.actions:
                for action in page.appbar.actions:
                    if hasattr(action, 'icon_color'):
                        action.icon_color = cores["texto_secundario"]
        
        if rail:
            rail.bgcolor = cores["surface"]
            # Atualiza cores dos destinos do Rail
            for dest in rail.destinations:
                dest.icon_content = ft.Icon(dest.icon, color=cores["texto_secundario"])
                dest.selected_icon_content = ft.Icon(dest.selected_icon, color=cores["primaria"])
            rail.update()


    def permissao_gerente_necessaria(page, view_function):
        modo = page.theme_mode.value.lower() if page.theme_mode else "light"
        cores = CORES[modo]

        if usuario_logado and usuario_logado.get('permissao') == 'GERENTE':
            return view_function()
        else:
            return ft.Column(
                [
                    ft.Icon(ft.Icons.LOCK_OUTLINE, size=100, color=cores["primaria"]),
                    ft.Text("Acesso Negado", size=32, weight=ft.FontWeight.BOLD, color=cores["texto_primario"]),
                    ft.Text("Apenas Gerentes podem acessar esta tela.", size=16, color=cores["texto_secundario"]),
                ],
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20
            )

    def on_login_success(usuario):
        nonlocal usuario_logado
        usuario_logado = usuario
        page.appbar.visible = True
        rail.visible = True
        page.go("/dashboard")
        page.update()

    def route_change(route):
        # Pega as cores do tema ATUAL
        modo = page.theme_mode.value.lower() if page.theme_mode else "light"
        cores_atuais = CORES[modo]
        
        nova_view = None
        
        if page.route == "/login":
            page.appbar.visible = False
            rail.visible = False
            main_content.padding = 0
            # Passa o dicionário completo CORES para o LoginView gerenciar seu tema interno se precisar
            nova_view = LoginView(page, on_login_success, CORES)
        else:
            page.appbar.visible = True
            rail.visible = True
            main_content.padding = 25
            
            if not usuario_logado:
                page.go("/login")
                return

            # Instancia as Views passando as cores atuais
            if page.route == "/dashboard" or page.route == "/":
                nova_view = DashboardView(cores=cores_atuais)
            elif page.route == "/caixa":
                nova_view = CaixaViewFunction(page, cores=cores_atuais)
            elif page.route == "/comandas":
                nova_view = ComandasViewFunction(page, cores=cores_atuais)
            elif page.route == "/estoque":
                nova_view = permissao_gerente_necessaria(page, lambda: EstoqueView(page, date_picker, cores=cores_atuais))
            elif page.route == "/configuracoes":
                nova_view = permissao_gerente_necessaria(page, lambda: ConfiguracoesView(page, cores=cores_atuais))
            elif page.route == "/usuarios":
                nova_view = permissao_gerente_necessaria(page, lambda: CadastroUsuarioView(page, cores=cores_atuais))
            elif page.route == "/historico":
                nova_view = permissao_gerente_necessaria(page, lambda: HistoricoView(page, cores=cores_atuais))
        
        main_content.content = nova_view
        
        if page.route != "/login":
             aplicar_tema(modo)
             
        page.update()

    def change_theme(e):
        page.theme_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        aplicar_tema(page.theme_mode.value.lower())
        route_change(page.route) 
        
    def logout(e):
        nonlocal usuario_logado
        usuario_logado = None
        page.go("/login")

    # --- Estrutura da Página ---
    
    page.appbar = ft.AppBar(
        title=ft.Text("Salsa", weight=ft.FontWeight.BOLD),
        center_title=False,
        elevation=0, 
        bgcolor=CORES["light"]["surface"],
        actions=[
            ft.IconButton(ft.Icons.WB_SUNNY_OUTLINED, on_click=change_theme, tooltip="Mudar Tema"),
            ft.IconButton(ft.Icons.LOGOUT, on_click=logout, tooltip="Logout"),
        ],
        visible=False 
    )

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD_OUTLINED, selected_icon=ft.Icons.DASHBOARD, label="Dashboard"),
            ft.NavigationRailDestination(icon=ft.Icons.POINT_OF_SALE_OUTLINED, selected_icon=ft.Icons.POINT_OF_SALE, label="Caixa"),
            ft.NavigationRailDestination(icon=ft.Icons.ROOM_SERVICE_OUTLINED, selected_icon=ft.Icons.ROOM_SERVICE, label="Comandas"),
            ft.NavigationRailDestination(icon=ft.Icons.INVENTORY_2_OUTLINED, selected_icon=ft.Icons.INVENTORY_2, label="Estoque"),
            ft.NavigationRailDestination(icon=ft.Icons.HISTORY_OUTLINED, selected_icon=ft.Icons.HISTORY, label="Historico"),
            ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="Configuracoes"),
            ft.NavigationRailDestination(icon=ft.Icons.PEOPLE_OUTLINE, selected_icon=ft.Icons.PEOPLE, label="Usuarios"),
        ],
        on_change=lambda e: page.go(f"/{e.control.destinations[e.control.selected_index].label.lower()}"),
        visible=False
    )

    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                main_content, 
            ],
            expand=True,
            spacing=0
        )
    )

    # Define tema inicial
    page.theme_mode = ft.ThemeMode.LIGHT 
    
    page.on_route_change = route_change
    
    # Sincroniza rota inicial
    current_route = page.route or "/login"
    if current_route != "/login":
        nav_labels = [dest.label.lower() for dest in rail.destinations]
        route_name = current_route.strip('/')
        map_rotas = {
            "dashboard": 0, "caixa": 1, "comandas": 2, 
            "estoque": 3, "historico": 4, "configuracoes": 5, "usuarios": 6
        }
        if route_name in map_rotas:
            rail.selected_index = map_rotas[route_name]
        elif route_name == "":
             rail.selected_index = 0 
    
    page.go(current_route)

if __name__ == "__main__":
    ft.app(target=main)