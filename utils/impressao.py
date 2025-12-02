# restaurante_sistema/utils/impressao.py (VERSÃO COM win32print)

from datetime import datetime
import os
try:
    import win32print # Importa a biblioteca para impressão no Windows
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("Aviso: A biblioteca 'pywin32' não está instalada. A impressão não funcionará no Windows.")


def gerar_pedido_cozinha(itens, origem="Caixa", destino=None):
    """
    Gera o pedido e o envia para a impressora configurada no Windows.
    """
    
    # --- 1. Defina o nome da sua impressora AQUI ---
    # O nome exato que você encontrou nas configurações do Windows.
    NOME_DA_IMPRESSORA = "MP-4200 TH" 

    # Monta o conteúdo do pedido em uma única string de texto
    conteudo_lista = [
        "        NOVO PEDIDO PARA COZINHA        ",
        "========================================",
        f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        f"Origem: {origem}",
    ]
    if destino:
        conteudo_lista.append(f"Destino: {destino}")
    
    conteudo_lista.extend([
        "----------------------------------------",
        "ITENS:",
        "----------------------------------------"
    ])
    
    total_itens = 0
    for item in itens:
        # Formata a linha para garantir alinhamento simples
        linha = f"{item['quantidade']}x {item['nome']}"
        conteudo_lista.append(linha)
        total_itens += item['quantidade']
    
    conteudo_lista.extend([
        "----------------------------------------",
        f"TOTAL DE ITENS: {total_itens}",
        "========================================",
        "\n\n\n\n\n" # Adiciona espaços para empurrar o papel e facilitar o corte
    ])
    
    conteudo_texto = "\n".join(conteudo_lista)

    # --- 2. Lógica de Impressão com win32print ---
    if WIN32_AVAILABLE:
        try:
            # Codificação para impressoras térmicas em português (para acentos, ç, etc.)
            dados_impressao = conteudo_texto.encode('cp850', errors='replace')
            
            h_impressora = win32print.OpenPrinter(NOME_DA_IMPRESSORA)
            try:
                # Inicia o documento de impressão
                h_job = win32print.StartDocPrinter(h_impressora, 1, ("Pedido Cozinha - Salsa", None, "RAW"))
                try:
                    # Inicia a página
                    win32print.StartPagePrinter(h_impressora)
                    # Escreve os dados brutos na impressora
                    win32print.WritePrinter(h_impressora, dados_impressao)
                    # Finaliza a página
                    win32print.EndPagePrinter(h_impressora)
                finally:
                    # Finaliza o documento
                    win32print.EndDocPrinter(h_impressora)
            finally:
                # Fecha a conexão com a impressora
                win32print.ClosePrinter(h_impressora)
            
            print("Pedido enviado para a impressora com sucesso.")
            
        except Exception as e:
            print(f"ERRO DE IMPRESSÃO: Não foi possível enviar para a impressora '{NOME_DA_IMPRESSORA}'. Verifique se o nome está correto e se a impressora está online. Erro: {e}")
            # A falha na impressão não impede o salvamento do arquivo de backup.
    else:
        print("Impressão pulada. A biblioteca 'pywin32' não foi encontrada.")


    # --- 3. Salva o arquivo de texto como backup (comportamento original) ---
    try:
        # Garante que a pasta de pedidos exista
        if not os.path.exists("pedidos_para_cozinha"):
            os.makedirs("pedidos_para_cozinha")
            
        # Cria um nome de arquivo único
        nome_arquivo = f"pedido_{datetime.now().strftime('%Y%m%d%H%M%S')}_{origem.replace(' ', '_')}.txt"
        caminho_arquivo = os.path.join("pedidos_para_cozinha", nome_arquivo)
        
        # Salva o conteúdo no arquivo
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo_texto)
            
        return True, f"Pedido gerado em: {caminho_arquivo}"
        
    except Exception as e:
        return False, f"Erro ao gerar arquivo de pedido: {e}"