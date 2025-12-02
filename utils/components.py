# restaurante_sistema/utils/components.py
import flet as ft

# --- Componentes "Salsa" Reutilizáveis ---

class StyledCard(ft.Card):
    """
    Um Cartão com o estilo padrão "Salsa" (elevação, borda, sombra).
    """
    def __init__(self, content, cores, expand=False, padding=20, color=None):
        # CORREÇÃO: O Card não aceita padding direto.
        # Envolvemos o conteúdo em um Container para aplicar o padding.
        content_with_padding = ft.Container(
            content=content,
            padding=padding
        )
        
        super().__init__(
            content=content_with_padding,
            expand=expand,
            elevation=2,
            shadow_color=ft.Colors.with_opacity(0.05, ft.Colors.BLACK),
            shape=ft.RoundedRectangleBorder(radius=12),
            color=color if color is not None else cores["surface"]
        )

def StyledTextField(label, cores, icon_name=None, is_password=False, prefix_text=None, on_change=None, on_submit=None, read_only=False, multiline=False):
    """
    Um Campo de Texto com o estilo padrão "Salsa".
    """
    prefix_icon_control = None
    if icon_name:
        prefix_icon_control = ft.Icon(name=icon_name, color=cores["texto_secundario"])
        
    return ft.TextField(
        label=label,
        prefix_icon=prefix_icon_control, 
        prefix_text=prefix_text,
        password=is_password,
        can_reveal_password=is_password,
        border_radius=10,
        border_color=cores["texto_secundario"],
        focused_border_color=cores["primaria"],
        cursor_color=cores["primaria"],
        label_style=ft.TextStyle(color=cores["texto_secundario"]),
        text_style=ft.TextStyle(color=cores["texto_primario"]),
        on_change=on_change,
        on_submit=on_submit,
        read_only=read_only,
        multiline=multiline
    )

def StyledButton(text, cores, icon=None, on_click=None, expand=False, bgcolor=None, height=50):
    """
    Um Botão Primário (de ação) com o estilo "Salsa".
    """
    cor_bg = bgcolor if bgcolor else cores["primaria"]
    
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        expand=expand,
        height=height,
        style=ft.ButtonStyle(
            bgcolor=cor_bg, 
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=10),
        )
    )

def StyledOutlinedButton(text, cores, icon=None, on_click=None, expand=False, visible=True, height=50):
    """
    Um Botão Secundário (ex: Cancelar) com o estilo "Salsa".
    """
    return ft.OutlinedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        expand=expand,
        visible=visible,
        height=height,
        style=ft.ButtonStyle(
            color=cores["texto_secundario"],
            # CORREÇÃO: BorderSide exige 'width'
            side=ft.BorderSide(width=1, color=cores["texto_secundario"]),
            shape=ft.RoundedRectangleBorder(radius=10),
        )
    )
    
def StyledTextButton(text, cores, icon=None, on_click=None):
    """
    Um Botão de Texto (para diálogos) com o estilo "Salsa".
    """
    return ft.TextButton(
        text=text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(color=cores["primaria"])
    )

def StyledDataTable(datatable: ft.DataTable, cores):
    """
    Aplica o estilo "Salsa" a um ft.DataTable existente.
    """
    # CORREÇÃO: DataRowStyle foi removido/alterado. Usamos heading_row_color diretamente.
    datatable.heading_row_color = ft.Colors.with_opacity(0.05, cores["texto_primario"])
    datatable.data_row_color = cores["surface"]
    
    for col in datatable.columns:
        if isinstance(col.label, ft.Text):
            label_text = col.label.value
            # CORREÇÃO: FontWeight.W_500
            col.label = ft.Text(label_text, weight=ft.FontWeight.W_500, color=cores["texto_primario"])
        
    return datatable

def Title(text: str, cores):
    return ft.Text(text, size=32, weight=ft.FontWeight.BOLD, color=cores["texto_primario"])

def SubTitle(text: str, cores):
    return ft.Text(text, size=22, weight=ft.FontWeight.BOLD, color=cores["texto_primario"])

def BodyText(text: str, cores, is_secondary=False):
    return ft.Text(
        text,
        color=cores["texto_secundario"] if is_secondary else cores["texto_primario"]
    )