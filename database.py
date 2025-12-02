# database.py (CORRIGIDO COM HASH DE SENHA)
import sqlite3
import os
import bcrypt # <--- 1. IMPORTE A BIBLIOTECA

DB_FILE = "restaurante.db"

def conectar():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()

def criar_tabelas():
    conn, cursor = conectar()

    # (O restante das criações de tabela 'estoque', 'transacoes', 'configuracoes', 'mesas', 'pedidos' continua igual...)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        quantidade REAL NOT NULL,
        unidade TEXT NOT NULL,
        valor_compra REAL NOT NULL,
        data_compra TEXT NOT NULL,
        data_validade TEXT NOT NULL,
        fornecedor TEXT,
        estoque_minimo REAL NOT NULL,
        data_reposicao TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_venda TEXT NOT NULL,
        itens TEXT,
        total REAL NOT NULL,
        metodo_pagamento TEXT,
        tipo TEXT NOT NULL,
        descricao TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracoes (
        id INTEGER PRIMARY KEY CHECK (id = 1), -- Garante que só haverá uma linha
        nome_comerciante TEXT NOT NULL,
        chave_pix TEXT NOT NULL,
        cidade TEXT NOT NULL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL -- 'LIVRE', 'OCUPADA'
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mesa_id INTEGER,
        itens TEXT NOT NULL, -- JSON dos itens, quantidade e preço de venda
        total REAL NOT NULL,
        data_abertura TEXT NOT NULL,
        data_fechamento TEXT,
        status TEXT NOT NULL, -- 'ABERTO', 'PAGO'
        FOREIGN KEY (mesa_id) REFERENCES mesas (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        login TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL,
        permissao TEXT NOT NULL -- 'GERENTE', 'CAIXA'
    )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM mesas")
    if cursor.fetchone()[0] == 0:
        for i in range(1, 11):
            cursor.execute("INSERT INTO mesas (nome, status) VALUES (?, 'LIVRE')", (f'Mesa {i}',))
        cursor.execute("INSERT INTO mesas (nome, status) VALUES (?, 'LIVRE')", ('Balcão/Delivery',))
        
    # Adiciona um usuário administrador padrão (login: admin, senha: 123456)
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        
        # --- 2. LÓGICA DE HASH ---
        senha_bytes = b'123456' # Senha em bytes
        sal = bcrypt.gensalt()
        hash_senha = bcrypt.hashpw(senha_bytes, sal)
        # Armazena o hash como string no banco
        hash_str = hash_senha.decode('utf-8') 
        
        cursor.execute("INSERT INTO usuarios (nome, login, senha, permissao) VALUES (?, ?, ?, ?)", 
                       ('Administrador', 'admin', hash_str, 'GERENTE')) # <--- 3. SALVA O HASH

    conn.commit()
    conn.close()


criar_tabelas()