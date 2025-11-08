import sqlite3
import uuid
import os
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'reseller_panel_secret_key_12345'
DATABASE = 'reseller_panel.db'

# --- 1. Inicialização do Banco de Dados (COM SEU NOVO LOGIN) ---

def get_db():
    """Conecta ao banco de dados"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Cria as tabelas SE NÃO EXISTIREM, com regras de 'CASCADE'
    para permitir exclusões corretas.
    """
    print("🚀 Verificando o banco de dados (v4.1 - Final Corrigido)...")
    conn = get_db()
    c = conn.cursor()
    
    # Habilitar chaves estrangeiras é essencial para 'ON DELETE CASCADE'
    c.execute("PRAGMA foreign_keys = ON")
    
    # Tabela 1: users
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'reseller',
        balance REAL NOT NULL DEFAULT 0.0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    print("✅ Tabela 'users' verificada.")
    
    # Tabela 2: products
    c.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    ''')
    print("✅ Tabela 'products' verificada.")

    # Tabela 3: plans
    c.execute('''
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        cost REAL NOT NULL,
        duration_days INTEGER NOT NULL,
        download_link TEXT,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
    )
    ''')
    print("✅ Tabela 'plans' verificada (com cascade).")
    
    # Tabela 4: purchases
    c.execute('''
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reseller_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        cost_paid REAL NOT NULL,
        purchase_id_ref TEXT UNIQUE NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (reseller_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE CASCADE
    )
    ''')
    print("✅ Tabela 'purchases' verificada (com cascade).")
    
    # --- Inserir dados de exemplo SOMENTE SE NÃO EXISTIREM ---
    
    # Verificar se o admin existe (COM SEU NOVO LOGIN)
    c.execute("SELECT * FROM users WHERE username = 'trader'") # <-- SEU LOGIN
    admin_exists = c.fetchone()
    if not admin_exists:
        admin_pass = generate_password_hash('traderbr') # <-- SUA SENHA
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('trader', admin_pass, 'admin')) # <-- SEU LOGIN E ROLE 'admin'
        print("👤 Usuário 'trader' (senha: 'traderbr') criado.")
    
    # Verificar se o revendedor1 existe
    c.execute("SELECT * FROM users WHERE username = 'revendedor1'")
    reseller_exists = c.fetchone()
    if not reseller_exists:
        reseller_pass = generate_password_hash('revenda123')
        c.execute("INSERT INTO users (username, password, role, balance) VALUES (?, ?, ?, ?)",
                  ('revendedor1', reseller_pass, 'reseller', 150.0))
        print("👤 Usuário 'revendedor1' (senha: 'revenda123', saldo: 150.0) criado.")

    # Verificar se o produto existe
    c.execute("SELECT * FROM products WHERE name = 'Cheat Free Fire'")
    product_exists = c.fetchone()
    product_id = None
    if product_exists:
        product_id = product_exists['id']
    else:
        c.execute("INSERT INTO products (name) VALUES ('Cheat Free Fire')")
        product_id = c.lastrowid
        print("📦 Produto 'Cheat Free Fire' criado.")

    # Verificar se os planos existem
    c.execute("SELECT * FROM plans WHERE product_id = ?", (product_id,))
    plan_exists = c.fetchone()
    if not plan_exists:
        # Inserir planos para este novo produto
        c.execute("INSERT INTO plans (product_id, name, cost, duration_days, download_link) VALUES (?, 'Semanal', 15.00, 7, 'https://exemplo.com/link_semanal.zip')", (product_id,))
        c.execute("INSERT INTO plans (product_id, name, cost, duration_days, download_link) VALUES (?, 'Mensal', 30.00, 30, 'https://exemplo.com/link_mensal.zip')", (product_id,))
        c.execute("INSERT INTO plans (product_id, name, cost, duration_days, download_link) VALUES (?, 'Permanente', 90.00, 9999, 'https://exemplo.com/link_permanente.zip')", (product_id,))
        print("💰 Planos (Semanal, Mensal, Permanente) criados com links de exemplo.")

    conn.commit()
    conn.close()
    print("\n🎉 Banco de dados verificado com sucesso!")


# --- 2. HTML Templates (MODO DARK + PARTÍCULAS + MODAIS) ---

# --- ESTILOS GLOBAIS E PARTÍCULAS (COM ESTILOS DE MODAL) ---
GLOBAL_STYLES_AND_PARTICLES = '''
<style>
    /* --- Fontes e Cores Base (Dark Mode) --- */
    :root {
        --bg-dark: #0a0a1a;
        --bg-card: #1a1a2e;
        --border-color: #3a3a5e;
        --text-light: #e0e0e0;
        --text-white: #ffffff;
        --text-dim: #888899;
        --primary: #007bff;
        --primary-hover: #0056b3;
        --success: #28a745;
        --success-hover: #1e7e34;
        --danger: #dc3545;
        --danger-hover: #a71d2a;
        --warning: #ffc107;
        --warning-hover: #d39e00;
    }
    
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: var(--bg-dark);
        color: var(--text-light);
        margin: 0;
        padding: 20px;
    }

    /* --- Partículas de Fundo --- */
    .particles {
        position: fixed; top: 0; left: 0;
        width: 100%; height: 100%;
        pointer-events: none; z-index: -1;
    }
    .particle {
        position: absolute; width: 2px; height: 2px;
        background: var(--primary); border-radius: 50%;
        animation: float 6s infinite linear; opacity: 0;
    }

    @keyframes float {
        0% { transform: translateY(100vh) translateX(0); opacity: 0; }
        10% { opacity: 1; }
        90% { opacity: 1; }
        100% { transform: translateY(-100px) translateX(100px); opacity: 0; }
    }
    
    /* --- Componentes --- */
    .container { max-width: 1200px; margin: auto; z-index: 1; position: relative; }
    .card {
        background: var(--bg-card); padding: 25px;
        border-radius: 12px; border: 1px solid var(--border-color);
        box-shadow: 0 8px 25px rgba(0, 123, 255, 0.1);
        margin-bottom: 20px;
    }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    h1, h2 { color: var(--text-white); }
    h2 {
        border-bottom: 2px solid var(--primary);
        padding-bottom: 10px; margin-bottom: 20px; font-weight: 600;
    }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td {
        padding: 12px 15px; border: 1px solid var(--border-color);
        text-align: left; vertical-align: middle;
    }
    th {
        background: rgba(0, 123, 255, 0.1); color: var(--text-white); font-weight: 600;
    }

    /* --- Formulários --- */
    form { display: block; margin-top: 15px; }
    form label {
        font-weight: 600; margin-top: 10px; display: block; color: var(--text-light);
    }
    input[type="text"], input[type="password"], input[type="number"], select {
        padding: 10px; border: 1px solid var(--border-color);
        border-radius: 8px; width: 100%;
        box-sizing: border-box; margin-top: 5px;
        background: #2a2a4e; color: var(--text-white); font-size: 1rem;
    }
    input::placeholder { color: var(--text-dim); }
    button, .btn {
        padding: 10px 20px; cursor: pointer; border: none;
        border-radius: 8px; font-size: 1rem; font-weight: 600;
        transition: all 0.3s ease; text-decoration: none;
        display: inline-block; text-align: center;
    }
    button:hover, .btn:hover {
        transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .btn-primary { background: var(--primary); color: white; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-success { background: var(--success); color: white; }
    .btn-success:hover { background: var(--success-hover); }
    .btn-danger { background: var(--danger); color: white; }
    .btn-danger:hover { background: var(--danger-hover); }
    .btn-warning { background: var(--warning); color: #111; }
    .btn-warning:hover { background: var(--warning-hover); }
    .btn-disabled { background: #555; color: #999; cursor: not-allowed; }
    .btn-disabled:hover { transform: none; box-shadow: none; }
    
    /* Ações em linha (para botões editar/excluir) */
    .inline-actions { display: flex; gap: 10px; flex-wrap: wrap; }
    .inline-actions form { margin: 0; }
    .inline-actions .btn { padding: 8px 12px; font-size: 0.9rem; }
    
    /* --- Feedback --- */
    .feedback {
        padding: 15px; border-radius: 8px;
        margin-bottom: 20px; font-weight: 600;
    }
    .feedback.success {
        background: rgba(40, 167, 69, 0.2);
        color: var(--success); border: 1px solid var(--success);
    }
    .feedback.error {
        background: rgba(220, 53, 69, 0.2);
        color: var(--danger); border: 1px solid var(--danger);
    }
    
    /* --- Específicos --- */
    .header {
        display: flex; justify-content: space-between;
        align-items: center; margin-bottom: 20px;
    }
    .balance { font-size: 2.5rem; color: var(--success); font-weight: 700; }
    code, .code {
        background: #2a2a4e; color: #ffb800; padding: 3px 6px;
        border-radius: 4px; font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
    }
    .file-status { 
        font-size: 0.9em; color: var(--text-dim); 
        word-break: break-all;
    }

    /* --- ESTILOS DO MODAL --- */
    .modal {
        display: none; position: fixed; z-index: 1000;
        left: 0; top: 0; width: 100%; height: 100%;
        overflow: auto; background-color: rgba(0,0,0,0.7);
        justify-content: center; align-items: center;
    }
    .modal-content {
        background: var(--bg-card); margin: auto; padding: 30px;
        border: 1px solid var(--border-color); border-radius: 12px;
        width: 90%; max-width: 500px;
    }
    .modal-header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 20px;
    }
    .modal-header h2 { margin: 0; padding: 0; border: none; }
    .close-btn {
        color: var(--text-dim); font-size: 28px; font-weight: bold;
        cursor: pointer;
    }
    .close-btn:hover { color: var(--text-white); }
    
    @media (max-width: 900px) {
        .grid { grid-template-columns: 1fr; }
    }
</style>

<div class="particles" id="particles"></div>

<script>
    document.addEventListener('DOMContentLoaded', function() {
        const particles = document.getElementById('particles');
        if (particles) {
            for (let i = 0; i < 50; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.left = Math.random() * 100 + 'vw';
                particle.style.animationDelay = Math.random() * 6 + 's';
                particle.style.animationDuration = (3 + Math.random() * 4) + 's';
                particles.appendChild(particle);
            }
        }
    });
</script>
'''

# Template da Página de Login
LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Revenda - Login</title>
    {{ GLOBAL_STYLES_AND_PARTICLES | safe }}
    <style>
        body {
            display: flex; justify-content: center;
            align-items: center; height: 100vh;
        }
        .login-box {
            background: var(--bg-card); padding: 40px;
            border-radius: 12px; border: 1px solid var(--border-color);
            box-shadow: 0 8px 25px rgba(0, 123, 255, 0.1);
            width: 100%; max-width: 400px;
            text-align: center; z-index: 1; position: relative;
        }
        .login-box h1 {
            color: var(--primary); margin-bottom: 30px; font-size: 2.5rem;
        }
        .login-box button { width: 100%; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>Painel Revenda</h1>
        {% if error %}
            <div class="feedback error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Usuário" required>
            <input type="password" name="password" placeholder="Senha" required style="margin-top: 15px;">
            <button type="submit" class="btn btn-primary">Entrar</button>
        </form>
    </div>
</body>
</html>
'''

# Template do Painel ADMIN
ADMIN_PANEL_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Painel Admin</title>
    {{ GLOBAL_STYLES_AND_PARTICLES | safe }}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Painel Admin <span style="color: var(--text-dim); font-size: 1.2rem;">({{ session.username }})</span></h1>
            <a href="/logout" class="btn btn-danger">Sair</a>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="feedback {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="grid">
            <div class="card">
                <h2>Gerenciar Revendedores</h2>
                
                <h3>Criar Novo Revendedor</h3>
                <form method="POST" action="/admin/create_reseller">
                    <label>Usuário:</label>
                    <input type="text" name="username" placeholder="Novo Usuário" required>
                    <label>Senha:</label>
                    <input type="text" name="password" placeholder="Nova Senha" required>
                    <button type="submit" class="btn btn-success" style="margin-top: 15px;">Criar</button>
                </form>

                <h3 style="margin-top: 30px;">Adicionar Créditos (Saldo)</h3>
                <form method="POST" action="/admin/add_credits">
                    <label>Revendedor:</label>
                    <select name="reseller_id" required>
                        <option value="">-- Selecione um Revendedor --</option>
                        {% for r in resellers %}
                        <option value="{{ r.id }}">{{ r.username }}</option>
                        {% endfor %}
                    </select>
                    <label>Valor:</label>
                    <input type="number" name="amount" placeholder="Valor (ex: 150.00)" step="0.01" required>
                    <button type="submit" class="btn btn-success" style="margin-top: 15px;">Adicionar Saldo</button>
                </form>

                <h3 style="margin-top: 30px;">Lista de Revendedores</h3>
                <table>
                    <tr><th>Usuário</th><th>Saldo (R$)</th><th>Ações</th></tr>
                    {% for r in resellers %}
                    <tr>
                        <td>{{ r.username }}</td>
                        <td style="color: var(--success); font-weight: bold;">R$ {{ "%.2f"|format(r.balance) }}</td>
                        <td>
                            <div class="inline-actions">
                                <button class="btn btn-warning" 
                                        onclick="openEditModal('editResellerModal', '{{ r.id }}', '{{ r.username }}')">
                                    Editar
                                </button>
                                <form method="POST" action="/admin/delete_reseller" 
                                      onsubmit="return confirm('Tem certeza que deseja excluir {{ r.username }}? TODAS as compras dele serão apagadas.');">
                                    <input type="hidden" name="reseller_id" value="{{ r.id }}">
                                    <button type="submit" class="btn btn-danger">Excluir</button>
                                </form>
                            </div>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="3">Nenhum revendedor encontrado.</td></tr>
                    {% endfor %}
                </table>
            </div>

            <div class="card">
                <h2>Gerenciar Produtos e Planos</h2>
                
                <h3>Adicionar/Editar Plano (com Link)</h3>
                <form method="POST" action="/admin/create_plan">
                    <label>Produto:</label>
                    <select name="product_id" required>
                        <option value="">-- Selecione o Produto --</option>
                        {% for p in products %}
                        <option value="{{ p.id }}">{{ p.name }}</option>
                        {% endfor %}
                    </select>
                    <label>Nome do Plano:</label>
                    <input type="text" name="name" placeholder="Nome (ex: Mensal)" required>
                    <label>Custo (R$):</label>
                    <input type="number" name="cost" placeholder="Custo (ex: 30.00)" step="0.01" required>
                    <label>Duração (Dias):</label>
                    <input type="number" name="duration_days" placeholder="Dias (ex: 30)" required>
                    <label>Link de Download (Google Drive, Mega, etc):</label>
                    <input type="text" name="download_link" placeholder="https://..." required>
                    
                    <button type="submit" class="btn btn-success" style="margin-top: 15px;">Criar/Atualizar Plano</button>
                </form>
                
                <h3 style="margin-top: 30px;">Gerenciar Produtos Atuais</h3>
                <form method="POST" action="/admin/create_product" style="display: flex; gap: 10px;">
                    <input type="text" name="name" placeholder="Nome do Novo Produto" required>
                    <button type="submit" class="btn btn-success" style="margin-top: 5px; width: 150px;">Criar Produto</button>
                </form>
                <table style="margin-top: 10px;">
                    <tr><th>Nome do Produto</th><th>Ações</th></tr>
                    {% for p in products %}
                    <tr>
                        <td>{{ p.name }}</td>
                        <td>
                             <div class="inline-actions">
                                <button class="btn btn-warning" 
                                        onclick="openEditModal('editProductModal', '{{ p.id }}', '{{ p.name }}')">
                                    Editar
                                </button>
                                <form method="POST" action="/admin/delete_product" 
                                      onsubmit="return confirm('Tem certeza que deseja excluir o produto {{ p.name }}? TODOS os planos e compras associados a ele serão apagados.');">
                                    <input type="hidden" name="product_id" value="{{ p.id }}">
                                    <button type="submit" class="btn btn-danger">Excluir</button>
                                </form>
                            </div>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="2">Nenhum produto criado.</td></tr>
                    {% endfor %}
                </table>


                <h3 style="margin-top: 30px;">Planos Atuais</h3>
                <table>
                    <tr><th>Produto</th><th>Plano</th><th>Custo (R$)</th><th>Link</th><th>Ações</th></tr>
                    {% for p in plans %}
                    <tr>
                        <td>{{ p.product_name }}</td>
                        <td>{{ p.name }}</td>
                        <td>R$ {{ "%.2f"|format(p.cost) }}</td>
                        <td class="file-status">
                            {% if p.download_link %}
                                <a href="{{ p.download_link }}" target="_blank">Ver Link</a>
                            {% else %}
                                <span style="color:var(--danger); font-weight: bold;">Sem link!</span>
                            {% endif %}
                        </td>
                        <td>
                            <form method="POST" action="/admin/delete_plan" 
                                  onsubmit="return confirm('Tem certeza que deseja excluir o plano {{ p.name }}? TODAS as compras deste plano serão apagadas.');">
                                <input type="hidden" name="plan_id" value="{{ p.id }}">
                                <button type="submit" class="btn btn-danger">Excluir</button>
                            </form>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="5">Nenhum plano encontrado.</td></tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </div>
    
    <div id="editResellerModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Editar Revendedor</h2>
                <span class="close-btn" onclick="closeModal('editResellerModal')">&times;</span>
            </div>
            <form method="POST" action="/admin/update_reseller">
                <input type="hidden" id="editResellerId" name="reseller_id">
                <label>Nome de Usuário:</label>
                <input type="text" id="editUsername" name="username" required>
                <label>Nova Senha:</label>
                <input type="text" name="password" placeholder="Deixe em branco para não alterar">
                <button type="submit" class="btn btn-warning" style="margin-top: 20px;">Salvar Alterações</button>
            </form>
        </div>
    </div>
    
    <div id="editProductModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Editar Produto</h2>
                <span class="close-btn" onclick="closeModal('editProductModal')">&times;</span>
            </div>
            <form method="POST" action="/admin/update_product">
                <input type="hidden" id="editProductId" name="product_id">
                <label>Nome do Produto:</label>
                <input type="text" id="editProductName" name="name" required>
                <button type="submit" class="btn btn-warning" style="margin-top: 20px;">Salvar Alterações</button>
            </form>
        </div>
    </div>

    <script>
        function openEditModal(modalId, id, name) {
            const modal = document.getElementById(modalId);
            if (modalId === 'editResellerModal') {
                modal.querySelector('#editResellerId').value = id;
                modal.querySelector('#editUsername').value = name;
            } else if (modalId === 'editProductModal') {
                modal.querySelector('#editProductId').value = id;
                modal.querySelector('#editProductName').value = name;
            }
            modal.style.display = 'flex';
        }

        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }

        // Fechar se clicar fora
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
            }
        }
    </script>
</body>
</html>
'''

# Template do Painel do REVEENDEDOR
RESELLER_PANEL_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Painel do Revendedor</title>
    {{ GLOBAL_STYLES_AND_PARTICLES | safe }}
    <style>
        h2 { border-bottom-color: var(--success); color: var(--success); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Painel do Revendedor <span style="color: var(--text-dim); font-size: 1.2rem;">({{ reseller.username }})</span></h1>
            <a href="/logout" class="btn btn-danger">Sair</a>
        </div>
        
        <div class="card">
            <h2>Meu Saldo (Créditos)</h2>
            <div class="balance">R$ {{ "%.2f"|format(reseller.balance) }}</div>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="feedback {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card">
            <h2>Comprar Acesso ao Produto</h2>
            <p style="color: var(--text-dim);">Ao comprar, o custo será descontado do seu saldo e o item aparecerá no seu "Histórico de Compras" com o link para download.</p>
            <table>
                <tr><th>Produto</th><th>Plano</th><th>Custo (R$)</th><th>Duração</th><th>Ação</th></tr>
                {% for p in plans %}
                <tr>
                    <td>{{ p.product_name }}</td>
                    <td>{{ p.name }}</td>
                    <td>R$ {{ "%.2f"|format(p.cost) }}</td>
                    <td>{{ p.duration_days }} dias</td>
                    <td>
                        <form method="POST" action="/reseller/purchase" style="margin:0;" onsubmit="return confirm('Tem certeza que deseja comprar este produto? O custo de R$ {{ "%.2f"|format(p.cost) }} será descontado do seu saldo.');">
                            <input type="hidden" name="plan_id" value="{{ p.id }}">
                            
                            {% set disabled = not p.download_link or p.cost > reseller.balance %}
                            {% set title = "" %}
                            {% if not p.download_link %}
                                {% set title = "Produto indisponível (sem link)" %}
                            {% elif p.cost > reseller.balance %}
                                {% set title = "Saldo insuficiente" %}
                            {% endif %}
                            
                            <button type="submit" class="btn {{ 'btn-primary' if not disabled else 'btn-disabled' }}"
                                {{ 'disabled' if disabled else '' }} title="{{ title }}">
                                Comprar
                            </button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="card">
            <h2>Meu Histórico de Compras</h2>
            <p style="color: var(--text-dim);">Use o <strong class="code">ID da Compra</strong> para me pedir a chave KeyAuth (via Discord/WhatsApp).</p>
            <table>
                <tr><th>ID da Compra</th><th>Produto</th><th>Plano</th><th>Custo Pago</th><th>Data</th><th>Download</th></tr>
                {% for p in purchases %}
                <tr>
                    <td><strong class="code">{{ p.purchase_id_ref }}</strong></td>
                    <td>{{ p.product_name }}</td>
                    <td>{{ p.plan_name }}</td>
                    <td>R$ {{ "%.2f"|format(p.cost_paid) }}</td>
                    <td>{{ p.created_at.split(' ')[0] }}</td>
                    <td>
                        <a href="{{ url_for('get_download_link', purchase_id=p.id) }}" class="btn btn-success" target="_blank">
                            Link de Download
                        </a>
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="6">Nenhuma compra realizada ainda.</td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
'''

# --- 3. Rotas da Aplicação (COMPLETAS E CORRIGIDAS) ---

# Função helper para checar sessão
def require_role(role_name):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or session.get('role') != role_name:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Rotas de Login / Logout / Dashboard ---

@app.route("/", methods=["GET", "POST"])
def login():
    if session.get('user_id'):
        # Se já está logado, verifica se o usuário ainda existe
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        conn.close()
        if user:
            return redirect(url_for('dashboard'))
        else:
            # Usuário não existe (foi deletado), limpa a sessão
            session.clear()
            
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user["password"], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            error = "Usuário ou senha inválidos."
            
    return render_template_string(LOGIN_HTML, GLOBAL_STYLES_AND_PARTICLES=GLOBAL_STYLES_AND_PARTICLES, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/dashboard")
def dashboard():
    # CORREÇÃO DO LOOP 'ERR_TOO_MANY_REDIRECTS'
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    
    if not user:
        # Usuário foi deletado, limpa sessão e vai para login
        session.clear()
        return redirect(url_for('login'))

    if session['role'] == 'admin':
        return redirect(url_for('admin_panel'))
    elif session['role'] == 'reseller':
        return redirect(url_for('reseller_panel'))
    else:
        # Se a role for desconhecida (como 'trader'), desloga
        session.clear()
        flash("Função de usuário desconhecida. Fazendo logout.", "error")
        return redirect(url_for('login'))

# --- Rotas do ADMIN (COMPLETAS) ---

@app.route("/admin")
@require_role('admin')
def admin_panel():
    conn = get_db()
    resellers = conn.execute("SELECT * FROM users WHERE role = 'reseller' ORDER BY username").fetchall()
    products = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    plans = conn.execute(
        "SELECT p.name as product_name, pl.* FROM plans pl "
        "JOIN products p ON p.id = pl.product_id ORDER BY p.name, pl.cost"
    ).fetchall()
    conn.close()
    
    return render_template_string(ADMIN_PANEL_HTML, GLOBAL_STYLES_AND_PARTICLES=GLOBAL_STYLES_AND_PARTICLES, resellers=resellers, products=products, plans=plans)

@app.route("/admin/create_reseller", methods=["POST"])
@require_role('admin')
def create_reseller():
    username = request.form['username']
    password = request.form['password']
    
    if not username or not password:
        flash('Usuário e senha são obrigatórios.', 'error')
        return redirect(url_for('admin_panel'))
        
    try:
        hashed_pass = generate_password_hash(password)
        conn = get_db()
        conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'reseller')",
                     (username, hashed_pass))
        conn.commit()
        conn.close()
        flash(f'Revendedor "{username}" criado com sucesso!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Erro: Usuário "{username}" já existe.', 'error')
    
    return redirect(url_for('admin_panel'))

# ROTA ADICIONADA: ATUALIZAR REVENDEDOR
@app.route("/admin/update_reseller", methods=["POST"])
@require_role('admin')
def update_reseller():
    try:
        reseller_id = request.form['reseller_id']
        username = request.form['username']
        password = request.form.get('password') # .get() pois pode ser opcional

        conn = get_db()
        if password:
            # Se uma nova senha foi fornecida, atualiza
            hashed_pass = generate_password_hash(password)
            conn.execute("UPDATE users SET username = ?, password = ? WHERE id = ?",
                         (username, hashed_pass, reseller_id))
            flash(f'Usuário "{username}" e senha atualizados!', 'success')
        else:
            # Se não, atualiza só o nome de usuário
            conn.execute("UPDATE users SET username = ? WHERE id = ?",
                         (username, reseller_id))
            flash(f'Usuário "{username}" atualizado (senha mantida)!', 'success')
        
        conn.commit()
    except sqlite3.IntegrityError:
        flash(f'Erro: Nome de usuário "{username}" já existe.', 'error')
    except Exception as e:
        flash(f'Erro ao atualizar: {e}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('admin_panel'))

# ROTA ADICIONADA: EXCLUIR REVENDEDOR
@app.route("/admin/delete_reseller", methods=["POST"])
@require_role('admin')
def delete_reseller():
    try:
        reseller_id = request.form['reseller_id']
        conn = get_db()
        conn.execute("PRAGMA foreign_keys = ON")
        
        user = conn.execute("SELECT username FROM users WHERE id = ?", (reseller_id,)).fetchone()
        
        if not user:
             flash(f'Erro: Usuário não encontrado.', 'error')
             conn.close()
             return redirect(url_for('admin_panel'))

        username = user["username"]
        conn.execute("DELETE FROM users WHERE id = ?", (reseller_id,))
        conn.commit()
        conn.close()
        flash(f'Revendedor "{username}" e todo o seu histórico foram excluídos!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir: {e}', 'error')
        
    return redirect(url_for('admin_panel'))


@app.route("/admin/add_credits", methods=["POST"])
@require_role('admin')
def add_credits():
    try:
        reseller_id = int(request.form['reseller_id'])
        amount = float(request.form['amount'])
        
        if amount <= 0:
            flash('O valor deve ser positivo.', 'error')
            return redirect(url_for('admin_panel'))
            
        conn = get_db()
        conn.execute("UPDATE users SET balance = balance + ? WHERE id = ? AND role = 'reseller'",
                     (amount, reseller_id))
        conn.commit()
        
        reseller = conn.execute("SELECT username FROM users WHERE id = ?", (reseller_id,)).fetchone()
        conn.close()
        
        flash(f'R$ {amount:.2f} adicionados com sucesso a "{reseller["username"]}".', 'success')
    except Exception as e:
        flash(f'Erro ao adicionar créditos: {e}', 'error')
        
    return redirect(url_for('admin_panel'))

@app.route("/admin/create_product", methods=["POST"])
@require_role('admin')
def create_product():
    name = request.form['name']
    if name:
        try:
            conn = get_db()
            conn.execute("INSERT INTO products (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()
            flash(f'Produto "{name}" criado com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao criar produto: {e}', 'error')
    return redirect(url_for('admin_panel'))

# ROTA ADICIONADA: ATUALIZAR PRODUTO
@app.route("/admin/update_product", methods=["POST"])
@require_role('admin')
def update_product():
    try:
        product_id = request.form['product_id']
        name = request.form['name']
        
        conn = get_db()
        conn.execute("UPDATE products SET name = ? WHERE id = ?", (name, product_id))
        conn.commit()
        conn.close()
        flash(f'Produto atualizado para "{name}"!', 'success')
    except Exception as e:
        flash(f'Erro ao atualizar produto: {e}', 'error')
        
    return redirect(url_for('admin_panel'))

# ROTA ADICIONADA: EXCLUIR PRODUTO
@app.route("/admin/delete_product", methods=["POST"])
@require_role('admin')
def delete_product():
    try:
        product_id = request.form['product_id']
        conn = get_db()
        conn.execute("PRAGMA foreign_keys = ON")
        
        product = conn.execute("SELECT name FROM products WHERE id = ?", (product_id,)).fetchone()
        product_name = product['name']

        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        flash(f'Produto "{product_name}" (e todos os seus planos) foi excluído!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir produto: {e}', 'error')
        
    return redirect(url_for('admin_panel'))


# Rota de criar plano (MODIFICADA para aceitar LINK)
@app.route("/admin/create_plan", methods=["POST"])
@require_role('admin')
def create_plan():
    try:
        product_id = int(request.form['product_id'])
        name = request.form['name']
        cost = float(request.form['cost'])
        duration_days = int(request.form['duration_days'])
        download_link = request.form['download_link'] # Pega o link do formulário
        
        if not download_link.startswith('http'):
            flash('Link de download inválido. Deve começar com http:// ou https://', 'error')
            return redirect(url_for('admin_panel'))

        conn = get_db()
        
        existing_plan = conn.execute(
            "SELECT * FROM plans WHERE product_id = ? AND name = ?", 
            (product_id, name)
        ).fetchone()
        
        if existing_plan:
            conn.execute(
                "UPDATE plans SET cost = ?, duration_days = ?, download_link = ? WHERE id = ?",
                (cost, duration_days, download_link, existing_plan['id'])
            )
            flash(f'Plano "{name}" atualizado com NOVO link!', 'success')
        else:
            conn.execute(
                "INSERT INTO plans (product_id, name, cost, duration_days, download_link) VALUES (?, ?, ?, ?, ?)",
                (product_id, name, cost, duration_days, download_link)
            )
            flash(f'Plano "{name}" (R$ {cost:.2f}) criado com sucesso!', 'success')
            
        conn.commit()
        conn.close()
        
    except Exception as e:
        flash(f'Erro ao criar/atualizar plano: {e}', 'error')
        
    return redirect(url_for('admin_panel'))

# ROTA ADICIONADA: EXCLUIR PLANO
@app.route("/admin/delete_plan", methods=["POST"])
@require_role('admin')
def delete_plan():
    try:
        plan_id = request.form['plan_id']
        conn = get_db()
        conn.execute("PRAGMA foreign_keys = ON")
        
        plan = conn.execute("SELECT name FROM plans WHERE id = ?", (plan_id,)).fetchone()
        plan_name = plan['name']

        conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        conn.commit()
        conn.close()
        flash(f'Plano "{plan_name}" (e todas as suas compras) foi excluído!', 'success')
    except Exception as e:
        flash(f'Erro ao excluir plano: {e}', 'error')
        
    return redirect(url_for('admin_panel'))


# --- Rotas do REVENDEDOR ---

@app.route("/reseller")
@require_role('reseller')
def reseller_panel():
    conn = get_db()
    reseller_id = session['user_id']
    
    reseller = conn.execute("SELECT * FROM users WHERE id = ?", (reseller_id,)).fetchone()
    
    # Verificação de segurança: se o reseller for None, desloga o usuário
    if not reseller:
        session.clear()
        flash("Sua sessão expirou ou o usuário foi removido.", "error")
        return redirect(url_for('login'))

    # Lista de planos para comprar
    plans = conn.execute(
        "SELECT p.name as product_name, pl.* FROM plans pl "
        "JOIN products p ON p.id = pl.product_id "
        "WHERE p.is_active = 1 ORDER BY p.name, pl.cost"
    ).fetchall()
    
    # Histórico de compras
    purchases = conn.execute(
        "SELECT p.*, pl.name as plan_name, pr.name as product_name "
        "FROM purchases p "
        "JOIN plans pl ON pl.id = p.plan_id "
        "JOIN products pr ON pr.id = pl.product_id " 
        "WHERE p.reseller_id = ? ORDER BY p.created_at DESC",
        (reseller_id,)
    ).fetchall()
    
    conn.close()
    
    return render_template_string(RESELLER_PANEL_HTML, GLOBAL_STYLES_AND_PARTICLES=GLOBAL_STYLES_AND_PARTICLES, reseller=reseller, plans=plans, purchases=purchases)

@app.route("/reseller/purchase", methods=["POST"])
@require_role('reseller')
def purchase_product():
    plan_id = int(request.form['plan_id'])
    reseller_id = session['user_id']
    
    conn = get_db()
    
    try:
        plan = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not plan:
            raise Exception("Plano não encontrado.")
        
        if not plan['download_link']:
             raise Exception("Produto indisponível (sem link). Contate o admin.")
            
        plan_cost = plan['cost']
        
        reseller = conn.execute("SELECT balance FROM users WHERE id = ?", (reseller_id,)).fetchone()
        current_balance = reseller['balance']
        
        if current_balance < plan_cost:
            raise Exception("Saldo insuficiente para comprar este produto.")
            
        new_balance = current_balance - plan_cost
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, reseller_id))
        
        purchase_id_ref = f"ID-{str(uuid.uuid4()).upper()[:8]}"
        
        conn.execute(
            "INSERT INTO purchases (reseller_id, plan_id, cost_paid, purchase_id_ref) VALUES (?, ?, ?, ?)",
            (reseller_id, plan_id, plan_cost, purchase_id_ref)
        )
        
        conn.commit()
        
        flash(f'Compra realizada com sucesso! ID: {purchase_id_ref}. O link de download está liberado no seu histórico.', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao comprar: {e}', 'error')
        
    finally:
        conn.close()
        
    return redirect(url_for('reseller_panel'))

# Rota para o DOWNLOAD (CORRIGIDA)
@app.route("/reseller/download/<int:purchase_id>")
@require_role('reseller')
def get_download_link(purchase_id):
    conn = get_db()
    
    purchase = conn.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
    
    if not purchase:
        flash("Compra não encontrada.", 'error')
        return redirect(url_for('reseller_panel'))
        
    if purchase['reseller_id'] != session['user_id']:
        flash("Acesso negado. Esta compra não é sua.", 'error')
        return redirect(url_for('reseller_panel'))
        
    plan = conn.execute("SELECT * FROM plans WHERE id = ?", (purchase['plan_id'],)).fetchone()
    conn.close()
    
    # CORREÇÃO DO ERRO 'AttributeError':
    download_link = plan['download_link'] # Acesso por chave
    
    if not download_link:
        flash("Erro: O link deste plano não foi encontrado. Contate o admin.", 'error')
        return redirect(url_for('reseller_panel'))

    # Redireciona o usuário para o link externo
    return redirect(download_link)

# --- 4. Iniciar a Aplicação (CORRIGIDO) ---
if __name__ == '__main__':
    # Inicializa o banco de dados (de forma segura)
    init_db() 
    
    print(f"\nServidor Flask (v4.1 - FINAL) rodando em http://127.0.0.1:5000")
    print("Logins de Teste:")
    print("  Admin:      trader / traderbr") # <-- ATUALIZADO
    print("  Revendedor: revendedor1 / revenda123 (Saldo: R$ 150.00)")
    
    # CORRIGIDO: Removido o argumento 'app_name'
    app.run(host="0.0.0.0", port=5000, debug=True)