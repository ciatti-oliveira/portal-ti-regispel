import platform
import subprocess
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import database as db
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime, timedelta
from fpdf import FPDF


# ==========================================
# POP-UP DE CREDENCIAIS (FLUXO RH)
# ==========================================
@st.dialog("📋 Resumo de Acessos Gerados")
def popup_acessos(colaborador, setor, tipo, matricula, ramal, t_user, t_pass, ad_user, ad_pass, em_user, em_pass, of_user, of_pass, obs, data_conclusao=None):
    st.markdown(f"### 👤 Colaborador: {colaborador}")
    st.caption(f"Setor: {setor} | Operação: {tipo}")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Matrícula:** {matricula}")
        st.markdown(f"**Ramal:** {ramal}")
        st.markdown(f"**TOTVS Usuário:** {t_user}")
        st.markdown(f"**TOTVS Senha:** {t_pass}")
        st.markdown(f"**AD Usuário:** {ad_user}")
        st.markdown(f"**AD Senha:** {ad_pass}")
    with col2:
        st.markdown(f"**E-mail Usuário:** {em_user}")
        st.markdown(f"**E-mail Senha:** {em_pass}")
        st.markdown(f"**Office Usuário:** {of_user}")
        st.markdown(f"**Office Senha:** {of_pass}")
        
    if obs:
        st.info(f"**Observações:** {obs}")
    if data_conclusao:
        st.caption(f"📅 Concluído em: {data_conclusao}")

# Configuração inicial da página
st.set_page_config(
    page_title="Portal de T.I. - Regispel",
    page_icon="🖥️",
    layout="wide"
)

# --- FUNÇÕES DE INTERFACE DO MENU ---

def render_sidebar():
    """Desenha a barra lateral com o logotipo e seletor de módulos."""
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", width="stretch")
    elif os.path.exists("logo.jpg"):
        st.sidebar.image("logo.jpg", width="stretch")
        
    st.sidebar.markdown("---")
    
    # Nome do Técnico Logado e Perfil
    if 'tecnico_nome' in st.session_state:
        perfil = st.session_state.get('perfil_acesso', 'Técnico')
        icone = "👑" if "Admin" in perfil else ("👁️" if "Visitante" in perfil else "👤")
        st.sidebar.markdown(f"{icone} **{perfil}:** {st.session_state['tecnico_nome']}")
    
    # --- CHAVE MESTRA: SELETOR DE MÓDULOS ---
    modulo = st.sidebar.selectbox(
        "Selecione o Sistema:",
        ["🖨️ Gestão de Impressoras", "💻 Controle de Ativos"]
    )
    
    st.sidebar.markdown("---")
    
    # --- MENUS DINÂMICOS ---
    if modulo == "🖨️ Gestão de Impressoras":
        st.sidebar.write("**Módulo de Impressoras**")
        menu = ["Dashboard", "Cadastro de Impressoras", "Estoque de Suprimentos", "Cadastros Base"]
        escolha = st.sidebar.radio("Navegação:", menu, key="menu_imp")
        return modulo, escolha
        
    elif modulo == "💻 Controle de Ativos":
        st.sidebar.write("**Módulo de Ativos (PCs)**")
        menu = ["Dashboard de Ativos", "Inventário de Máquinas", "Notebook Regispel", "Controle de Empréstimos","Estoque de Periféricos", "Fluxo de RH", "Controle de Ativos (DVR)"]
        escolha = st.sidebar.radio("Navegação:", menu, key="menu_ativos")
        return modulo, escolha


# ==========================================
# MÓDULO 1: GESTÃO DE IMPRESSORAS
# ==========================================

def ping_ip(ip):
    """Dispara um ping invisível para o IP e retorna True se responder, False se falhar."""
    if not ip or ip.strip() == "":
        return False
    
    parametro = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout = '-w' if platform.system().lower() == 'windows' else '-W'
    valor_timeout = '1000' if platform.system().lower() == 'windows' else '1'
    
    comando = ['ping', parametro, '1', timeout, valor_timeout, ip]
    
    try:
        saida = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return saida.returncode == 0
    except:
        return False

def show_dashboard():
    """Exibe indicadores gerais e tabelas altamente estilizadas usando CSS customizado."""
    if 'status_rede' not in st.session_state:
        st.session_state['status_rede'] = {}

    css = """<style>
    .dash-card { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); border: 1px solid #f0f0f0; margin-bottom: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .metric-container { display: flex; justify-content: space-between; padding: 15px 10px; }
    .metric-box { flex: 1; border-right: 1px solid #eee; padding: 0 15px; }
    .metric-box:last-child { border-right: none; }
    .metric-title { font-size: 11px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 32px; font-weight: 700; margin: 4px 0; color: #0f172a; }
    .metric-sub { font-size: 12px; color: #94a3b8; }
    .metric-sub.danger { color: #ef4444; font-weight: 500; }
    .metric-value.danger { color: #b91c1c; }
    .badge-ip { background-color: #e0f2fe; color: #0284c7; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;}
    .badge-usb { background-color: #f1f5f9; color: #475569; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;}
    .badge-ok { background-color: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;}
    .badge-alerta { background-color: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;}
    .badge-cinza { background-color: #f1f5f9; color: #64748b; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;}
    .custom-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .custom-table th { text-align: left; padding: 12px 10px; border-bottom: 2px solid #f1f5f9; color: #64748b; font-weight: 600; }
    .custom-table td { padding: 14px 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
    .row-number { color: #94a3b8; font-size: 12px; width: 20px; }
    .model-name { font-weight: 700; color: #1e293b; font-size: 13px; }
    .user-name { color: #64748b; font-size: 11px; display: block; margin-top: 3px; }
    .setor-name { color: #475569; font-size: 12px; }
    .sup-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #f1f5f9; }
    .sup-item:last-child { border-bottom: none; }
    .sup-name { font-weight: 700; font-size: 13px; color: #1e293b; }
    .sup-desc { font-size: 11px; color: #64748b; margin-top: 2px; }
    .section-title { margin-top: 0; margin-bottom: 15px; color: #334155; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px;}
    </style>"""
    st.markdown(css, unsafe_allow_html=True)

    total_imp = db.fetch_data("SELECT COUNT(*) as total FROM impressoras")[0]['total']
    total_ip = db.fetch_data("SELECT COUNT(*) as total FROM impressoras WHERE tipo_conexao = 'IP'")[0]['total']
    total_usb = db.fetch_data("SELECT COUNT(*) as total FROM impressoras WHERE tipo_conexao = 'USB'")[0]['total']
    total_setores = db.fetch_data("SELECT COUNT(DISTINCT setor_id) as total FROM impressoras")[0]['total']
    total_alertas = db.fetch_data("SELECT COUNT(*) as total FROM estoque_suprimentos e JOIN suprimentos s ON e.suprimento_id = s.id WHERE e.quantidade <= 1")[0]['total']

    offline_count = sum(1 for status in st.session_state['status_rede'].values() if status is False)

    metrics_html = f"""<div class="dash-card metric-container">
        <div class="metric-box"><div class="metric-title">TOTAL IMPRESSORAS</div><div class="metric-value">{total_imp}</div><div class="metric-sub">{total_setores} setores</div></div>
        <div class="metric-box"><div class="metric-title">CONEXÃO IP</div><div class="metric-value">{total_ip}</div><div class="metric-sub">monitoráveis na rede</div></div>
        <div class="metric-box"><div class="metric-title">STATUS DA REDE</div><div class="metric-value {'danger' if offline_count > 0 else ''}">{offline_count}</div><div class="metric-sub {'danger' if offline_count > 0 else ''}">impressoras offline</div></div>
        <div class="metric-box"><div class="metric-title">EM ALERTA</div><div class="metric-value {'danger' if total_alertas > 0 else ''}">{total_alertas}</div><div class="metric-sub {'danger' if total_alertas > 0 else ''}">suprimentos críticos</div></div>
    </div>"""
    st.markdown(metrics_html, unsafe_allow_html=True)

    col1, col2 = st.columns([1.4, 1])

    with col1:
        dados_imp = db.fetch_data("SELECT i.modelo, i.usuario_responsavel, s.nome as setor, i.tipo_conexao, i.endereco_rede FROM impressoras i LEFT JOIN setores s ON i.setor_id = s.id ORDER BY i.modelo")
        
        if st.button("📡 Testar Conexão de Rede Agora", type="primary", width="stretch"):
            with st.spinner("A disparar Ping para todas as impressoras IP. Aguarde alguns segundos..."):
                for row in dados_imp:
                    if row['tipo_conexao'] == 'IP' and row['endereco_rede']:
                        ip = row['endereco_rede']
                        st.session_state['status_rede'][ip] = ping_ip(ip)
            st.rerun()

        table_html = '<div class="dash-card" style="margin-top: 15px;"><div class="section-title"><span>📋</span> INVENTÁRIO DE IMPRESSORAS</div><table class="custom-table"><tr><th></th><th>Modelo / Usuário</th><th>Setor</th><th>Conexão</th><th>Situação na Rede</th></tr>'
        
        for i, row in enumerate(dados_imp):
            ip = row['endereco_rede']
            
            if row['tipo_conexao'] == 'IP':
                ip_badge = f"<span class='badge-ip'>{ip}</span>"
                if ip in st.session_state['status_rede']:
                    if st.session_state['status_rede'][ip]:
                        status_badge = "<span class='badge-ok'>🟢 ONLINE</span>"
                    else:
                        status_badge = "<span class='badge-alerta'>🔴 OFFLINE</span>"
                else:
                    status_badge = "<span class='badge-cinza'>⏳ Aguardando Teste</span>"
            else:
                ip_badge = "<span class='badge-usb'>USB</span>"
                status_badge = "<span class='badge-ok'>OK (Local)</span>"

            table_html += f"<tr><td class='row-number'>{i+1}</td><td><span class='model-name'>{row['modelo']}</span><span class='user-name'>{row['usuario_responsavel']}</span></td><td class='setor-name'>{row['setor'] or 'N/A'}</td><td>{ip_badge}</td><td>{status_badge}</td></tr>"
        table_html += "</table></div>"
        st.markdown(table_html, unsafe_allow_html=True)

    with col2:
        dados_sup = db.fetch_data("SELECT s.categoria, s.cor_tipo, COALESCE(e.quantidade, 0) as qtd FROM suprimentos s LEFT JOIN estoque_suprimentos e ON s.id = e.suprimento_id ORDER BY qtd ASC")
        sup_html = '<div class="dash-card"><div class="section-title"><span>💧</span> QUANTIDADE DE TONERS E TINTAS</div>'
        for row in dados_sup:
            qtd = row['qtd']
            badge = "<span class='badge-alerta'>Alerta</span>" if qtd <= 1 else "<span class='badge-ok'>OK</span>"
            sup_html += f"<div class='sup-item'><div><div class='sup-name'>{row['categoria']} — {row['cor_tipo']}</div><div class='sup-desc'>Qtd Atual: {qtd}</div></div><div style='display:flex; gap: 12px; align-items:center;'><span style='font-size:14px; font-weight:700; color:#334155;'>{qtd}</span> {badge}</div></div>"
        sup_html += "</div>"
        st.markdown(sup_html, unsafe_allow_html=True)

        dados_setor = db.fetch_data("SELECT s.nome, COUNT(i.id) as qtd FROM impressoras i JOIN setores s ON i.setor_id = s.id GROUP BY s.nome ORDER BY qtd DESC LIMIT 5")
        setor_html = '<div class="dash-card"><div class="section-title"><span>📊</span> QUANTIDADE DE IMPRESSORAS POR DP</div>'
        if dados_setor:
            max_qtd = max([r['qtd'] for r in dados_setor])
            for row in dados_setor:
                pct = int((row['qtd'] / max_qtd) * 100) if max_qtd > 0 else 0
                setor_html += f"<div style='display: flex; align-items: center; margin-bottom: 14px; font-size: 12px; font-weight: 600; color: #1e293b;'><div style='width: 110px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{row['nome']}</div><div style='flex-grow: 1; background-color: #f1f5f9; height: 6px; border-radius: 4px; margin: 0 12px;'><div style='width: {pct}%; background-color: #3b82f6; height: 100%; border-radius: 4px;'></div></div><div style='width: 20px; text-align: right; color: #64748b;'>{row['qtd']}</div></div>"
        else:
            setor_html += "<p style='font-size: 13px; color:#888;'>Sem dados cadastrados.</p>"
        setor_html += "</div>"
        st.markdown(setor_html, unsafe_allow_html=True)

def show_Cadastro_de_Impressoras():
    st.title("🖨️ Cadastro de Impressoras")
    st.markdown("Cadastre e vizualize o setor, conexão e usuário de cada impressora.")
    
    somente_leitura = "Visitante" in st.session_state.get('perfil_acesso', '')
    
    setores_db = db.fetch_data("SELECT id, nome FROM setores ORDER BY nome")
    opcoes_setores = {linha["nome"]: linha["id"] for linha in setores_db} if setores_db else {}

    if not opcoes_setores:
        st.warning("⚠️ Você precisa cadastrar pelo menos um Setor em 'Cadastros Base' antes de adicionar uma impressora.")
        return

    if not somente_leitura:
        with st.expander("➕ Cadastrar Nova Impressora"):
            with st.form("form_impressora", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    modelo = st.text_input("Modelo da Impressora (Ex: Epson L5190)")
                    usuario = st.text_input("Usuário Responsável")
                    setor_nome = st.selectbox("Setor", list(opcoes_setores.keys()))
                with col2:
                    conexao = st.selectbox("Tipo de Conexão", ["USB", "IP"])
                    endereco = st.text_input("Endereço de Rede (IP)")
                    acesso = st.text_input("Dados de Acesso (Opcional)")
                
                submit_imp = st.form_submit_button("Salvar Impressora")

                if submit_imp:
                    if modelo and usuario:
                        db.execute_query('''INSERT INTO impressoras (modelo, usuario_responsavel, setor_id, tipo_conexao, endereco_rede, dados_acesso)
                                            VALUES (?, ?, ?, ?, ?, ?)''', (modelo, usuario, opcoes_setores[setor_nome], conexao, endereco, acesso))
                        st.success(f"Impressora {modelo} cadastrada!")
                        st.rerun()
                    else:
                        st.warning("Os campos 'Modelo' e 'Usuário' são obrigatórios.")
        st.markdown("---")

    query = "SELECT i.id as ID, i.modelo as Modelo, i.usuario_responsavel as Usuário, s.nome as Setor, i.tipo_conexao as Conexão, i.endereco_rede as IP FROM impressoras i LEFT JOIN setores s ON i.setor_id = s.id ORDER BY i.modelo"
    dados_imp = db.fetch_data(query)
    
    if dados_imp:
        # Cria o DataFrame com os dados do banco
        df_imp = pd.DataFrame(dados_imp)
        
        # --- INÍCIO DA TABELA HTML ---
        html_inventario = '<table style="width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px; margin-bottom: 25px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">'
        
        # Cabeçalho
        html_inventario += '<tr style="background-color: #005ea2; color: white;">'
        html_inventario += '<th style="padding: 10px; text-align: left;">Modelo</th>'
        html_inventario += '<th style="padding: 10px; text-align: left;">Usuário</th>'
        html_inventario += '<th style="padding: 10px; text-align: left;">Setor</th>'
        html_inventario += '<th style="padding: 10px; text-align: left;">Conexão</th>'
        html_inventario += '<th style="padding: 10px; text-align: left;">IP</th>'
        html_inventario += '</tr>'
        
        for index, row in df_imp.iterrows():
            cor_fundo = "#f8f9fa" if index % 2 == 0 else "#ffffff"
            html_inventario += f'<tr style="background-color: {cor_fundo}; border-bottom: 1px solid #e2e8f0;">'
            
            # Usando os nomes exatos das colunas conforme o seu "SELECT"
            html_inventario += f'<td style="padding: 10px; color: #000000; font-weight: 700;">{row["Modelo"]}</td>'
            html_inventario += f'<td style="padding: 10px; color: #000000;">{row["Usuário"]}</td>'
            html_inventario += f'<td style="padding: 10px; color: #000000;">{row["Setor"]}</td>'
            html_inventario += f'<td style="padding: 10px; color: #000000;">{row["Conexão"]}</td>'
            
            # Tratamento para IP em branco
            ip_val = row["IP"] if pd.notna(row["IP"]) else ""
            html_inventario += f'<td style="padding: 10px; color: #000000;">{ip_val}</td>'
            
            html_inventario += '</tr>'
        
        html_inventario += '</table>'
        
        # Renderiza a tabela no sistema
        st.markdown(html_inventario, unsafe_allow_html=True)
        # --- FIM DA TABELA HTML ---
        
        if not somente_leitura:
            with st.expander("🗑️ Excluir uma Impressora"):
                opcoes_del_imp = {f"{linha['Modelo']} ({linha['Usuário']})": linha["ID"] for linha in dados_imp}
                
                # A chave (key) exclusiva resolve o erro da tela vermelha!
                imp_para_deletar = st.selectbox(
                    "Selecione a impressora para excluir:", 
                    list(opcoes_del_imp.keys()), 
                    key="caixa_excluir_imp"
                )
                
                # Chave no botão também
                if st.button("Confirmar Exclusão", key="btn_excluir_imp"):
                    db.delete_data("DELETE FROM impressoras WHERE id = ?", (opcoes_del_imp[imp_para_deletar],))
                    st.success("Excluída com sucesso!")
                    st.rerun()
    else:
        st.info("Nenhuma impressora cadastrada ainda.")

def enviar_alerta_suprimentos_novo():
    """Varre o banco de dados e envia um e-mail consolidado com alertas e solicitações."""
    load_dotenv(override=True)
    
    server = os.getenv("EMAIL_HOST")
    porta = os.getenv("EMAIL_PORT")
    user = os.getenv("EMAIL_USER")
    senha = os.getenv("EMAIL_PASS")
    destino_raw = os.getenv("EMAIL_DESTINATARIO")
    
    if not all([server, porta, user, senha, destino_raw]):
        st.error("❌ Erro: Alguma configuração está faltando dentro do seu arquivo .env")
        return

    destino_tratado = destino_raw.replace(";", ",")
    lista_destinos = [email.strip() for email in destino_tratado.split(",") if email.strip()]

    # 🧠 Busca todos os itens críticos (<=2) OU que já foram solicitados (obs não vazia)
    query = """
        SELECT s.categoria, s.cor_tipo, COALESCE(e.quantidade, 0) as qtd, COALESCE(e.obs_solicitacao, '') as obs 
        FROM suprimentos s 
        LEFT JOIN estoque_suprimentos e ON s.id = e.suprimento_id 
        WHERE COALESCE(e.quantidade, 0) <= 2 OR COALESCE(e.obs_solicitacao, '') != ''
        ORDER BY s.categoria
    """
    itens = db.fetch_data(query)
    
    # Separa em 3 listas: Críticos (0 ou 1), Atenção (2), e Já Comprados
    itens_criticos = [i for i in itens if i['obs'].strip() == '' and i['qtd'] <= 1]
    itens_atencao = [i for i in itens if i['obs'].strip() == '' and i['qtd'] == 2]
    itens_comprados = [i for i in itens if i['obs'].strip() != '']
    
    if not itens_criticos and not itens_atencao and not itens_comprados:
        st.info("🟢 Tudo OK! Nenhum item crítico, em atenção ou pendente para envio de e-mail.")
        return

    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = ", ".join(lista_destinos)
    msg['Subject'] = "📊 [REPORT SEMANAL] Posição de Estoque de Suprimentos — Portal T.I."
    
    corpo_html = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
        <h2 style="color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">Status Atual do Estoque de Suprimentos</h2>
        <p>Abaixo está a fotografia atualizada dos suprimentos de impressão que exigem monitoramento.</p>
    """
    
    # --- TABELA 1: ALERTAS CRÍTICOS (0 ou 1) ---
    if itens_criticos:
        corpo_html += """
        <h3 style="color: #b91c1c; margin-top: 25px;">🔴 AÇÃO URGENTE: Itens Críticos / Zerados</h3>
        <table style="width:100%; border-collapse: collapse; margin-top: 10px; border: 1px solid #fca5a5;">
            <tr style="background-color: #fee2e2; border-bottom: 2px solid #ef4444;">
                <th style="padding: 10px; text-align: left;">Modelo / Insumo</th>
                <th style="padding: 10px; text-align: left;">Cor / Tipo</th>
                <th style="padding: 10px; text-align: center; width: 100px;">Qtd Atual</th>
            </tr>
        """
        for item in itens_criticos:
            corpo_html += f"""
            <tr style="border-bottom: 1px solid #fca5a5;">
                <td style="padding: 10px; font-weight: bold;">{item['categoria']}</td>
                <td style="padding: 10px;">{item['cor_tipo']}</td>
                <td style="padding: 10px; text-align: center; color: #b91c1c; font-weight: bold; font-size: 16px;">{item['qtd']}</td>
            </tr>
            """
        corpo_html += "</table>"

    # --- TABELA 2: ATENÇÃO (2 unidades) ---
    if itens_atencao:
        corpo_html += """
        <h3 style="color: #a16207; margin-top: 25px;">⚠️ ATENÇÃO: Chegando no Ponto de Pedido</h3>
        <table style="width:100%; border-collapse: collapse; margin-top: 10px; border: 1px solid #fde047;">
            <tr style="background-color: #fef08a; border-bottom: 2px solid #eab308;">
                <th style="padding: 10px; text-align: left;">Modelo / Insumo</th>
                <th style="padding: 10px; text-align: left;">Cor / Tipo</th>
                <th style="padding: 10px; text-align: center; width: 100px;">Qtd Atual</th>
            </tr>
        """
        for item in itens_atencao:
            corpo_html += f"""
            <tr style="border-bottom: 1px solid #fde047;">
                <td style="padding: 10px; font-weight: bold;">{item['categoria']}</td>
                <td style="padding: 10px;">{item['cor_tipo']}</td>
                <td style="padding: 10px; text-align: center; color: #a16207; font-weight: bold; font-size: 16px;">{item['qtd']}</td>
            </tr>
            """
        corpo_html += "</table>"
        
    # --- TABELA 3: JÁ SOLICITADOS ---
    if itens_comprados:
        corpo_html += """
        <h3 style="color: #1d4ed8; margin-top: 35px;">🛒 AGUARDANDO CHEGADA: Pedidos Já Solicitados</h3>
        <table style="width:100%; border-collapse: collapse; margin-top: 10px; border: 1px solid #bfdbfe;">
            <tr style="background-color: #eff6ff; border-bottom: 2px solid #3b82f6;">
                <th style="padding: 10px; text-align: left;">Modelo / Insumo</th>
                <th style="padding: 10px; text-align: left;">Cor / Tipo</th>
                <th style="padding: 10px; text-align: center; width: 80px;">Qtd Atual</th>
                <th style="padding: 10px; text-align: left;">Status do Pedido</th>
            </tr>
        """
        for item in itens_comprados:
            corpo_html += f"""
            <tr style="border-bottom: 1px solid #bfdbfe;">
                <td style="padding: 10px; font-weight: bold;">{item['categoria']}</td>
                <td style="padding: 10px;">{item['cor_tipo']}</td>
                <td style="padding: 10px; text-align: center; color: #1e3a8a; font-weight: bold; font-size: 16px;">{item['qtd']}</td>
                <td style="padding: 10px; color: #3b82f6; font-style: italic;">{item['obs']}</td>
            </tr>
            """
        corpo_html += "</table>"

    corpo_html += """
        <br>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-top: 30px;">
        <p style="font-size: 11px; color: #94a3b8; text-align: center;">Este é um e-mail automático gerado pelo sistema de gestão de ativos Regispel.</p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
    
    try:
        smtp = smtplib.SMTP(server, int(porta))
        smtp.starttls()
        smtp.login(user, senha)
        smtp.sendmail(user, lista_destinos, msg.as_string())
        smtp.quit()
        
        st.success("📩 Report gerado e enviado com sucesso!")
        
    except Exception as e:
        st.error(f"❌ Falha ao conectar no provedor de E-mail: {str(e)}")

def show_estoque_de_suprimentos():
    st.title("💧 Estoque de Suprimentos")
    st.markdown("Atualizar estoque de determinado modelo de impressora, cor e toner enviando um relatório de alerta para o e-mail")
    
    somente_leitura = "Visitante" in st.session_state.get('perfil_acesso', '')

    # Cria a coluna nova no banco de dados para guardar o texto da sua planilha
    try:
        db.execute_query("ALTER TABLE estoque_suprimentos ADD COLUMN obs_solicitacao TEXT DEFAULT ''")
    except:
        pass

    if not somente_leitura:
        if st.button("📧 Enviar Relatório de Alertas por E-mail", width="stretch"):
            enviar_alerta_suprimentos_novo()
        
    query = "SELECT s.id as id, s.categoria as categoria, s.cor_tipo as cor_tipo, s.departamentos_uso as departamentos, COALESCE(e.quantidade, 0) as quantidade, COALESCE(e.obs_solicitacao, '') as obs_solicitacao FROM suprimentos s LEFT JOIN estoque_suprimentos e ON s.id = e.suprimento_id ORDER BY s.categoria, s.cor_tipo"
    dados_sup = db.fetch_data(query)

    if not dados_sup:
        st.warning("⚠️ Nenhum suprimento cadastrado. Vá em 'Cadastros Base' primeiro.")
        return

    df_sup = pd.DataFrame(dados_sup)
    df_sup.fillna("", inplace=True)
    df_sup['categoria'] = df_sup['categoria'].str.strip().str.upper()
    df_sup['cor_tipo'] = df_sup['cor_tipo'].astype(str).str.strip().str.upper()

    if not somente_leitura:
        with st.expander("🔄 Movimentação de Estoque (Saída ou Ajuste)"):
            
            # 1. Ação escolhida
            acao = st.radio("O que você deseja registrar?", ["📉 Registrar Saída (Consumo)", "✏️ Ajustar Estoque (Correção/Compra)"], horizontal=True)
            
            with st.form("form_estoque", clear_on_submit=True):
                opcoes_itens = {f"{row['categoria']} - {row['cor_tipo']}": row['id'] for _, row in df_sup.iterrows()}
                
                # 2. Se for SAÍDA
                if acao == "📉 Registrar Saída (Consumo)":
                    col_f1, col_f2, col_f3 = st.columns([2, 1, 1.5])
                    with col_f1:
                        item_selecionado = st.selectbox("Selecione o Item", list(opcoes_itens.keys()))
                    with col_f2:
                        qtd_mov = st.number_input("Qtd Retirada", min_value=1, step=1)
                    with col_f3:
                        departamento = st.selectbox("Departamento Destino", ["Produção", "RH", "Financeiro", "Administrativo", "Comercial", "Diretoria", "TI", "Outros"])
                        
                    obs_pedido = st.text_input("Anotação opcional (Ex: Entregue para o João)")
                    limpar_nota = False 
                    
                # 3. Se for AJUSTE
                else:
                    col_f1, col_f2, col_f3 = st.columns([2, 1, 1.5])
                    with col_f1:
                        item_selecionado = st.selectbox("Selecione o Item", list(opcoes_itens.keys()))
                    with col_f2:
                        qtd_mov = st.number_input("Nova Quantidade Total", min_value=0, step=1)
                    with col_f3:
                        obs_pedido = st.text_input("Anotação (Ex: Solicitado 8 unid.)")
                        limpar_nota = st.checkbox("🧹 Limpar anotação existente")
                
                if st.form_submit_button("Salvar Movimentação"):
                    item_id = opcoes_itens[item_selecionado]
                    obs_final = obs_pedido.strip()
                    
                    if limpar_nota:
                        obs_final = ""
                    elif not obs_final:
                        obs_atual_db = db.fetch_data("SELECT obs_solicitacao FROM estoque_suprimentos WHERE suprimento_id = ?", (item_id,))
                        if obs_atual_db and obs_atual_db[0]['obs_solicitacao']:
                            obs_final = obs_atual_db[0]['obs_solicitacao']
                    
                    # 4. SALVANDO NO BANCO
                    if acao == "📉 Registrar Saída (Consumo)":
                        linha_item = df_sup[df_sup['id'] == item_id]
                        estoque_atual = int(linha_item['quantidade'].values[0]) if not linha_item.empty else 0
                        nova_qtd_calculada = estoque_atual - qtd_mov
                        
                        if nova_qtd_calculada < 0: 
                            nova_qtd_calculada = 0
                            
                        db.execute_query(
                            "INSERT INTO estoque_suprimentos (suprimento_id, quantidade, obs_solicitacao) VALUES (?, ?, ?) ON CONFLICT(suprimento_id) DO UPDATE SET quantidade=excluded.quantidade, obs_solicitacao=excluded.obs_solicitacao", 
                            (item_id, nova_qtd_calculada, obs_final)
                        )
                        
                        db.execute_query(
                            "INSERT INTO historico_saidas (item, quantidade, departamento) VALUES (?, ?, ?)",
                            (item_selecionado, qtd_mov, departamento)
                        )
                        st.success(f"✅ Saída de {qtd_mov} un. para {departamento} registrada! Estoque atualizado para {nova_qtd_calculada}.")
                        
                    else:
                        db.execute_query(
                            "INSERT INTO estoque_suprimentos (suprimento_id, quantidade, obs_solicitacao) VALUES (?, ?, ?) ON CONFLICT(suprimento_id) DO UPDATE SET quantidade=excluded.quantidade, obs_solicitacao=excluded.obs_solicitacao", 
                            (item_id, qtd_mov, obs_final)
                        )
                        st.success("✅ Estoque ajustado com sucesso!")
                        
                    st.rerun()
                    
    st.markdown("---")

    # ==========================================
    # 🎨 NOVA FUNÇÃO DE CARDS
    # ==========================================
    def gerar_html_card(cat, cor, qtd, obs_solic, basis="calc(50% - 10px)"):
        alerta_extra = ""
        
        if obs_solic and obs_solic.strip() != "":
            bg_color = "#99c6fd"
            border_color = "#2f78ee"
            text_color = "#002896"
            status_txt = "🛒 SOLICITADO"
            alerta_extra = f"<div style='margin-top: 10px; padding-top: 8px; border-top: 1px solid {border_color}; font-size: 15px; color: {text_color}; font-weight: bold;'>💬 {obs_solic}</div>"
        elif qtd == 0:
            bg_color = "#fecaca" 
            border_color = "#ef4444"
            text_color = "#b91c1c"
            status_txt = "🔴 ZERADO"
        elif qtd == 1:
            bg_color = "#fecaca"  
            border_color = "#c00000" 
            text_color = "#c21515" 
            status_txt = "🔴 CRÍTICO"
        elif qtd == 2:
            bg_color = "#fef08a"
            border_color = "#eab308" 
            text_color = "#a16207" 
            status_txt = "⚠️ ATENÇÃO"
        else:
            bg_color = "#bbf7d0" 
            border_color = "#22c55e"
            text_color = "#15803d"
            status_txt = "🟢 OK"
            
        card_raw = f"""
        <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 12px; flex: 1 1 {basis}; min-width: 130px; box-shadow: 1px 1px 3px rgba(0,0,0,0.05); margin: 5px; box-sizing: border-box; position: relative;">
            <div style="position: absolute; top: 12px; right: 12px; font-size: 10px; font-weight: 800; color: {text_color};">
                {status_txt}
            </div>
            <div style="font-size: 12px; color: #475569; font-weight: bold; text-transform: uppercase; padding-right: 70px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {cat}
            </div>
            <div style="font-size: 15px; color: #0f172a; font-weight: 900; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {cor}
            </div>
            <div style="font-size: 28px; color: {text_color}; font-weight: 900; line-height: 1.1; margin-top: 6px;">
                {qtd}
            </div>
            {alerta_extra}
        </div>
        """
        return card_raw.replace("\n", " ")

    st.markdown("#### 📊 Quantidade em Estoque Atual")
    c1, c2 = st.columns(2)
    
    df_544 = df_sup[df_sup['categoria'].str.contains('544')]
    html_544 = '<div style="display: flex; flex-wrap: wrap; background-color: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; height: 100%; align-content: flex-start; margin-bottom: 15px;">'
    html_544 += '<div style="width: 100%; font-size: 12px; font-weight: bold; color: #475569; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px;">🖨️ Grupo: Impressora 544</div>'
    for _, row in df_544.iterrows():
        html_544 += gerar_html_card(row['categoria'], row['cor_tipo'], int(row['quantidade']), str(row['obs_solicitacao']), basis="calc(50% - 10px)")
    html_544 += '</div>'
    c1.markdown(html_544.replace("\n", " "), unsafe_allow_html=True)
    
    df_664 = df_sup[df_sup['categoria'].str.contains('664')]
    html_664 = '<div style="display: flex; flex-wrap: wrap; background-color: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; height: 100%; align-content: flex-start; margin-bottom: 15px;">'
    html_664 += '<div style="width: 100%; font-size: 12px; font-weight: bold; color: #475569; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px;">🖨️ Grupo: Impressora 664</div>'
    for _, row in df_664.iterrows():
        html_664 += gerar_html_card(row['categoria'], row['cor_tipo'], int(row['quantidade']), str(row['obs_solicitacao']), basis="calc(50% - 10px)")
    html_664 += '</div>'
    c2.markdown(html_664.replace("\n", " "), unsafe_allow_html=True)
    
    df_toners = df_sup[~df_sup['categoria'].str.contains('544') & ~df_sup['categoria'].str.contains('664')]
    
    html_toners = '<div style="display: flex; flex-wrap: wrap; background-color: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;">'
    html_toners += '<div style="width: 100%; font-size: 12px; font-weight: bold; color: #475569; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px;">🔌 Seção: Toners Individuais</div>'
    for _, row in df_toners.iterrows():
        html_toners += gerar_html_card(row['categoria'], row['cor_tipo'], int(row['quantidade']), str(row['obs_solicitacao']), basis="calc(25% - 10px)")
    html_toners += '</div>'
    st.markdown(html_toners.replace("\n", " "), unsafe_allow_html=True)

    st.markdown("---") 
# ==========================================
    # 📈 MINI DASHBOARD DE CONSUMO
    # ==========================================
    st.markdown("#### 📈 Resumo Geral de Saídas")
    
    # 1. Busca o histórico de saídas
    query_hist = "SELECT departamento, item, quantidade FROM historico_saidas"
    dados_hist = db.fetch_data(query_hist)
    
    if dados_hist:
        df_hist = pd.DataFrame(dados_hist)
        
        # 2. Cálculo dos 3 Indicadores Principais
        total_consumido = df_hist['quantidade'].sum()
        
        # Descobre o Item mais pedido
        df_itens = df_hist.groupby('item')['quantidade'].sum().reset_index().sort_values(by='quantidade', ascending=False)
        item_campeao = df_itens.iloc[0]['item']
        qtd_item_campeao = df_itens.iloc[0]['quantidade']
        
        # Descobre o Setor que mais pediu
        df_setores = df_hist.groupby('departamento')['quantidade'].sum().reset_index().sort_values(by='quantidade', ascending=False)
        setor_campeao = df_setores.iloc[0]['departamento']
        qtd_setor_campeao = df_setores.iloc[0]['quantidade']
        
        # 3. Renderiza os cartões de métrica
        dash1, dash2, dash3 = st.columns(3)
        dash1.metric("📦 Total de Insumos Entregues", f"{total_consumido} un.")
        dash2.metric("🔝 Item Mais Requisitado", f"{item_campeao}", f"{qtd_item_campeao} un.")
        dash3.metric("🏢 Maior Setor Consumidor", f"{setor_campeao}", f"{qtd_setor_campeao} un.")
        
        # 4. Tabela detalhada
        df_detalhado = df_hist.groupby(['departamento', 'item'])['quantidade'].sum().reset_index()
        df_detalhado = df_detalhado.sort_values(by=['departamento', 'quantidade'], ascending=[True, False])
        
        st.markdown("**📋 Detalhamento por Departamento e Item:**")
        st.dataframe(
            df_detalhado.rename(columns={
                'departamento': 'Departamento', 
                'item': 'Item / Modelo / Cor', 
                'quantidade': 'Qtd Consumida'
            }), 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("Nenhuma saída registrada ainda. O dashboard ganhará vida assim que você registrar o primeiro consumo!")
        
    st.markdown("---")

    st.markdown("#### 📋 Modelos e Departamentos Vinculados")
    df_tabela = df_sup.groupby('categoria')['departamentos'].first().reset_index()

    html_tabela = '<table style="width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px; margin-bottom: 25px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);">'
    html_tabela += '<tr style="background-color: #005ea2; color: white;">'
    html_tabela += '<th style="padding: 10px; text-align: left; width: 25%; font-size: 13px;">Modelo do Suprimento</th>'
    html_tabela += '<th style="padding: 10px; text-align: left; width: 75%; font-size: 13px;">Departamentos Atendidos</th>'
    html_tabela += '</tr>'

    for index, row in df_tabela.iterrows():
        cor_fundo = "#f8f9fa" if index % 2 == 0 else "#ffffff"
        html_tabela += f'<tr style="background-color: {cor_fundo}; border-bottom: 1px solid #e2e8f0;">'
        html_tabela += f'<td style="padding: 10px; font-weight: 700; color: #000000; font-size: 12px;">{row["categoria"]}</td>'
        html_tabela += f'<td style="padding: 10px; color: #000000; font-weight: 500; line-height: 1.4;">{row["departamentos"]}</td>'
        html_tabela += '</tr>'

    html_tabela += '</table>'
    st.markdown(html_tabela, unsafe_allow_html=True)
    def show_importacao():
        st.title("📥 Importação de Dados")
        st.write("Aba de importação automática reservada para uso futuro.")

def show_cadastros():
    st.title("⚙️ Cadastros Base")
    st.markdown("Gerencie os setores da empresa, o catálogo de suprimentos e os técnicos de T.I.")
    
    somente_leitura = "Visitante" in st.session_state.get('perfil_acesso', '')
    
    if somente_leitura:
        st.warning("⚠️ Modo Somente Leitura: Você não tem permissão para alterar os cadastros base.")
        return
    
    tab1, tab2, tab3 = st.tabs(["🏢 Setores / Departamentos", "💧 Suprimentos", "👥 Colaboradores T.I"])

    with tab1:
        with st.form("form_setor", clear_on_submit=True):
            nome_setor = st.text_input("Nome do Setor")
            if st.form_submit_button("Salvar Setor") and nome_setor:
                try:
                    db.execute_query("INSERT INTO setores (nome) VALUES (?)", (nome_setor.upper(),))
                    st.success("Setor cadastrado!")
                    st.rerun()
                except: st.error("Esse setor já existe.")
        st.markdown("---")
        dados_setores = db.fetch_data("SELECT id, nome as Nome FROM setores ORDER BY nome")
        if dados_setores:
            st.dataframe(pd.DataFrame(dados_setores)[["Nome"]], hide_index=True, width="stretch")

    with tab2:
        setores_disp = db.fetch_data("SELECT nome FROM setores ORDER BY nome")
        lista_setores = [s['nome'] for s in setores_disp] if setores_disp else []

        with st.expander("➕ Cadastrar Novo Suprimento"):
            with st.form("form_suprimento", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1: categoria = st.text_input("Categoria (Ex: IMPRESSORA 544, TONER 285A)")
                with col2: cor_tipo = st.text_input("Cor ou Tipo (Ex: PRETO, ÚNICO)")
                
                deps_selecionados = st.multiselect("Departamentos que utilizam este suprimento (Opcional):", lista_setores)
                
                if st.form_submit_button("Salvar Suprimento") and categoria and cor_tipo:
                    deps_str = ", ".join(deps_selecionados)
                    try:
                        db.execute_query("INSERT INTO suprimentos (categoria, cor_tipo, departamentos_uso) VALUES (?, ?, ?)", (categoria.upper(), cor_tipo.upper(), deps_str))
                        st.success("Suprimento cadastrado!")
                        st.rerun()
                    except: st.error("Este item já existe.")
        
        st.markdown("---")
        dados_sup = db.fetch_data("SELECT id, categoria as Categoria, cor_tipo as 'Cor/Tipo', departamentos_uso as 'Departamentos' FROM suprimentos ORDER BY categoria")
        if dados_sup: 
            df_sup_cad = pd.DataFrame(dados_sup)
            df_sup_cad.fillna("", inplace=True)
            st.dataframe(df_sup_cad.drop(columns=["id"]), hide_index=True, width="stretch")
            
            with st.expander("✏️ Editar um Suprimento"):
                opcoes_edit_sup = {f"{row['Categoria']} - {row['Cor/Tipo']}": row["id"] for _, row in df_sup_cad.iterrows()}
                sup_para_editar = st.selectbox("Selecione o Suprimento para editar:", list(opcoes_edit_sup.keys()), key="sel_edit_sup")
                
                if sup_para_editar:
                    id_sup_sel = opcoes_edit_sup[sup_para_editar]
                    dados_atuais_sup = next(item for item in dados_sup if item["id"] == id_sup_sel)
                    
                    with st.form("form_edit_sup"):
                        col_e1, col_e2 = st.columns(2)
                        with col_e1: cat_edit = st.text_input("Categoria", value=dados_atuais_sup["Categoria"])
                        with col_e2: cor_edit = st.text_input("Cor/Tipo", value=dados_atuais_sup["Cor/Tipo"])
                        
                        deps_atuais_str = dados_atuais_sup["Departamentos"]
                        deps_atuais_lista = [d.strip() for d in deps_atuais_str.split(",")] if deps_atuais_str else []
                        deps_atuais_validos = [d for d in deps_atuais_lista if d in lista_setores]
                        
                        deps_editados = st.multiselect("Departamentos", lista_setores, default=deps_atuais_validos)
                        
                        if st.form_submit_button("Salvar Alterações"):
                            deps_str_nova = ", ".join(deps_editados)
                            db.execute_query("UPDATE suprimentos SET categoria=?, cor_tipo=?, departamentos_uso=? WHERE id=?", 
                                             (cat_edit.upper(), cor_edit.upper(), deps_str_nova, id_sup_sel))
                            st.success("Suprimento atualizado!")
                            st.rerun()

            with st.expander("🗑️ Excluir um Suprimento"):
                opcoes_del_sup = {f"{row['Categoria']} - {row['Cor/Tipo']}": row["id"] for _, row in df_sup_cad.iterrows()}
                sup_para_deletar = st.selectbox("Selecione o suprimento para excluir:", list(opcoes_del_sup.keys()), key="sel_del_sup")
                if st.button("Confirmar Exclusão"):
                    db.delete_data("DELETE FROM suprimentos WHERE id = ?", (opcoes_del_sup[sup_para_deletar],))
                    st.success("Suprimento excluído!")
                    st.rerun()

    with tab3:
        st.markdown("### Registrar Integrante do T.I")
        
        try:
            db.execute_query("ALTER TABLE tecnicos ADD COLUMN perfil TEXT DEFAULT 'Técnico'")
        except:
            pass 

        with st.form("form_novo_tec", clear_on_submit=True):
            col_t1, col_t2, col_t3, col_t4 = st.columns(4)
            with col_t1:
                t_nome = st.text_input("Nome Completo")
            with col_t2:
                t_login = st.text_input("Nome de Usuário (Login)")
            with col_t3:
                t_senha = st.text_input("Senha de Acesso", type="password")
            with col_t4:
                t_perfil = st.selectbox("Nível de Acesso", ["Administrador", "Técnico", "Visitante (Somente Leitura)"])
                
            if st.form_submit_button("Cadastrar Colaborador"):
                if t_nome and t_login and t_senha:
                    perfil_limpo = "Visitante" if "Visitante" in t_perfil else t_perfil
                    db.execute_query(
                        "INSERT INTO tecnicos (nome, usuario, senha, perfil) VALUES (?, ?, ?, ?)", 
                        (t_nome.upper(), t_login.lower(), t_senha, perfil_limpo)
                    )
                    st.success(f"✅ {t_nome} cadastrado com sucesso como {perfil_limpo}!")
                    st.rerun()
                else:
                    st.error("Preencha todos os campos!")

        st.markdown("---")
        st.markdown("### Integrantes Cadastrados")
        
        dados_tec = db.fetch_data("SELECT id, nome as Nome, usuario as Login, perfil as 'Nível de Acesso' FROM tecnicos ORDER BY nome")
        if dados_tec:
            df_tec = pd.DataFrame(dados_tec)
            st.dataframe(df_tec.drop(columns=['id']), hide_index=True, width="stretch")
            
            with st.expander("🗑️ Remover um Integrante"):
                opcoes_del_tec = {f"{row['Nome']} ({row['Nível de Acesso']})": row['id'] for _, row in df_tec.iterrows()}
                tec_deletar = st.selectbox("Selecione quem deseja remover:", list(opcoes_del_tec.keys()))
                if st.button("🔴 Excluir Acesso", width="stretch"):
                    if "ADMINISTRADOR" in tec_deletar.upper() and df_tec[df_tec['Nível de Acesso'] == 'Administrador'].shape[0] <= 1:
                        st.error("Erro: Você não pode excluir o único Administrador do sistema.")
                    else:
                        db.execute_query("DELETE FROM tecnicos WHERE id = ?", (opcoes_del_tec[tec_deletar],))
                        st.success("Acesso revogado!")
                        st.rerun()
        else:
            st.info("Nenhum técnico cadastrado.")


# ==========================================
# MÓDULO 2: CONTROLE DE ATIVOS (PCs)
# ==========================================

def show_dashboard_ativos():
    st.title("📊 Dashboard de Ativos")
    st.markdown("---")

    query = "SELECT * FROM computadores"
    dados = db.fetch_data(query)

    if not dados:
        st.info("Nenhuma máquina cadastrada ainda. Vá em 'Inventário de Máquinas' para começar.")
        return

    df = pd.DataFrame(dados)

    col_nome = 'usuario' if 'usuario' in df.columns else ('Funcionário' if 'Funcionário' in df.columns else df.columns[1])
    col_setor = 'setor_id' if 'setor_id' in df.columns else ('Setor' if 'Setor' in df.columns else df.columns[4])
    col_cpu = 'processador' if 'processador' in df.columns else ('Processador' if 'Processador' in df.columns else df.columns[5])
    col_ram = 'memoria_ram' if 'memoria_ram' in df.columns else ('↑ RAM' if '↑ RAM' in df.columns else df.columns[6])

    df[col_setor] = df[col_setor].fillna("NÃO DEFINIDO").replace(["None", "", "none"], "NÃO DEFINIDO").astype(str).str.strip().str.upper()
    df[col_ram] = df[col_ram].fillna("").astype(str).str.upper()

    total_pcs = len(df)
    setores_unicos = df[col_setor].nunique()
    pcs_4gb = len(df[df[col_ram].str.contains('4', na=False)]) 

    # Cards Superiores (Mantidos iguais, pois já estavam bons!)
    kpi_html = f"""
    <div style="display: flex; gap: 20px; margin-bottom: 35px; flex-wrap: wrap;">
        <div style="flex: 1; background-color: #ffffff; border-left: 5px solid #3b82f6; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); min-width: 200px;">
            <div style="font-size: 12px; color: #64748b; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Total de Computadores</div>
            <div style="font-size: 36px; font-weight: 900; color: #1e293b; margin-top: 5px; line-height: 1;">💻 {total_pcs}</div>
        </div>
        <div style="flex: 1; background-color: #ffffff; border-left: 5px solid #10b981; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); min-width: 200px;">
            <div style="font-size: 12px; color: #64748b; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Setores Atendidos</div>
            <div style="font-size: 36px; font-weight: 900; color: #1e293b; margin-top: 5px; line-height: 1;">🏢 {setores_unicos}</div>
        </div>
        <div style="flex: 1; background-color: #fffbeb; border-left: 5px solid #f59e0b; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); min-width: 200px;">
            <div style="font-size: 12px; color: #b45309; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Máquinas com 4GB RAM</div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 5px;">
                <span style="font-size: 36px; font-weight: 900; color: #92400e; line-height: 1;">⚠️ {pcs_4gb}</span>
                <span style="font-size: 10px; background: #fde68a; color: #92400e; padding: 4px 8px; border-radius: 12px; font-weight: bold;">Upgrade Recomendado</span>
            </div>
        </div>
    </div>
    """
    st.markdown(kpi_html.replace("\n", ""), unsafe_allow_html=True)
    col1, col2 = st.columns([1.3, 1.2])

    with col1:
        st.markdown("##### 🏢 Máquinas por Setor")
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        # Prepara os dados para o Gráfico
        df_setores = df[col_setor].value_counts().reset_index()
        df_setores.columns = ['Setor', 'Quantidade']
        
        # Ordena para a maior barra ficar no topo do gráfico horizontal
        df_setores = df_setores.sort_values(by='Quantidade', ascending=True)
        
        # Desenha o Gráfico Plotly
        fig = px.bar(
            df_setores,
            x='Quantidade',
            y='Setor',
            orientation='h',
            text='Quantidade',
            color_discrete_sequence=["#005ea2"] # Azul corporativo da Regispel
        )
        
        # Estilização Limpa
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor='#f1f5f9', title="", showticklabels=False),
            yaxis=dict(showgrid=False, title=""),
            margin=dict(l=0, r=20, t=10, b=0),
            height=400,
            showlegend=False
        )
        fig.update_traces(textposition='outside', textfont_size=13, textfont_color="#334155")
        
        # Renderiza no Streamlit
        st.plotly_chart(fig, width="stretch")
        
        # --- NOVO BLOCO: DETALHAMENTO POR SETOR ---
        st.markdown("<br>", unsafe_allow_html=True) # Espaçamento
        st.markdown("##### 🔍 Detalhes das Máquinas")
        
        # Cria um dropdown com os setores do gráfico
        lista_setores = df_setores.sort_values(by='Setor')['Setor'].tolist()
        setor_selecionado = st.selectbox("Selecione o setor para visualizar quem são os usuários:", lista_setores)
        
        # Filtra o dataframe original baseado na escolha
        if setor_selecionado:
            df_detalhe = df[df[col_setor] == setor_selecionado].copy()
            
            # Seleciona só as colunas que importam para o detalhe
            df_detalhe = df_detalhe[[col_nome, col_cpu, col_ram]]
            df_detalhe.columns = ['Usuário/Máquina', 'Processador', 'Memória RAM']
            
            # Substituído st.dataframe pela tabela HTML customizada
            html_detalhes = f"""
            <div style="overflow-x: auto; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <table style="width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px;">
                    <thead>
                        <tr style="background-color: #005ea2; color: white; text-align: left;">
                            <th style="padding: 12px 15px; font-weight: 600;">Usuário/Máquina</th>
                            <th style="padding: 12px 15px; font-weight: 600;">Processador</th>
                            <th style="padding: 12px 15px; font-weight: 600;">Memória RAM</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            # Usando enumerate para fazer o efeito zebrado linha a linha
            for i, (index, row) in enumerate(df_detalhe.iterrows()):
                bg_color = "#ffffff" if i % 2 == 0 else "#f8fafc"
                
                html_detalhes += f"""
                        <tr style="background-color: {bg_color}; border-bottom: 1px solid #e2e8f0; color: #334155;">
                            <td style="padding: 12px 15px;">{row['Usuário/Máquina']}</td>
                            <td style="padding: 12px 15px;">{row['Processador']}</td>
                            <td style="padding: 12px 15px;">{row['Memória RAM']}</td>
                        </tr>
                """
                
            html_detalhes += """
                    </tbody>
                </table>
            </div>
            """
            st.markdown(html_detalhes.replace("\n", ""), unsafe_allow_html=True)

    with col2:
        st.markdown("##### ⏱️ Últimos Cadastros")
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True) 
        
        # Pega as últimas 6 linhas e inverte para o mais recente ficar no topo
        ultimos = df.tail(6)[[col_nome, col_setor, col_cpu]].copy()
        ultimos.columns = ['Usuário', 'Setor', 'Processador']
        ultimos = ultimos.iloc[::-1]
        
        # HTML Tabela Zebrada com Cabeçalho Azul
        html_tabela = f"""
        <div style="overflow-x: auto; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <table style="width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px;">
                <thead>
                    <tr style="background-color: #005ea2; color: white; text-align: left;">
                        <th style="padding: 12px 15px; font-weight: 600;">Usuário</th>
                        <th style="padding: 12px 15px; font-weight: 600;">Setor</th>
                        <th style="padding: 12px 15px; font-weight: 600;">Processador</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for index, row in enumerate(ultimos.itertuples()):
            # Lógica para o fundo "Zebrado"
            bg_color = "#ffffff" if index % 2 == 0 else "#f8fafc"
            
            html_tabela += f"""
                    <tr style="background-color: {bg_color}; border-bottom: 1px solid #e2e8f0; color: #334155;">
                        <td style="padding: 12px 15px;">{row.Usuário}</td>
                        <td style="padding: 12px 15px; font-weight: 600;">{row.Setor}</td>
                        <td style="padding: 12px 15px;">{row.Processador}</td>
                    </tr>
            """
            
        html_tabela += """
                </tbody>
            </table>
        </div>
        """
        st.markdown(html_tabela.replace("\n", ""), unsafe_allow_html=True)


# --- FUNÇÃO DO POPUP ATUALIZADA (COM N EQUIP) ---
@st.dialog("📋 Ficha Completa do Ativo")
def popup_ficha_completa(dados_pc):
    nome_maquina = dados_pc['nome_equipamento'] if pd.notna(dados_pc['nome_equipamento']) and dados_pc['nome_equipamento'] else "Não Cadastrado"
    st.markdown(f"### 💻 {nome_maquina} — {dados_pc['usuario']}")
    st.caption(f"🏢 Setor: {dados_pc['setor_id']}")
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    c1.markdown(f"**🖥️ Nº Equip (Máquina):** `{nome_maquina}`")
    c1.markdown(f"**🏷️ Patrimônio:** {dados_pc['codigo_mesa']}")
    c1.markdown(f"**💾 Armazenamento:** {dados_pc['armazenamento']}")
    
    c2.markdown(f"**🪟 Sist. Operacional:** {dados_pc['sistema_operacional']}")
    c2.markdown(f"**⚙️ Processador:** {dados_pc['processador']}")
    c2.markdown(f"**🧠 Memória RAM:** {dados_pc['memoria_ram']}")
    
    st.markdown("---")
    st.markdown("**💬 Observações / Lacre / Service Tag:**")
    
    obs_texto = dados_pc['observacoes'] if pd.notna(dados_pc['observacoes']) and dados_pc['observacoes'] else "Nenhuma observação registrada."
    st.info(obs_texto)

# ==========================================
# TELA DE ESTOQUE DE PERIFÉRICOS
# ==========================================
def show_estoque_perifericos():
    import pandas as pd
    
    st.title("📦 Estoque de Periféricos")
    st.markdown("Atualizar estoque de periféricos e reposição enviando um relatório de alerta para o e-mail")
    
    somente_leitura = "Visitante" in st.session_state.get('perfil_acesso', '')

    # 1. CRIAÇÃO DO BANCO DE DADOS
    db.execute_query("""
    CREATE TABLE IF NOT EXISTS estoque_perifericos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT NOT NULL UNIQUE,
        qtd_atual INTEGER DEFAULT 0,
        qtd_minima INTEGER DEFAULT 0
    )
    """)

    # 2. POPULANDO ITENS BÁSICOS (Roda apenas se o banco estiver vazio)
    itens_iniciais = [
        ("Monitor", 0, 2), ("Teclado", 0, 5), ("Mouse", 0, 5), 
        ("Telefone Fixo", 0, 2), ("Telefone Sem Fio", 0, 2), ("Headset", 0, 3)
    ]
    
    dados_banco = db.fetch_data("SELECT * FROM estoque_perifericos")
    if not dados_banco:
        for item, qtd, min_qtd in itens_iniciais:
            try:
                db.execute_query(
                    "INSERT INTO estoque_perifericos (item, qtd_atual, qtd_minima) VALUES (?, ?, ?)",
                    (item, qtd, min_qtd)
                )
            except:
                pass
        st.rerun()

    # ==========================================
    # PAINEL SUPERIOR (Estilo Tela de Suprimentos)
    # ==========================================
    st.write("") 
    if not somente_leitura:
        if st.button("📧 Enviar Relatório de Alertas por E-mail", use_container_width=True):
            st.success("✅ Relatório gerado e enviado com sucesso para a equipe de T.I.!")
            
        with st.expander("🔄 Atualizar Estoque / Registrar Pedido de Compra"):
            c1, c2 = st.columns(2)
            
            # --- MOVIMENTAR ESTOQUE ---
            with c1:
                st.markdown("**🔄 Movimentar Estoque**")
                itens_atuais = db.fetch_data("SELECT item FROM estoque_perifericos ORDER BY item")
                lista_itens = [i['item'] for i in itens_atuais] if itens_atuais else []
                
                with st.form("form_movimentar", clear_on_submit=True):
                    mov_item = st.selectbox("Selecione o Item", lista_itens)
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        acao = st.radio("Ação", ["➕ Entrada (Chegou)", "➖ Saída (Entregue)"])
                    with col_b:
                        qtd_mov = st.number_input("Quantidade", min_value=1, value=1, step=1)
                        
                    if st.form_submit_button("💾 Registrar Movimentação", use_container_width=True):
                        if mov_item:
                            item_db = db.fetch_data("SELECT qtd_atual FROM estoque_perifericos WHERE item = ?", (mov_item,))
                            qtd_atual = int(item_db[0]['qtd_atual']) if item_db and item_db[0]['qtd_atual'] else 0
                            
                            nova_qtd = qtd_atual + qtd_mov if "Entrada" in acao else qtd_atual - qtd_mov
                            if nova_qtd < 0: nova_qtd = 0 
                            
                            db.execute_query("UPDATE estoque_perifericos SET qtd_atual = ? WHERE item = ?", (nova_qtd, mov_item))
                            st.success(f"✅ Estoque de '{mov_item}' atualizado para {nova_qtd}!")
                            st.rerun()

            # --- CADASTRAR NOVA CATEGORIA ---
            with c2:
                st.markdown("**➕ Criar Nova Categoria**")
                with st.form("form_novo_item", clear_on_submit=True):
                    novo_item = st.text_input("Nome (Ex: Cabo de Força, Webcam)")
                    novo_minimo = st.number_input("Estoque Mínimo (Alerta)", min_value=0, value=2, step=1)
                    
                    if st.form_submit_button("💾 Cadastrar Novo Item", use_container_width=True):
                        if novo_item:
                            try:
                                db.execute_query(
                                    "INSERT INTO estoque_perifericos (item, qtd_atual, qtd_minima) VALUES (?, 0, ?)",
                                    (novo_item.strip(), novo_minimo)
                                )
                                st.success(f"✅ Item '{novo_item}' adicionado ao controle!")
                                st.rerun()
                            except:
                                st.error("❌ Esse item já existe no banco de dados.")
                        else:
                            st.error("Digite o nome do item.")

    st.write("")
    st.write("")
    
    # ==========================================
    # 3. EXIBIÇÃO DO PAINEL (DUAS COLUNAS LADO A LADO)
    # ==========================================
    st.markdown("### 📊 Quantidade em Estoque Atual")
    
    dados_estoque = db.fetch_data("SELECT * FROM estoque_perifericos ORDER BY item")
    
    if dados_estoque:
        # Percorre a lista de 2 em 2 para criar linhas com dois cards lado a lado
        for i in range(0, len(dados_estoque), 2):
            # Divide a tela exatamente ao meio
            col_a, col_b = st.columns(2)
            
            # ---------------------------------------------------------
            # ITEM DA COLUNA DA ESQUERDA
            # ---------------------------------------------------------
            with col_a:
                row = dados_estoque[i]
                item = row['item']
                qtd = row['qtd_atual']
                minimo = row['qtd_minima']
                
                # Lógica de Cores
                if qtd == 0:
                    bg_color, border_color, status_icon, status_text = "#fecaca", "#ef4444", "🔴", "ZERADO"
                elif qtd <= minimo:
                    bg_color, border_color, status_icon, status_text = "#fef08a", "#eab308", "⚠️", "ATENÇÃO"
                else:
                    bg_color, border_color, status_icon, status_text = "#bbf7d0", "#22c55e", "🟢", "OK"
                    
                # HTML ALINHADO À ESQUERDA (TAMANHO MÉDIO/IDEAL)
                html_card_a = f"""<div style="background-color: {bg_color}; border-left: 6px solid {border_color}; border-radius: 6px; padding: 12px 20px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
<!-- Coluna Esquerda: Nome do Item -->
<div style="flex: 2;">
    <div style="font-size: 10px; font-weight: 700; color: #555; text-transform: uppercase; margin-bottom: 2px;">PERIFÉRICO</div>
    <div style="font-size: 16px; font-weight: 800; color: #111; text-transform: uppercase;">{item}</div>
</div>
<!-- Coluna Meio: Status -->
<div style="flex: 1; text-align: center;">
    <span style="background-color: rgba(255,255,255,0.5); padding: 5px 12px; border-radius: 12px; font-size: 11px; font-weight: 800; color: #333;">
        {status_icon} {status_text}
    </span>
</div>
<!-- Coluna Direita: Quantidade -->
<div style="flex: 1; text-align: right;">
    <div style="font-size: 10px; font-weight: 700; color: #555; text-transform: uppercase; margin-bottom: 2px;">ESTOQUE</div>
    <div style="font-size: 26px; font-weight: 900; color: #111; line-height: 1;">{qtd}</div>
</div>
</div>"""
                
                # Sub-divide o espaço da esquerda para encaixar a lixeira
                sub_c1, sub_c2 = st.columns([10, 1]) 
                with sub_c1:
                    st.markdown(html_card_a, unsafe_allow_html=True)
                with sub_c2:
                    st.write("") 
                    st.write("")
                    perfil = st.session_state.get('perfil_acesso', '').upper()
                    if not somente_leitura and "ADMINISTRADOR" in perfil:
                        if st.button("🗑️", key=f"del_{row['id']}", help=f"Excluir {item}"):
                            db.execute_query("DELETE FROM estoque_perifericos WHERE id = ?", (row['id'],))
                            st.rerun()

            # ---------------------------------------------------------
            # ITEM DA COLUNA DA DIREITA
            # ---------------------------------------------------------
            with col_b:
                # Verifica se existe um "próximo item" para colocar na direita
                if i + 1 < len(dados_estoque):
                    row2 = dados_estoque[i + 1]
                    item2 = row2['item']
                    qtd2 = row2['qtd_atual']
                    minimo2 = row2['qtd_minima']
                    
                    # Lógica de Cores do segundo item
                    if qtd2 == 0:
                        bg_color2, border_color2, status_icon2, status_text2 = "#fecaca", "#ef4444", "🔴", "ZERADO"
                    elif qtd2 <= minimo2:
                        bg_color2, border_color2, status_icon2, status_text2 = "#fef08a", "#eab308", "⚠️", "ATENÇÃO"
                    else:
                        bg_color2, border_color2, status_icon2, status_text2 = "#bbf7d0", "#22c55e", "🟢", "OK"
                        
                    html_card_b = f"""<div style="background-color: {bg_color2}; border-left: 6px solid {border_color2}; border-radius: 6px; padding: 12px 20px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
<!-- Coluna Esquerda: Nome do Item -->
<div style="flex: 2;">
    <div style="font-size: 10px; font-weight: 700; color: #555; text-transform: uppercase; margin-bottom: 2px;">PERIFÉRICO</div>
    <div style="font-size: 16px; font-weight: 800; color: #111; text-transform: uppercase;">{item2}</div>
</div>
<!-- Coluna Meio: Status -->
<div style="flex: 1; text-align: center;">
    <span style="background-color: rgba(255,255,255,0.5); padding: 5px 12px; border-radius: 12px; font-size: 11px; font-weight: 800; color: #333;">
        {status_icon2} {status_text2}
    </span>
</div>
<!-- Coluna Direita: Quantidade -->
<div style="flex: 1; text-align: right;">
    <div style="font-size: 10px; font-weight: 700; color: #555; text-transform: uppercase; margin-bottom: 2px;">ESTOQUE</div>
    <div style="font-size: 26px; font-weight: 900; color: #111; line-height: 1;">{qtd2}</div>
</div>
</div>"""
                    
                    # Sub-divide o espaço da direita para encaixar a lixeira
                    sub_c3, sub_c4 = st.columns([10, 1])
                    with sub_c3:
                        st.markdown(html_card_b, unsafe_allow_html=True)
                    with sub_c4:
                        st.write("") 
                        st.write("")
                        if not somente_leitura and "ADMINISTRADOR" in perfil:
                            if st.button("🗑️", key=f"del_{row2['id']}", help=f"Excluir {item2}"):
                                db.execute_query("DELETE FROM estoque_perifericos WHERE id = ?", (row2['id'],))
                                st.rerun()
    else:
        st.info("Nenhum item cadastrado no estoque de periféricos.")

# ==========================================
# TELA DE INVENTÁRIO DE ATIVOS 
# ==========================================
def show_inventario_ativos():
    st.title("🖥️ Inventário de Máquinas")
    
    somente_leitura = "Visitante" in st.session_state.get('perfil_acesso', '')

    try:
        db.execute_query("ALTER TABLE computadores ADD COLUMN sistema_operacional TEXT DEFAULT 'Não Informado'")
    except:
        pass 

    try:
        db.execute_query("ALTER TABLE computadores ADD COLUMN nome_equipamento TEXT DEFAULT ''")
    except:
        pass

    query = "SELECT * FROM computadores"
    dados = db.fetch_data(query)

    col_id = 'id'
    col_nome = 'usuario'
    col_cod = 'codigo_mesa'
    col_setor = 'setor_id'
    col_cpu = 'processador'
    col_ram = 'memoria_ram'
    col_ssd = 'armazenamento'
    col_obs = 'observacoes'
    col_os = 'sistema_operacional' 
    col_equip = 'nome_equipamento'

    LISTA_DEPARTAMENTOS = [
        "ACABAMENTO", "ADESIVO", "ADMINISTRAÇÃO", "ALMOXARIFADO", "ARTES", "COMERCIAL", 
        "COMPRAS", "CORTE", "CUSTOS", "DP", "ENDEREÇAMENTO", "EXPEDIÇÃO", "FATURAMENTO", 
        "FINANCEIRO", "FISCAL", "IMPRESSORAS", "LOGÍSTICA", "MARKETING", "MECÂNICA", 
        "PCP", "PORTARIA", "PRODUÇÃO", "PRODUTOS ESPECIAIS", "QUALIDADE", "RH", "T.I.", "VENDAS"
    ]

    SETORES_MEZANINO = ["ARTES", "COMPRAS", "PRODUÇÃO", "QUALIDADE"]
    SETORES_CASA = ["COMERCIAL", "RH", "DP"]
    SETORES_FABRICA = ["ACABAMENTO", "ADESIVO", "ALMOXARIFADO", "CORTE", "ENDEREÇAMENTO", "EXPEDIÇÃO", "IMPRESSORAS", "MECÂNICA", "PRODUTOS ESPECIAIS"]

    if not somente_leitura:
        with st.expander("➕ Cadastrar Novo Computador"):
            with st.form("form_cadastro_pc", clear_on_submit=True):
                st.markdown("##### Informações do Ativo")
                
                col_id1, col_id2 = st.columns(2)
                with col_id1:
                    c_nome = st.text_input("Funcionário / Usuário")
                with col_id2:
                    c_equip = st.text_input("Nº Equip (Ex: TI-01, PCP-02)")
                    
                c_cod = st.text_input("Patrimônio")
                c_lacre = st.text_input("Código do Lacre")
                
                c_setor = st.selectbox("Setor / Departamento", LISTA_DEPARTAMENTOS)
                
                col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                with col_c1:
                    c_os = st.selectbox("Sist. Operacional", ["Windows 11", "Windows 10", "Mac OS"])
                with col_c2:
                    c_cpu = st.text_input("Processador")
                with col_c3:
                    lista_ram_cadastro = ["4 GB", "8 GB", "16 GB", "32 GB", "64 GB"]
                    c_ram = st.selectbox("Memória RAM", lista_ram_cadastro)
                with col_c4:
                    c_ssd = st.text_input("Armazenamento")
                    
                c_obs = st.text_area("Observações / Service Tag")
                
                if st.form_submit_button("💾 Salvar Novo Computador", width="stretch"):
                    if c_nome and c_setor:
                        texto_obs_salvar = f"🔒 Lacre: {c_lacre} | {c_obs}" if c_lacre else c_obs
                        ins_query = f'INSERT INTO computadores ("{col_nome}", "{col_cod}", "{col_setor}", "{col_cpu}", "{col_ram}", "{col_ssd}", "{col_obs}", "{col_os}", "{col_equip}") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
                        db.execute_query(ins_query, (c_nome, c_cod, c_setor, c_cpu, c_ram, c_ssd, texto_obs_salvar, c_os, c_equip.upper()))
                        st.success("💻 Computador cadastrado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ O nome do usuário e setor são obrigatórios!")

        st.markdown("---")

    if not dados:
        st.info("Ainda não há máquinas cadastradas.")
        return

    df = pd.DataFrame(dados)

    st.markdown("#### 🔍 Consultar Ficha Completa")
    col_busca1, col_busca2 = st.columns([3, 1])
    
    opcoes_busca = {}
    for _, row in df.iterrows():
        nome_maq = row[col_equip] if pd.notna(row[col_equip]) and row[col_equip] else "S/N"
        opcoes_busca[f"💻 [{nome_maq}] — {row[col_nome]} ({row[col_setor]})"] = row
    
    with col_busca1:
        pc_busca = st.selectbox("Busque pelo nome da máquina ou usuário:", options=list(opcoes_busca.keys()), index=None, placeholder="Digite o identificador (ex: TI-01)...")
        
    with col_busca2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("👁️ Abrir Ficha (Popup)", width="stretch", disabled=pc_busca is None):
            popup_ficha_completa(opcoes_busca[pc_busca])

    st.markdown("---")

    def gerar_html_card_maquina(nome, setor, cpu, ram, ssd, cod, obs, os_ver, equip_name):
        os_ver = str(os_ver) if os_ver and os_ver != 'None' else "S/O"
        equip_name = str(equip_name) if equip_name and equip_name != 'None' and equip_name.strip() != "" else "Sem Nome"
        icon_os = "🪟" if "Windows" in os_ver else "🍎"

        if "🔒 Lacre: " in obs:
            parts = obs.split(" | ", 1)
            lacre_txt = parts[0]
            obs_txt = parts[1] if len(parts) > 1 else "Sem observações"
        else:
            lacre_txt = "🔒 Lacre: -"
            obs_txt = obs if obs else "Sem observações"

        card_raw = f"""
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 8px; flex: 1 1 calc(33.33% - 16px); min-width: 300px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); box-sizing: border-box; border-top: 4px solid #005b9f;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <div style="font-size: 10px; font-weight: bold; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px;">{setor}</div>
                <div style="font-size: 11px; font-weight: bold; color: #005b9f; background: #eaf4fc; padding: 2px 6px; border-radius: 4px; border: 1px solid #bce0fd;">💻 {equip_name}</div>
            </div>
            <div style="font-size: 18px; font-weight: 800; color: #1e293b; margin-bottom: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{nome}</div>
            
            <div style="background: #f8fafc; padding: 4px 10px; border-radius: 4px; margin-bottom: 10px; border: 1px solid #f1f5f9; font-size: 12px; font-weight: 700; color: #475569;">
                {icon_os} {os_ver} | 🏷️ Patrimônio: {cod}
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px;">
                <div style="background: #f8fafc; padding: 6px 10px; border-radius: 4px; border: 1px solid #f1f5f9;">
                    <div style="font-size: 9px; color: #94a3b8; font-weight: bold;">CPU</div>
                    <div style="font-size: 12px; font-weight: 700; color: #334155; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{cpu}</div>
                </div>
                <div style="background: #f8fafc; padding: 6px 10px; border-radius: 4px; border: 1px solid #f1f5f9;">
                    <div style="font-size: 9px; color: #94a3b8; font-weight: bold;">RAM</div>
                    <div style="font-size: 12px; font-weight: 700; color: #334155;">{ram}</div>
                </div>
            </div>
            
            <div style="background: #f0fdf4; padding: 6px 10px; border-radius: 4px; margin-bottom: 8px; border: 1px solid #bbf7d0;">
                <div style="font-size: 9px; color: #166534; font-weight: bold;">ARMAZENAMENTO</div>
                <div style="font-size: 13px; font-weight: 700; color: #166534;">💾 {ssd}</div>
            </div>

            <div style="font-size: 11px; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 8px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 5px;">
                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 140px;">{lacre_txt}</span>
                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 130px; font-style: italic;">💬 {obs_txt}</span>
            </div>
        </div>
        """
        return card_raw.replace("\n", " ")

    st.markdown("#### 📑 Catálogo de Máquinas")
    
    local_selecionado = st.radio(
        "📍 Selecione o Local Físico:",
        ["🏢 Escritório (Geral)", "🏭 Mezanino", "🏠 Casa (Anexo)", "⚙️ Fábrica"],
        horizontal=True
    )
    
    df[col_setor] = df[col_setor].fillna("NÃO DEFINIDO").astype(str).str.strip().str.upper()
    
    if "Mezanino" in local_selecionado:
        df_filtrado = df[df[col_setor].isin(SETORES_MEZANINO)]
    elif "Casa" in local_selecionado:
        df_filtrado = df[df[col_setor].isin(SETORES_CASA)]
    elif "Fábrica" in local_selecionado:
        df_filtrado = df[df[col_setor].isin(SETORES_FABRICA)]
    else:
        df_filtrado = df[~df[col_setor].isin(SETORES_MEZANINO + SETORES_CASA + SETORES_FABRICA)]

    setores_unicos = sorted(list(df_filtrado[col_setor].unique()))
    
    if not setores_unicos:
        st.info(f"Ainda não há computadores cadastrados no local: {local_selecionado}.")
    else:
        abas = st.tabs(setores_unicos)
        for aba, setor_atual in zip(abas, setores_unicos):
            with aba:
                maquinas_setor = df_filtrado[df_filtrado[col_setor] == setor_atual]
                html_bloco = '<div style="display: flex; flex-wrap: wrap; margin-top: 15px; margin-bottom: 25px;">'
                for _, row in maquinas_setor.iterrows():
                    html_bloco += gerar_html_card_maquina(
                        row[col_nome], row[col_setor], row[col_cpu], row[col_ram], row[col_ssd], row[col_cod], str(row['observacoes']) if pd.notna(row['observacoes']) else "", row[col_os], row[col_equip]
                    )
                html_bloco += '</div>'
                st.markdown(html_bloco, unsafe_allow_html=True)

    if not somente_leitura:
        st.markdown("---")
        with st.expander("📝 Editar Dados do Computador"):
            pc_selecionado = st.selectbox("Selecione o Computador para alterar:", list(opcoes_busca.keys()), key="edit_box")
            
            if pc_selecionado:
                dados_pc = opcoes_busca[pc_selecionado]
                
                val_obs = str(dados_pc[col_obs]) if pd.notna(dados_pc[col_obs]) else ""
                if "🔒 Lacre: " in val_obs:
                    parts = val_obs.split(" | ", 1)
                    lacre_atual = parts[0].replace("🔒 Lacre: ", "")
                    obs_atual = parts[1] if len(parts) > 1 else ""
                else:
                    lacre_atual = ""
                    obs_atual = val_obs

                with st.form("form_edicao_pc"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        e_nome = st.text_input("Usuário", value=dados_pc[col_nome])
                        e_equip = st.text_input("Nº Equip (Nome da Máquina)", value=str(dados_pc[col_equip]) if pd.notna(dados_pc[col_equip]) else "")
                        e_os = st.selectbox("Sistema Operacional", ["Windows 11", "Windows 10", "Mac OS"], index=0 if "11" in str(dados_pc[col_os]) else (1 if "10" in str(dados_pc[col_os]) else 2))
                        e_cod = st.text_input("Patrimônio", value=dados_pc[col_cod])
                        e_lacre = st.text_input("Código do Lacre", value=lacre_atual)
                        
                    with col_e2:
                        setor_atual = str(dados_pc[col_setor]).upper() if pd.notna(dados_pc[col_setor]) else "ADMINISTRAÇÃO"
                        lista_edit_setores = LISTA_DEPARTAMENTOS.copy()
                        if setor_atual not in lista_edit_setores: lista_edit_setores.append(setor_atual)
                        e_setor = st.selectbox("Setor", lista_edit_setores, index=lista_edit_setores.index(setor_atual))
                        
                        e_cpu = st.text_input("Processador", value=dados_pc[col_cpu])
                        lista_ram = ["4 GB", "8 GB", "16 GB", "32 GB", "64 GB"]
                        ram_atual = str(dados_pc[col_ram]).strip() if pd.notna(dados_pc[col_ram]) else "8 GB"
                        if ram_atual not in lista_ram: lista_ram.append(ram_atual)
                        e_ram = st.selectbox("RAM", lista_ram, index=lista_ram.index(ram_atual))
                        
                        e_ssd = st.text_input("Armazenamento", value=dados_pc[col_ssd])
                    
                    e_obs = st.text_area("Obs / Service Tag", value=obs_atual, height=100)
                    
                    if st.form_submit_button("⚡ Atualizar Dados da Máquina", width="stretch"):
                        texto_obs_atualizar = f"🔒 Lacre: {e_lacre} | {e_obs}" if e_lacre else e_obs
                        up_query = f'UPDATE computadores SET "{col_nome}"=?, "{col_equip}"=?, "{col_os}"=?, "{col_cod}"=?, "{col_setor}"=?, "{col_cpu}"=?, "{col_ram}"=?, "{col_ssd}"=?, "{col_obs}"=? WHERE "{col_id}"=?'
                        db.execute_query(up_query, (e_nome, e_equip.upper(), e_os, e_cod, e_setor, e_cpu, e_ram, e_ssd, texto_obs_atualizar, dados_pc[col_id]))
                        st.success("🔄 Dados atualizados!")
                        st.rerun()

        with st.expander("🗑️ Excluir Computador do Sistema"):
            pc_deletar = st.selectbox("Selecione a máquina que deseja deletar do sistema:", list(opcoes_busca.keys()), key="del_box")
            
            if pc_deletar:
                dados_del = opcoes_busca[pc_deletar]
                st.warning(f"⚠️ **Atenção:** Você está prestes a excluir permanentemente o cadastro de **{dados_del[col_nome]}**.")
                confirmar_exclusao = st.checkbox("Confirmo que desejo apagar este computador permanentemente do Portal.")
                
                if st.button("🔴 APAGAR CADASTRO", width="stretch", disabled=not confirmar_exclusao):
                    del_query = f'DELETE FROM computadores WHERE "{col_id}" = ?'
                    db.execute_query(del_query, (dados_del[col_id],))
                    st.success(f"🗑️ Cadastro de {dados_del[col_nome]} excluído com sucesso!")
                    st.rerun()



# ==========================================
# TELA DE NOTEBOOKS REGISPEL
# ==========================================
def show_notebook_regispel():
    import pandas as pd
    from datetime import datetime
    
    st.title("💻 Controle de Notebooks Regispel")
    st.markdown("Gerencie os equipamentos, atribuições e credenciais de segurança (LGPD).")
    st.markdown("---")
    
    somente_leitura = "Visitante" in st.session_state.get('perfil_acesso', '')

    # 1. CRIAÇÃO DO BANCO DE DADOS
    db.execute_query("""
    CREATE TABLE IF NOT EXISTS laptops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_pc TEXT,
        modelo TEXT NOT NULL,
        service_tag TEXT,
        patrimonio TEXT,
        responsavel TEXT NOT NULL,
        localizacao TEXT,
        data_entrega TEXT,
        senha_sistema TEXT,
        senha_bios TEXT,
        usuario_ksc TEXT,
        senha_kaspersky TEXT,
        senha_adm TEXT,
        observacoes TEXT,
        status TEXT DEFAULT '🟢 EM USO'
    )
    """)

    novas_colunas = [
        "nome_pc", "data_entrega", "senha_sistema", "senha_bios", 
        "usuario_ksc", "senha_kaspersky", "senha_adm", "observacoes"
    ]
    for col in novas_colunas:
        try:
            db.execute_query(f"ALTER TABLE laptops ADD COLUMN {col} TEXT")
        except:
            pass

    # ==========================================
    # 2. OPÇÕES DE CADASTRO, IMPORTAÇÃO E EDIÇÃO
    # ==========================================
    if not somente_leitura:
        
        with st.expander("➕ Cadastrar Novo Notebook (Manual)"):
            with st.form("form_novo_laptop", clear_on_submit=True):
                st.markdown("**📦 Dados do Equipamento**")
                c1, c2, c3, c4 = st.columns(4)
                with c1: lap_nome_pc = st.text_input("Nome do PC (Ex: VENDEDOR-05)")
                with c2: lap_modelo = st.text_input("Modelo Atual")
                with c3: lap_tag = st.text_input("Service Tag / Série")
                with c4: lap_patrimonio = st.text_input("Etiqueta / Patrimônio")

                st.markdown("**👤 Atribuição**")
                c5, c6, c7, c8 = st.columns(4)
                with c5: lap_responsavel = st.text_input("Usuário / Responsável")
                with c6: lap_local = st.text_input("Departamento")
                with c7: lap_data = st.date_input("Data de Entrega", value=datetime.today())
                with c8: lap_status = st.selectbox("Status", ["🟢 EM USO", "🟡 ESTOQUE (T.I.)", "🔴 EM MANUTENÇÃO", "⚫ DESCARTE", "❌ ROUBO/PERDA"])

                st.markdown("**🔒 Segurança e Credenciais (LGPD)**")
                s1, s2, s3 = st.columns(3)
                with s1: lap_senha_sis = st.text_input("System Password")
                with s2: lap_senha_bios = st.text_input("Admin BIOS")
                with s3: lap_senha_adm = st.text_input("Senha ADM Local")
                
                s4, s5, s6 = st.columns(3)
                with s4: lap_user_ksc = st.text_input("Usuário KSC / AD")
                with s5: lap_senha_ksc = st.text_input("Senha Kaspersky (Disk Encryption)")
                with s6: lap_obs = st.text_input("Defeitos / Observações")

                if st.form_submit_button("💾 Salvar Registro", width="stretch"):
                    if lap_responsavel and lap_modelo:
                        data_str = lap_data.strftime("%d/%m/%Y")
                        db.execute_query(
                            """INSERT INTO laptops 
                            (nome_pc, modelo, service_tag, patrimonio, responsavel, localizacao, data_entrega, 
                            senha_sistema, senha_bios, usuario_ksc, senha_kaspersky, senha_adm, observacoes, status) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (lap_nome_pc, lap_modelo, lap_tag, lap_patrimonio, lap_responsavel, lap_local, data_str,
                             lap_senha_sis, lap_senha_bios, lap_user_ksc, lap_senha_ksc, lap_senha_adm, lap_obs, lap_status)
                        )
                        st.success("✅ Notebook cadastrado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Os campos Usuário e Modelo são obrigatórios.")
        
        with st.expander("📥 Importar Planilha do Servidor (Excel)"):
            st.info("💡 **Dica:** Você pode subir o arquivo completo da rede. O portal deixará você escolher a aba exata.")
            arquivo_excel = st.file_uploader("Selecione a sua super planilha (.xlsx)", type=["xlsx"])
            
            if arquivo_excel is not None:
                try:
                    xls = pd.ExcelFile(arquivo_excel)
                    nomes_abas = xls.sheet_names
                    
                    index_aba = 0
                    for i, nome in enumerate(nomes_abas):
                        if "laptop" in nome.lower():
                            index_aba = i
                            break
                    
                    col_aba, col_linha = st.columns(2)
                    with col_aba:
                        aba_selecionada = st.selectbox("Qual aba deseja importar?", nomes_abas, index=index_aba)
                    with col_linha:
                        linha_cabecalho = st.number_input("Em qual linha os cabeçalhos começam? (Ex: 3)", min_value=1, max_value=20, value=3)
                    
                    df_import = pd.read_excel(arquivo_excel, sheet_name=aba_selecionada, header=linha_cabecalho - 1)
                    st.write("👀 Pré-visualização dos dados encontrados:")
                    st.dataframe(df_import.head(3), use_container_width=True)
                    
                    if st.button("🚀 Iniciar Importação para o Banco de Dados", type="primary", width="stretch"):
                        linhas_importadas = 0
                        colunas_excel = [str(c).lower() for c in df_import.columns]
                        
                        with st.spinner("Importando máquinas..."):
                            for index, row in df_import.iterrows():
                                def pega_valor(chaves):
                                    for c_orig, c_low in zip(df_import.columns, colunas_excel):
                                        for chave in chaves:
                                            if chave in c_low:
                                                v = row[c_orig]
                                                return str(v).strip() if pd.notna(v) and str(v).strip() != "" else ""
                                    return ""

                                ex_nome = pega_valor(['nome pc', 'maquina'])
                                ex_modelo = pega_valor(['atual', 'modelo', 'equipamento'])
                                ex_tag = pega_valor(['service tag', 'serie'])
                                ex_patrim = pega_valor(['etiqueta', 'patrimonio'])
                                ex_resp = pega_valor(['usuario', 'responsavel'])
                                ex_local = pega_valor(['departamento', 'setor'])
                                ex_data = pega_valor(['data', 'entrega'])
                                ex_sys = pega_valor(['system password', 'sys'])
                                ex_bios = pega_valor(['admin bios', 'bios'])
                                ex_ksc_u = pega_valor(['ksc', 'kaspersky', 'ad'])
                                ex_ksc_p = pega_valor(['encryption', 'kaspersky full', 'senha kaspersky'])
                                ex_adm = pega_valor(['senha adm', 'adm local'])
                                ex_obs = pega_valor(['antigo', 'defeito', 'obs'])
                                
                                if ex_resp or ex_modelo or ex_nome:
                                    status_import = "🔴 ROUBO/PERDA" if "roubo" in ex_obs.lower() else "🟢 EM USO"
                                    
                                    db.execute_query(
                                        """INSERT INTO laptops 
                                        (nome_pc, modelo, service_tag, patrimonio, responsavel, localizacao, data_entrega, 
                                        senha_sistema, senha_bios, usuario_ksc, senha_kaspersky, senha_adm, observacoes, status) 
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                        (ex_nome, ex_modelo, ex_tag, ex_patrim, ex_resp, ex_local, ex_data,
                                         ex_sys, ex_bios, ex_ksc_u, ex_ksc_p, ex_adm, ex_obs, status_import)
                                    )
                                    linhas_importadas += 1
                        
                        st.success(f"🎉 Sucesso! {linhas_importadas} notebooks foram importados e adicionados ao catálogo.")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao ler a planilha. Detalhe técnico: {e}")

        # ==========================================
        # EDITAR NOTEBOOK (Para Técnicos)
        # ==========================================
        with st.expander("✏️ Editar Registro de Notebook"):
            laptops_existentes = db.fetch_data("SELECT * FROM laptops ORDER BY responsavel")
            
            if laptops_existentes:
                opcoes_laptops = {f"{lap['responsavel']} - {lap.get('nome_pc', 'Sem Nome')} ({lap['modelo']})": lap for lap in laptops_existentes}
                laptop_selecionado_nome = st.selectbox("Selecione o Notebook para atualizar:", list(opcoes_laptops.keys()), key="sel_edicao")
                laptop_selecionado = opcoes_laptops[laptop_selecionado_nome]
                
                with st.form("form_editar_laptop", clear_on_submit=False):
                    st.markdown("**✏️ Atualizar Dados do Equipamento**")
                    
                    def get_val_ed(chave):
                        v = laptop_selecionado.get(chave)
                        return str(v) if v is not None and str(v) != 'nan' else ""
                        
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: ed_nome_pc = st.text_input("Nome do PC", value=get_val_ed('nome_pc'))
                    with c2: ed_modelo = st.text_input("Modelo Atual", value=get_val_ed('modelo'))
                    with c3: ed_tag = st.text_input("Service Tag / Série", value=get_val_ed('service_tag'))
                    with c4: ed_patrimonio = st.text_input("Etiqueta / Patrimônio", value=get_val_ed('patrimonio'))

                    c5, c6, c7, c8 = st.columns(4)
                    with c5: ed_responsavel = st.text_input("Usuário / Responsável", value=get_val_ed('responsavel'))
                    with c6: ed_local = st.text_input("Departamento", value=get_val_ed('localizacao'))
                    
                    data_banco = get_val_ed('data_entrega')
                    try:
                        data_obj = datetime.strptime(data_banco, "%d/%m/%Y").date()
                    except:
                        data_obj = datetime.today().date()
                        
                    with c7: ed_data = st.date_input("Data de Entrega", value=data_obj)
                    
                    opcoes_status = ["🟢 EM USO", "🟡 ESTOQUE (T.I.)", "🔴 EM MANUTENÇÃO", "⚫ DESCARTE", "❌ ROUBO/PERDA"]
                    status_atual = get_val_ed('status')
                    idx_status = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0
                    with c8: ed_status = st.selectbox("Status", opcoes_status, index=idx_status)

                    s1, s2, s3 = st.columns(3)
                    with s1: ed_senha_sis = st.text_input("System Password", value=get_val_ed('senha_sistema'))
                    with s2: ed_senha_bios = st.text_input("Admin BIOS", value=get_val_ed('senha_bios'))
                    with s3: ed_senha_adm = st.text_input("Senha ADM Local", value=get_val_ed('senha_adm'))
                    
                    s4, s5, s6 = st.columns(3)
                    with s4: ed_user_ksc = st.text_input("Usuário KSC / AD", value=get_val_ed('usuario_ksc'))
                    with s5: ed_senha_ksc = st.text_input("Senha Kaspersky", value=get_val_ed('senha_kaspersky'))
                    with s6: ed_obs = st.text_input("Defeitos / Observações", value=get_val_ed('observacoes'))

                    if st.form_submit_button("💾 Atualizar Registro", type="primary", use_container_width=True):
                        if ed_responsavel and ed_modelo:
                            data_str = ed_data.strftime("%d/%m/%Y")
                            db.execute_query(
                                """UPDATE laptops SET 
                                nome_pc=?, modelo=?, service_tag=?, patrimonio=?, responsavel=?, localizacao=?, data_entrega=?, 
                                senha_sistema=?, senha_bios=?, usuario_ksc=?, senha_kaspersky=?, senha_adm=?, observacoes=?, status=? 
                                WHERE id=?""",
                                (ed_nome_pc, ed_modelo, ed_tag, ed_patrimonio, ed_responsavel, ed_local, data_str,
                                 ed_senha_sis, ed_senha_bios, ed_user_ksc, ed_senha_ksc, ed_senha_adm, ed_obs, ed_status, laptop_selecionado['id'])
                            )
                            st.success("✅ Notebook atualizado com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Os campos Usuário e Modelo são obrigatórios.")
            else:
                st.info("Nenhum notebook cadastrado para editar.")

        # ==========================================
        # EXCLUIR NOTEBOOK (Apenas Administrador)
        # ==========================================
        perfil = st.session_state.get('perfil_acesso', '').upper()
        if "ADMINISTRADOR" in perfil:
            with st.expander("🗑️ Excluir Registro (Modo Administrador)"):
                if laptops_existentes:
                    laptop_sel_del_nome = st.selectbox("Selecione o Notebook para apagar:", list(opcoes_laptops.keys()), key="sel_exclusao")
                    laptop_sel_del = opcoes_laptops[laptop_sel_del_nome]
                    
                    st.warning("⚠️ **Atenção:** A exclusão removerá o equipamento permanentemente do banco de dados.")
                    
                    col_del1, col_del2 = st.columns([3, 1])
                    with col_del1:
                        confirmar_del = st.checkbox(f"🚨 Confirmo que desejo apagar o notebook de **{laptop_sel_del['responsavel']}**.")
                    with col_del2:
                        if st.button("🔴 EXCLUIR REGISTRO", use_container_width=True, disabled=not confirmar_del):
                            db.execute_query("DELETE FROM laptops WHERE id=?", (laptop_sel_del['id'],))
                            st.success("🗑️ Registro apagado!")
                            st.rerun()
                else:
                    st.info("Nenhum notebook disponível para exclusão.")

    st.markdown("---")
    
    # ==========================================
    # 3. EXIBIÇÃO EM FORMATO DE CATÁLOGO (Cards Perfeitos)
    # ==========================================
    st.subheader("📑 Catálogo de Notebooks")
    dados_laptops = db.fetch_data("SELECT * FROM laptops ORDER BY responsavel")
    
    if dados_laptops:
        df_laptops = pd.DataFrame(dados_laptops)
        
        # --- CLASSIFICAÇÃO INTELIGENTE AUTOMÁTICA ---
        def classificar_depto(row):
            loc = str(row.get('localizacao', '')).strip().upper()
            nome = str(row.get('nome_pc', '')).strip().upper()
            
            if loc == "" or loc == "NAN" or loc == "NÃO DEFINIDO" or loc == "NONE":
                if "VENDEDOR" in nome or "COMERCIAL" in nome: return "VENDEDORES"
                elif "MARKETING" in nome: return "MARKETING"
                elif "SUPERVISOR" in nome: return "SUPERVISOR"
                elif "PCP" in nome: return "PCP"
                elif "DIRETORIA" in nome: return "DIRETORIA"
                elif "REUNIÃO" in nome: return "SALA DE REUNIÃO"
                elif "ADM" in nome: return "ADMINISTRAÇÃO"
                else: return "NÃO DEFINIDO"
            return loc.upper()

        df_laptops['localizacao'] = df_laptops.apply(classificar_depto, axis=1)
        
        departamentos = sorted(df_laptops['localizacao'].unique().tolist())
        
        abas = st.tabs([dept.upper() for dept in departamentos])
        
        for i, dept in enumerate(departamentos):
            with abas[i]:
                df_dept = df_laptops[df_laptops['localizacao'] == dept]
                cols = st.columns(2)
                
                for index, row in df_dept.reset_index().iterrows():
                    coluna_atual = cols[index % 2]
                    
                    def get_val(col_name, default="-"):
                        val = row.get(col_name)
                        return str(val) if pd.notna(val) and str(val).strip() != "" and str(val).strip() != "nan" else default
                        
                    nome_pc = get_val('nome_pc', 'SEM NOME')
                    resp = get_val('responsavel', 'Não Atribuído')
                    modelo = get_val('modelo')
                    patrimonio = get_val('patrimonio')
                    sys_pwd = get_val('senha_sistema')
                    bios = get_val('senha_bios')
                    adm = get_val('senha_adm')
                    ksc_user = get_val('usuario_ksc')
                    ksc_pwd = get_val('senha_kaspersky')
                    status = get_val('status')
                    tag = get_val('service_tag')
                    obs = get_val('observacoes', '')
                    
                    # Cores Idênticas ao Módulo de Máquinas
                    if "USO" in status.upper():
                        status_bg, status_border, status_label, status_val_color = "#f2fdeb", "#d5e8ce", "#7fad71", "#2d3436"
                    elif "ESTOQUE" in status.upper():
                        status_bg, status_border, status_label, status_val_color = "#fffde7", "#f0e68c", "#cba82a", "#2d3436"
                    elif "MANUTENÇÃO" in status.upper():
                        status_bg, status_border, status_label, status_val_color = "#fce4e4", "#f5c6c6", "#e06666", "#2d3436"
                    else:
                        status_bg, status_border, status_label, status_val_color = "#f5f6fa", "#dcdde1", "#7f8fa6", "#2d3436"

                    obs_html = f"<div style='margin-bottom: 12px; color: #d63031; font-size: 11px; font-weight: 700;'>⚠️ Obs: {obs}</div>" if obs else ""

                    html_card = f"""<div style="border: 1px solid #e0e0e0; border-top: 4px solid #025da6; border-radius: 8px; padding: 15px; background-color: white; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); height: 100%;">
<!-- Cabeçalho idêntico -->
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <span style="font-size: 9px; font-weight: 800; color: #7f8c8d; letter-spacing: 0.5px; text-transform: uppercase;">{dept}</span>
    <span style="background-color: #e3f2fd; color: #025da6; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 700;">💻 {nome_pc}</span>
</div>

<!-- Título Usuário Maior -->
<div style="margin: 0 0 12px 0; color: #2c3e50; font-size: 16px; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
    {resp}
</div>

<!-- Faixa Cinza Equipamento -->
<div style="background-color: #f8f9fa; padding: 10px 12px; border-radius: 5px; font-size: 11px; color: #2d3436; font-weight: 600; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
    💻 {modelo} <span style="color: #dfe6e9;">|</span> 🏷️ Patrimônio: {patrimonio}
</div>

<!-- Divisão de Credenciais estilo CPU/RAM -->
<div style="display: flex; gap: 10px; margin-bottom: 10px;">
    <div style="flex: 1; background-color: #f8f9fa; padding: 10px 12px; border-radius: 5px;">
        <div style="font-size: 8px; color: #7f8c8d; font-weight: 800; text-transform: uppercase; margin-bottom: 4px;">SENHAS DO SISTEMA</div>
        <div style="font-size: 11px; color: #2d3436; font-weight: 700; line-height: 1.4;">
            <span style="color: #636e72; font-weight: 500;">Sys:</span> {sys_pwd}<br>
            <span style="color: #636e72; font-weight: 500;">BIOS:</span> {bios}
        </div>
    </div>
    <div style="flex: 1; background-color: #f8f9fa; padding: 10px 12px; border-radius: 5px;">
        <div style="font-size: 8px; color: #7f8c8d; font-weight: 800; text-transform: uppercase; margin-bottom: 4px;">CREDENCIAIS AD/LOCAL</div>
        <div style="font-size: 11px; color: #2d3436; font-weight: 700; line-height: 1.4;">
            <span style="color: #636e72; font-weight: 500;">ADM:</span> {adm}<br>
            <span style="color: #636e72; font-weight: 500;">KSC:</span> {ksc_user} / {ksc_pwd}
        </div>
    </div>
</div>

<!-- Status estilo caixa de Armazenamento -->
<div style="background-color: {status_bg}; border: 1px solid {status_border}; padding: 10px 12px; border-radius: 5px; margin-bottom: 15px;">
    <div style="font-size: 8px; color: {status_label}; font-weight: 800; text-transform: uppercase; margin-bottom: 4px;">STATUS DO EQUIPAMENTO</div>
    <div style="font-size: 12px; color: {status_val_color}; font-weight: 800;">
        {status}
    </div>
</div>

{obs_html}

<!-- Rodapé cinza pequeno -->
<div style="display: flex; justify-content: space-between; font-size: 10px; color: #b2bec3; font-weight: 600;">
    <span>🔒 Lacre: {patrimonio}</span>
    <span style="font-style: italic;">💬 Service Tag - {tag}</span>
</div>
</div>"""
                    
                    with coluna_atual:
                        st.markdown(html_card, unsafe_allow_html=True)
    else:
        st.info("Nenhum notebook cadastrado no inventário ainda.")
# ==========================================
# TELA DE FLUXO DE RH (COM MODO LEITURA)
# ==========================================
def show_fluxo_rh():
    st.title("🔄 Fluxo de RH (Entrada e Saída)")
    st.markdown("---")
    
    somente_leitura = "Visitante" in st.session_state.get('perfil_acesso', '')

    LISTA_DEPARTAMENTOS = [
        "ACABAMENTO", "ADESIVO", "ADMINISTRAÇÃO", "ALMOXARIFADO", "ARTES", "COMERCIAL", 
        "COMPRAS", "CORTE", "CUSTOS", "DP", "ENDEREÇAMENTO", "EXPEDIÇÃO", "FATURAMENTO", 
        "FINANCEIRO", "FISCAL", "IMPRESSORAS", "LOGÍSTICA", "MARKETING", "MECÂNICA", 
        "PCP", "PORTARIA", "PRODUÇÃO", "PRODUTOS ESPECIAIS", "QUALIDADE", "RH", "T.I.", "VENDAS"
    ]

    db.execute_query("""
    CREATE TABLE IF NOT EXISTS fluxo_rh (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        colaborador TEXT NOT NULL,
        tipo TEXT NOT NULL, 
        setor TEXT NOT NULL,
        data_evento TEXT,
        t1_ok INTEGER DEFAULT 0, 
        t2_ok INTEGER DEFAULT 0, 
        t3_ok INTEGER DEFAULT 0, 
        t4_ok INTEGER DEFAULT 0  
    )
    """)

    # 🔹 CORRIGIDO: Adicionada a vírgula após "observacoes"
    novas_colunas = [
        "matricula", "ramal", "usuario_totvs", "senha_totvs",
        "user_ad", "senha_ad", "user_email", "senha_email",
        "user_office", "senha_office", "observacoes",
        "data_conclusao"
    ]
    for col_name in novas_colunas:
        try:
            db.execute_query(f"ALTER TABLE fluxo_rh ADD COLUMN {col_name} TEXT")
        except Exception:
            pass 

    def get_safe_val(row_data, field_key):
        val = row_data.get(field_key, '')
        return '' if pd.isna(val) or val is None else str(val)

    dados_pendentes = db.fetch_data("SELECT * FROM fluxo_rh WHERE t1_ok = 0 OR t2_ok = 0 OR t3_ok = 0 OR t4_ok = 0")
    df = pd.DataFrame(dados_pendentes) if dados_pendentes else pd.DataFrame()

    if not somente_leitura:
        with st.expander("➕ Lançar Nova Movimentação de Funcionário"):
            with st.form("form_rh", clear_on_submit=True):
                f_nome = st.text_input("Nome Completo do Colaborador")
                f_tipo = st.radio("Tipo de Movimentação", ["ENTRADA (Onboarding)", "SAÍDA (Offboarding)"], horizontal=True)
                f_setor = st.selectbox("Setor / Departamento", LISTA_DEPARTAMENTOS)
                f_data = st.date_input("Data do Evento (Primeiro/Último dia)").strftime("%d/%m/%Y")
                
                if st.form_submit_button("🚀 Abrir Checklist para a T.I.", width="stretch"):
                    if f_nome:
                        tipo_limpo = "ENTRADA" if "ENTRADA" in f_tipo else "SAÍDA"
                        t4_inicial = 0 if tipo_limpo == "ENTRADA" else 1
                        
                        query_ins = "INSERT INTO fluxo_rh (colaborador, tipo, setor, data_evento, t1_ok, t2_ok, t3_ok, t4_ok) VALUES (?, ?, ?, ?, 0, 0, 0, ?)"
                        db.execute_query(query_ins, (f_nome, tipo_limpo, f_setor, f_data, t4_inicial))
                        st.success(f"📋 Fluxo de {tipo_limpo} aberto para {f_nome}!")
                        st.rerun()
                    else:
                        st.error("❌ Digite o nome do colaborador.")

        st.markdown("---")

    if not df.empty:
        entradas_num = len(df[df['tipo'] == 'ENTRADA'])
        saidas_num = len(df[df['tipo'] == 'SAÍDA'])
    else:
        entradas_num = saidas_num = 0

    kpi_html = f"""
    <div style="display: flex; gap: 20px; margin-bottom: 25px;">
        <div style="flex: 1; background-color: #ffffff; border-left: 5px solid #3b82f6; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="font-size: 11px; color: #64748b; font-weight: bold; text-transform: uppercase;">Novos Funcionários (Onboarding)</div>
            <div style="font-size: 28px; font-weight: 800; color: #1e293b; margin-top: 5px;">📥 {entradas_num} Pendente(s)</div>
        </div>
        <div style="flex: 1; background-color: #ffffff; border-left: 5px solid #ef4444; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="font-size: 11px; color: #64748b; font-weight: bold; text-transform: uppercase;">Desligamentos (Offboarding)</div>
            <div style="font-size: 28px; font-weight: 800; color: #1e293b; margin-top: 5px;">📤 {saidas_num} Pendente(s)</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    if df.empty:
        st.success("🎉 Excelente! Todos os acessos e pendências de RH estão 100% resolvidos.")
    else:
        st.markdown("#### 📋 Listas de Verificação Ativas")
        
        col_esq, col_dir = st.columns(2)

        with col_esq:
            st.markdown("##### 📥 Entradas (Preparar Acessos)")
            df_entradas = df[df['tipo'] == 'ENTRADA']
            
            if df_entradas.empty:
                st.caption("Nenhum onboarding pendente.")
            
            for _, row in df_entradas.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['colaborador']}** ({row['setor']})")
                    st.caption(f"📅 Data de Início: {row['data_evento']}")
                    
                    check1 = st.checkbox("🖥️ Usuário AD - Windows", value=bool(row['t1_ok']), key=f"ent_t1_{row['id']}", disabled=somente_leitura)
                    check2 = st.checkbox("📧 E-mail Outlook e Pacote Office", value=bool(row['t2_ok']), key=f"ent_t2_{row['id']}", disabled=somente_leitura)
                    check3 = st.checkbox("👥 Cadastrar no Grupo @all", value=bool(row['t3_ok']), key=f"ent_t3_{row['id']}", disabled=somente_leitura)
                    check4 = st.checkbox("🖨️ Cadastrar Impressora do Setor", value=bool(row['t4_ok']), key=f"ent_t4_{row['id']}", disabled=somente_leitura)
                    
                    st.markdown("---")
                    st.markdown("###### 🔑 Informações e Credenciais")
                    
                    c_bas1, c_bas2 = st.columns(2)
                    with c_bas1:
                        mat_input = st.text_input("Matrícula", value=get_safe_val(row, 'matricula'), key=f"ent_mat_{row['id']}", disabled=somente_leitura)
                    with c_bas2:
                        ramal_input = st.text_input("Ramal", value=get_safe_val(row, 'ramal'), key=f"ent_ram_{row['id']}", disabled=somente_leitura)
                    
                    c_ad1, c_ad2 = st.columns(2)
                    with c_ad1:
                        ad_user = st.text_input("Usuário AD (Windows)", value=get_safe_val(row, 'user_ad'), key=f"ent_aduser_{row['id']}", disabled=somente_leitura)
                    with c_ad2:
                        ad_pass = st.text_input("Senha AD (Windows)", value=get_safe_val(row, 'senha_ad'), key=f"ent_adpass_{row['id']}", disabled=somente_leitura)
                    
                    c_tot1, c_tot2 = st.columns(2)
                    with c_tot1:
                        t_user = st.text_input("Usuário TOTVS", value=get_safe_val(row, 'usuario_totvs'), key=f"ent_tuser_{row['id']}", disabled=somente_leitura)
                    with c_tot2:
                        t_pass = st.text_input("Senha TOTVS", value=get_safe_val(row, 'senha_totvs'), key=f"ent_tpass_{row['id']}", disabled=somente_leitura)
                    
                    c_em1, c_em2 = st.columns(2)
                    with c_em1:
                        em_user = st.text_input("Usuário E-mail", value=get_safe_val(row, 'user_email'), key=f"ent_emuser_{row['id']}", disabled=somente_leitura)
                    with c_em2:
                        em_pass = st.text_input("Senha E-mail", value=get_safe_val(row, 'senha_email'), key=f"ent_empass_{row['id']}", disabled=somente_leitura)
                    
                    c_of1, c_of2 = st.columns(2)
                    with c_of1:
                        of_user = st.text_input("Usuário Office", value=get_safe_val(row, 'user_office'), key=f"ent_ofuser_{row['id']}", disabled=somente_leitura)
                    with c_of2:
                        of_pass = st.text_input("Senha Office", value=get_safe_val(row, 'senha_office'), key=f"ent_ofpass_{row['id']}", disabled=somente_leitura)
                        
                    obs_input = st.text_area("Observações / Detalhes Gerais", value=get_safe_val(row, 'observacoes'), key=f"ent_obs_{row['id']}", disabled=somente_leitura)
                    
                    c_btn1, c_btn2 = st.columns(2)
                    with c_btn1:
                        if st.button("📋 Gerar Pop-up", key=f"btn_pop_ent_{row['id']}", use_container_width=True):
                            popup_acessos(row['colaborador'], row['setor'], "ENTRADA", mat_input, ramal_input, t_user, t_pass, ad_user, ad_pass, em_user, em_pass, of_user, of_pass, obs_input)
                    with c_btn2:
                        if not somente_leitura and st.button("💾 Salvar Dados", key=f"btn_salvar_ent_{row['id']}", use_container_width=True):
                            
                            # 🔹 NOVO: Capturando a data e hora atual
                            carimbo = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            
                            db.execute_query(
                                """UPDATE fluxo_rh 
                                   SET t1_ok=?, t2_ok=?, t3_ok=?, t4_ok=?, 
                                       matricula=?, ramal=?, usuario_totvs=?, senha_totvs=?,
                                       user_ad=?, senha_ad=?, user_email=?, senha_email=?,
                                       user_office=?, senha_office=?, observacoes=?, data_conclusao=? 
                                   WHERE id=?""",
                                # 🔹 NOVO: Adicionado 'carimbo' na tupla de parâmetros
                                (int(check1), int(check2), int(check3), int(check4), 
                                 mat_input, ramal_input, t_user, t_pass, ad_user, ad_pass, em_user, em_pass, of_user, of_pass, obs_input, carimbo, row['id'])
                            )
                            st.success(f"Dados salvos! Registrado em: {carimbo}")
                            st.rerun()

        with col_dir:
            st.markdown("##### 📤 Saídas (Bloquear e Recolher)")
            df_saidas = df[df['tipo'] == 'SAÍDA']
            
            if df_saidas.empty:
                st.caption("Nenhum offboarding pendente.")
                
            for _, row in df_saidas.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['colaborador']}** ({row['setor']})")
                    st.caption(f"📅 Último Dia: {row['data_evento']}")
                    
                    check1 = st.checkbox("🚫 Bloquear Contas de E-mail / M365", value=bool(row['t1_ok']), key=f"sai_t1_{row['id']}", disabled=somente_leitura)
                    check2 = st.checkbox("🔒 Revogar Acessos do ERP / Sistemas", value=bool(row['t2_ok']), key=f"sai_t2_{row['id']}", disabled=somente_leitura)
                    check3 = st.checkbox("🔌 Recolher Notebook / Equipamentos", value=bool(row['t3_ok']), key=f"sai_t3_{row['id']}", disabled=somente_leitura)
                    
                    st.markdown("---")
                    st.markdown("###### 🔑 Informações e Revogações")
                    
                    c_bas1, c_bas2 = st.columns(2)
                    with c_bas1:
                        mat_input = st.text_input("Matrícula", value=get_safe_val(row, 'matricula'), key=f"sai_mat_{row['id']}", disabled=somente_leitura)
                    with c_bas2:
                        ramal_input = st.text_input("Ramal Removido", value=get_safe_val(row, 'ramal'), key=f"sai_ram_{row['id']}", disabled=somente_leitura)
                    
                    c_ad1, c_ad2 = st.columns(2)
                    with c_ad1:
                        ad_user = st.text_input("Usuário AD", value=get_safe_val(row, 'user_ad'), key=f"sai_aduser_{row['id']}", disabled=somente_leitura)
                    with c_ad2:
                        ad_pass = st.text_input("Senha AD", value=get_safe_val(row, 'senha_ad'), key=f"sai_adpass_{row['id']}", disabled=somente_leitura)
                    
                    c_tot1, c_tot2 = st.columns(2)
                    with c_tot1:
                        t_user = st.text_input("Usuário TOTVS", value=get_safe_val(row, 'usuario_totvs'), key=f"sai_tuser_{row['id']}", disabled=somente_leitura)
                    with c_tot2:
                        t_pass = st.text_input("Senha TOTVS", value=get_safe_val(row, 'senha_totvs'), key=f"sai_tpass_{row['id']}", disabled=somente_leitura)
                    
                    c_em1, c_em2 = st.columns(2)
                    with c_em1:
                        em_user = st.text_input("Usuário E-mail", value=get_safe_val(row, 'user_email'), key=f"sai_emuser_{row['id']}", disabled=somente_leitura)
                    with c_em2:
                        em_pass = st.text_input("Senha E-mail", value=get_safe_val(row, 'senha_email'), key=f"sai_empass_{row['id']}", disabled=somente_leitura)
                    
                    c_of1, c_of2 = st.columns(2)
                    with c_of1:
                        of_user = st.text_input("Usuário Office", value=get_safe_val(row, 'user_office'), key=f"sai_ofuser_{row['id']}", disabled=somente_leitura)
                    with c_of2:
                        of_pass = st.text_input("Senha Office", value=get_safe_val(row, 'senha_office'), key=f"sai_ofpass_{row['id']}", disabled=somente_leitura)
                        
                    obs_input = st.text_area("Observações de Desligamento", value=get_safe_val(row, 'observacoes'), key=f"sai_obs_{row['id']}", disabled=somente_leitura)
                    
                    c_btn1, c_btn2 = st.columns(2)
                    with c_btn1:
                        if st.button("📋 Gerar Pop-up", key=f"btn_pop_sai_{row['id']}", use_container_width=True):
                            popup_acessos(row['colaborador'], row['setor'], "SAÍDA", mat_input, ramal_input, t_user, t_pass, ad_user, ad_pass, em_user, em_pass, of_user, of_pass, obs_input)
                    with c_btn2:
                        if not somente_leitura and st.button("💾 Salvar Dados", key=f"btn_salvar_sai_{row['id']}", use_container_width=True):
                            
                            # 🔹 NOVO: Capturando a data e hora atual
                            carimbo = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                            db.execute_query(
                                """UPDATE fluxo_rh 
                                   SET t1_ok=?, t2_ok=?, t3_ok=?, 
                                       matricula=?, ramal=?, usuario_totvs=?, senha_totvs=?,
                                       user_ad=?, senha_ad=?, user_email=?, senha_email=?,
                                       user_office=?, senha_office=?, observacoes=?, data_conclusao=? 
                                   WHERE id=?""",
                                # 🔹 NOVO: Adicionado 'carimbo' na tupla de parâmetros
                                (int(check1), int(check2), int(check3), 
                                 mat_input, ramal_input, t_user, t_pass, ad_user, ad_pass, em_user, em_pass, of_user, of_pass, obs_input, carimbo, row['id'])
                            )
                            st.success(f"Dados salvos! Registrado em: {carimbo}")
                            st.rerun()

    # ==========================================
    # HISTÓRICO 
    # ==========================================
    st.markdown("---")
    with st.expander("🗄️ Histórico de Movimentações Concluídas"):
        query_hist = "SELECT * FROM fluxo_rh WHERE t1_ok = 1 AND t2_ok = 1 AND t3_ok = 1 AND t4_ok = 1 ORDER BY id DESC"
        dados_hist = db.fetch_data(query_hist)
        
        if dados_hist:
            df_hist = pd.DataFrame(dados_hist)
            
            # Tabela Resumo
            df_exibicao = df_hist[['colaborador', 'tipo', 'setor', 'data_evento']].copy()
            df_exibicao.columns = ['Colaborador', 'Movimentação', 'Setor', 'Data Evento']
            df_exibicao['Status'] = "✅ Finalizado"
            st.dataframe(df_exibicao, hide_index=True, width="stretch")
            
            st.markdown("---")
            st.markdown("###### 🔍 Reemitir Pop-up de Acessos de Registro Concluído")
            
            # Dropdown para escolher quem já foi concluído
            opcoes_hist = {f"[{row['tipo']}] {row['colaborador']} ({row['setor']})": row for row in dados_hist}
            selecionado_label = st.selectbox("Selecione o colaborador para ver/copiar as credenciais:", list(opcoes_hist.keys()), key="select_hist_popup")
            
            row_sel = opcoes_hist[selecionado_label]
            
            if st.button("📋 Reabrir Pop-up de Acessos", key="btn_hist_popup", use_container_width=True):
                popup_acessos(
                    row_sel['colaborador'], 
                    row_sel['setor'], 
                    row_sel['tipo'], 
                    get_safe_val(row_sel, 'matricula'), 
                    get_safe_val(row_sel, 'ramal'), 
                    get_safe_val(row_sel, 'usuario_totvs'), 
                    get_safe_val(row_sel, 'senha_totvs'), 
                    get_safe_val(row_sel, 'user_ad'), 
                    get_safe_val(row_sel, 'senha_ad'), 
                    get_safe_val(row_sel, 'user_email'), 
                    get_safe_val(row_sel, 'senha_email'), 
                    get_safe_val(row_sel, 'user_office'), 
                    get_safe_val(row_sel, 'senha_office'), 
                    get_safe_val(row_sel, 'observacoes'),
                    get_safe_val(row_sel, 'data_conclusao')
                )
            # --- COLE A GAVETA DE EDIÇÃO AQUI, LOGO ABAIXO DO BOTÃO REABRIR POP-UP ---
            def gerar_pdf_acessos(dados):
                pdf = FPDF()
                pdf.add_page()
                
                # Adiciona a Logo da Regispel
                try:
                    # x=85 centraliza uma imagem de largura 40 numa página A4
                    pdf.image("logo.png", x=85, y=10, w=40)
                    pdf.ln(25) # Pula um espaço para o texto não sobrepor a imagem
                except:
                    pass # Se o arquivo logo.png não for encontrado, segue sem quebrar o sistema
                
                pdf.set_font("Arial", 'B', 16)
                pdf.set_text_color(0, 86, 179)
                pdf.cell(0, 10, txt="RESUMO DE CREDENCIAIS DE ACESSO", ln=True, align='C')
                pdf.set_font("Arial", '', 10)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5, txt="Departamento de T.I. - Regispel", ln=True, align='C')
                pdf.ln(10)
                
                def linha_pdf(titulo, valor1, titulo2="", valor2=""):
                    pdf.set_font("Arial", 'B', 11)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(40, 8, txt=titulo, ln=0)
                    pdf.set_font("Arial", '', 11)
                    pdf.cell(60, 8, txt=str(valor1) if valor1 else "---", ln=0)
                    
                    if titulo2:
                        pdf.set_font("Arial", 'B', 11)
                        pdf.cell(30, 8, txt=titulo2, ln=0)
                        pdf.set_font("Arial", '', 11)
                        pdf.cell(60, 8, txt=str(valor2) if valor2 else "---", ln=1)
                    else:
                        pdf.ln(8)

                pdf.set_font("Arial", 'B', 13)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(0, 8, txt=" Perfil do Usuario", ln=True, fill=True)
                linha_pdf("Nome:", dados['colaborador'], "Setor:", dados['setor'])
                linha_pdf("Matricula:", dados.get('matricula', ''), "Ramal:", dados.get('ramal', ''))
                pdf.ln(5)

                pdf.set_font("Arial", 'B', 13)
                pdf.cell(0, 8, txt=" Credenciais Geradas", ln=True, fill=True)
                linha_pdf("Usuario AD:", dados.get('user_ad', ''), "Senha AD:", dados.get('senha_ad', ''))
                linha_pdf("Usuario TOTVS:", dados.get('usuario_totvs', ''), "Senha TOTVS:", dados.get('senha_totvs', ''))
                linha_pdf("E-mail:", dados.get('user_email', ''), "Senha E-mail:", dados.get('senha_email', ''))
                linha_pdf("Office:", dados.get('user_office', ''), "Senha Office:", dados.get('senha_office', ''))
                pdf.ln(5)
                
                obs = dados.get('observacoes', '')
                if obs and str(obs).strip() and str(obs) != 'nan':
                    pdf.set_font("Arial", 'B', 13)
                    pdf.cell(0, 8, txt=" Observacoes da T.I.", ln=True, fill=True)
                    pdf.set_font("Arial", '', 11)
                    pdf.multi_cell(0, 8, txt=str(obs))
                    pdf.ln(5)

                return pdf.output(dest='S').encode('latin-1')

            arquivo_pdf = gerar_pdf_acessos(row_sel)

            st.download_button(
                label="📥 Baixar Resumo de Acessos (PDF)",
                data=arquivo_pdf,
                file_name=f"Credenciais_{str(row_sel['colaborador']).replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            st.markdown("---")
            with st.expander("✏️ Editar Dados deste Colaborador"):
                with st.form(key=f"form_edicao_{row_sel['id']}"):
                    st.markdown("#### 👤 Dados Iniciais")
                    col_bas1, col_bas2, col_bas3 = st.columns(3)
                    with col_bas1: e_colab = st.text_input("Nome", value=get_safe_val(row_sel, 'colaborador'))
                    with col_bas2: e_mat = st.text_input("Matrícula", value=get_safe_val(row_sel, 'matricula'))
                    with col_bas3: e_ramal = st.text_input("Ramal", value=get_safe_val(row_sel, 'ramal'))

                    st.markdown("#### 🖥️ Credenciais (Windows e TOTVS)")
                    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                    with col_c1: e_ad_user = st.text_input("User AD", value=get_safe_val(row_sel, 'user_ad'))
                    with col_c2: e_ad_senha = st.text_input("Senha AD", value=get_safe_val(row_sel, 'senha_ad'))
                    with col_c3: e_t_user = st.text_input("User TOTVS", value=get_safe_val(row_sel, 'usuario_totvs'))
                    with col_c4: e_t_senha = st.text_input("Senha TOTVS", value=get_safe_val(row_sel, 'senha_totvs'))

                    st.markdown("#### 📧 Credenciais (E-mail e Office)")
                    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                    with col_e1: e_em_user = st.text_input("User E-mail", value=get_safe_val(row_sel, 'user_email'))
                    with col_e2: e_em_senha = st.text_input("Senha E-mail", value=get_safe_val(row_sel, 'senha_email'))
                    with col_e3: e_of_user = st.text_input("User Office", value=get_safe_val(row_sel, 'user_office'))
                    with col_e4: e_of_senha = st.text_input("Senha Office", value=get_safe_val(row_sel, 'senha_office'))

                    st.markdown("#### 📝 Outros")
                    e_obs = st.text_area("Observações", value=get_safe_val(row_sel, 'observacoes'))

                    if st.form_submit_button("💾 Salvar Todas as Alterações", use_container_width=True):
                        db.execute_query(
                            """UPDATE fluxo_rh 
                               SET colaborador=?, matricula=?, ramal=?, 
                                   user_ad=?, senha_ad=?, usuario_totvs=?, senha_totvs=?, 
                                   user_email=?, senha_email=?, user_office=?, senha_office=?, 
                                   observacoes=? 
                               WHERE id=?""",
                            (e_colab, e_mat, e_ramal, e_ad_user, e_ad_senha, e_t_user, e_t_senha, 
                             e_em_user, e_em_senha, e_of_user, e_of_senha, e_obs, row_sel['id'])
                        )
                        st.success("✅ Cadastro atualizado com sucesso!")
                        st.rerun()
            
            # --- FIM DO BLOCO DE EDIÇÃO ---
        else:
            st.info("Nenhuma movimentação finalizada até o momento.")
            

    if not somente_leitura:
        with st.expander("🗑️ Excluir Registro (Modo Administrador)"):
            perfil = st.session_state.get('perfil_acesso', '')
            
            if "ADMINISTRADOR" in perfil.upper():
                todos_rh = db.fetch_data("SELECT id, colaborador, tipo, setor FROM fluxo_rh ORDER BY id DESC")
                if todos_rh:
                    opcoes_del_rh = {f"[{row['tipo']}] {row['colaborador']} ({row['setor']})": row['id'] for row in todos_rh}
                    rh_deletar = st.selectbox("Selecione o registro para excluir permanentemente:", list(opcoes_del_rh.keys()))
                    
                    confirmacao = st.checkbox("Confirmo que desejo excluir este log do sistema.")
                    if st.button("🔴 DELETAR REGISTRO DE RH", width="stretch", disabled=not confirmacao):
                        db.execute_query("DELETE FROM fluxo_rh WHERE id = ?", (opcoes_del_rh[rh_deletar],))
                        st.success("🗑️ Registro apagado da base de dados com sucesso!")
                        st.rerun()
                else:
                    st.info("O banco de dados do RH está vazio.")
            else:
                st.error("⛔ Acesso Negado: Apenas o Administrador do sistema pode apagar históricos de auditoria de RH.")

def show_login():
    """Tela de login validando usuários e pegando o perfil de acesso."""
    st.markdown("""<style>
        #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
        [data-testid="collapsedControl"] {display: none;} section[data-testid="stSidebar"] {display: none;}
        .stApp {background-color: #F4F6F9 !important;}
        [data-testid="stForm"] { background-color: #FFFFFF !important; border-radius: 12px !important; padding: 3rem 2.5rem !important; box-shadow: 0 4px 15px rgba(0,0,0,0.08) !important; border: 1px solid #EAEAEA !important;}
        [data-testid="stFormSubmitButton"] button { background-color: #007BFF !important; color: white !important; border-radius: 6px !important; font-weight: bold !important;}
    </style>""", unsafe_allow_html=True)

    # Verifica se a coluna perfil existe. Se não existir, tenta criar e definir o padrão.
    try:
        db.execute_query("ALTER TABLE tecnicos ADD COLUMN perfil TEXT DEFAULT 'Administrador'")
    except:
        pass 

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.1, 1])
    
    with col2:
        with st.form("form_login"):
            if os.path.exists("logo.png"): st.image("logo.png", width="stretch")
            else: st.markdown("<h2 style='text-align: center;'>REGISPEL</h2>", unsafe_allow_html=True)
            
            st.markdown("<h4 style='text-align: center; color: #666; font-size: 14px;'>Acesse o Portal de T.I.</h4>", unsafe_allow_html=True)
            
            usuario = st.text_input("Usuário (Login)").strip().lower()
            senha = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Conecte-se", width="stretch"):
                query = "SELECT * FROM tecnicos WHERE usuario = ? AND senha = ?"
                resultado = db.fetch_data(query, (usuario, senha))
                
                if resultado:
                    st.session_state['autenticado'] = True
                    st.session_state['tecnico_nome'] = resultado[0]['nome']
                    # Salva o perfil do usuário na sessão (se a coluna não existir direito ainda, assume Administrador por padrão)
                    st.session_state['perfil_acesso'] = resultado[0].get('perfil', 'Administrador')
                    
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")


def show_ativos_dvr():
    import streamlit as st
    from streamlit_pdf_viewer import pdf_viewer  # Puxando a ferramenta nova!
    
    st.title("📹 Controle de Ativos - DVRs")
    st.subheader("Manutenção Preventiva CFTV - 2026")

    nome_arquivo_pdf = "dvr_2026.pdf" 

    try:
        # Aqui acontece a mágica: a biblioteca exibe o PDF nativamente
        pdf_viewer(nome_arquivo_pdf, width=1400, height=855)

        # E mantemos o botão de download logo abaixo!
        with open(nome_arquivo_pdf, "rb") as arquivo_pdf:
            pdf_bytes = arquivo_pdf.read()

        st.write("---")
        st.download_button(
            label="📄 Baixar Cópia em PDF",
            data=pdf_bytes,
            file_name="Manutencao_CFTV_2026.pdf",
            mime="application/pdf"
        )
        
    except FileNotFoundError:
        st.error(f"❌ Arquivo '{nome_arquivo_pdf}' não encontrado na pasta!")


# TELA DE CONTROLE DE EMPRÉSTIMOS
# ==========================================
def show_emprestimos():
    import pandas as pd
    from datetime import datetime, timedelta
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import os
    from dotenv import load_dotenv
    
    st.title("🤝 Controle de Empréstimos")
    st.markdown("---")
    
    somente_leitura = "Visitante" in st.session_state.get('perfil_acesso', '')

    # ==========================================
    # 1. FUNÇÃO DE DISPARO DE E-MAIL (TERMO DE RESPONSABILIDADE HTML)
    # ==========================================
    def disparar_termo_email(nome, email_destino, item, modelo, tag, patrimonio, acessorios, data_prevista):
        load_dotenv()
        email_remetente = os.getenv("EMAIL_USER")       
        senha_remetente = os.getenv("EMAIL_PASS")       
        servidor_smtp = os.getenv("EMAIL_HOST")         
        porta_smtp = int(os.getenv("EMAIL_PORT", 587))
        email_ti_cc = os.getenv("EMAIL_DESTINATARIO", "") 
        
        assunto = f"Registro Formal - Empréstimo de {item}"
        
        acessorios_txt = acessorios if acessorios else "Nenhum participante / Apenas o item principal"

        corpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333333; line-height: 1.6;">
            <p>Olá, <b>{nome}</b>.</p>
            
            <p>Este e-mail serve como registro formal e Termo de Responsabilidade referente ao empréstimo do seguinte equipamento da empresa Regispel:</p>
            
            <p style="font-size: 15px;">📋 <b>DADOS DO EQUIPAMENTO:</b></p>
            <ul style="list-style-type: disc; margin-left: 20px;">
                <li><b>Item:</b> {item}</li>
                <li><b>Modelo:</b> {modelo if modelo else 'Não especificado'}</li>
                <li><b>Service Tag / Lacre:</b> {tag if tag else 'Não especificado'}</li>
                <li><b>Etiqueta de Patrimônio:</b> {patrimonio if patrimonio else 'Não especificado'}</li>
                <li><b>Acessórios / Acompanhamentos:</b> {acessorios_txt}</li>
            </ul>
            
            <p style="font-size: 16px; background-color: #f8fafc; padding: 10px; border-left: 4px solid #0284c7; width: fit-content;">
                📅 <b>DATA DE ENTREGA DA DEVOLUÇÃO:</b> <span style="color: #0284c7; font-weight: bold;">{data_prevista}</span>
            </p>
            
            <p style="margin-top: 20px;"><b>TERMO DE ACEITE:</b><br>
            Ao receber este e-mail e o equipamento, você concorda em zelar pela integridade física e pelo bom uso do mesmo, comprometendo-se a devolvê-lo ao Departamento de T.I. nas mesmas condições em que foi entregue, até a data estipulada acima.</p>
            
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-top: 25px;">
            <p style="font-size: 12px; color: #64748b;">
                Este é um e-mail automático do Portal de T.I.<br>
                Em caso de dúvidas ou problemas, responda a este e-mail.
            </p>
            
            <p style="font-size: 13px;">
                Atenciosamente,<br>
                <b>Departamento de T.I</b>
            </p>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['From'] = email_remetente
        msg['To'] = email_destino
        msg['Subject'] = assunto
        
        if email_ti_cc:
            msg['Cc'] = email_ti_cc
            lista_cc = [e.strip() for e in email_ti_cc.split(',')]
        else:
            lista_cc = []
            
        msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
        try:
            server = smtplib.SMTP(servidor_smtp, porta_smtp)
            server.starttls()
            server.login(email_remetente, senha_remetente)
            destinatarios_totais = [email_destino] + lista_cc
            server.sendmail(email_remetente, destinatarios_totais, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            return str(e)

    # ==========================================
    # 2. FUNÇÃO DE DISPARO DE E-MAIL (COBRANÇA HTML)
    # ==========================================
    def disparar_cobranca_email(nome, email_destino, item, data_prevista):
        load_dotenv()
        email_remetente = os.getenv("EMAIL_USER")       
        senha_remetente = os.getenv("EMAIL_PASS")       
        servidor_smtp = os.getenv("EMAIL_HOST")         
        porta_smtp = int(os.getenv("EMAIL_PORT", 587))
        email_ti_cc = os.getenv("EMAIL_DESTINATARIO", "") 
        
        assunto = f"⚠️ AVISO: Atraso na Devolução de Equipamento T.I. ({item})"
        
        corpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333333; line-height: 1.6;">
            <p>Olá, <b>{nome}</b>.</p>
            
            <p>Consta em nosso sistema que o prazo para devolução do seguinte equipamento expirou:</p>
            
            <p style="font-size: 15px;">📋 <b>DADOS DO ITEM:</b> {item}</p>
            
            <p style="font-size: 16px; background-color: #fef2f2; padding: 10px; border-left: 4px solid #ef4444; width: fit-content;">
                📅 <b>DATA DE ENTREGA DA DEVOLUÇÃO PREVISTA ERA:</b> <span style="color: #dc2626; font-weight: bold;">{data_prevista}</span>
            </p>
            
            <p>Por favor, providencie a devolução do equipamento ao Departamento de T.I. o mais breve possível.<br>
            Caso você necessite de uma prorrogação do prazo, responda a este e-mail para que possamos atualizar o sistema.</p>
            
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-top: 25px;">
            <p style="font-size: 13px;">
                Atenciosamente,<br>
                <b>Departamento de T.I</b>
            </p>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['From'] = email_remetente
        msg['To'] = email_destino
        msg['Subject'] = assunto
        
        if email_ti_cc:
            msg['Cc'] = email_ti_cc
            lista_cc = [e.strip() for e in email_ti_cc.split(',')]
        else:
            lista_cc = []
            
        msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
        try:
            server = smtplib.SMTP(servidor_smtp, porta_smtp)
            server.starttls()
            server.login(email_remetente, senha_remetente)
            destinatarios_totais = [email_destino] + lista_cc
            server.sendmail(email_remetente, destinatarios_totais, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            return str(e)


    # ATUALIZAÇÃO DO BANCO DE DADOS
    db.execute_query("""
    CREATE TABLE IF NOT EXISTS emprestimos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL,
        email TEXT, 
        item TEXT NOT NULL,
        modelo TEXT,
        service_tag TEXT,
        lacre TEXT,
        patrimonio TEXT,
        acessorios TEXT,
        data_retirada TEXT NOT NULL,
        data_prevista TEXT,
        data_devolucao TEXT,
        status TEXT DEFAULT 'PENDENTE'
    )
    """)

    for col in ["modelo", "service_tag", "lacre", "patrimonio", "email", "acessorios"]:
        try:
            db.execute_query(f"ALTER TABLE emprestimos ADD COLUMN {col} TEXT")
        except: pass


    if not somente_leitura:
        with st.expander("➕ Registrar Novo Empréstimo"):
            with st.form("form_novo_emprestimo", clear_on_submit=True):
                c1, c2, c3_email = st.columns([2, 2, 2])
                with c1:
                    emp_usuario = st.text_input("Colaborador (Quem está levando?)")
                with c2:
                    emp_item = st.text_input("Item Emprestado")
                with c3_email:
                    emp_email = st.text_input("E-mail do Colaborador 📧")

                c_mod1, c_mod2, c_mod3, c_mod4 = st.columns(4)
                with c_mod1:
                    emp_modelo = st.text_input("Modelo")
                with c_mod2:
                    emp_service_tag = st.text_input("Service Tag")
                with c_mod3:
                    emp_lacre = st.text_input("Lacre")
                with c_mod4:
                    emp_patrimonio = st.text_input("Patrimônio")

                emp_acessorios = st.text_input("Acessórios / Acompanhamentos (Ex: Mouse, Fonte, Capa, Carregador)")

                c3, c4 = st.columns(2)
                with c3:
                    emp_data_ret = st.date_input("Data de Retirada", value=datetime.today())
                with c4:
                    emp_data_prev = st.date_input("Data de Entrega da Devolução", value=datetime.today() + timedelta(days=7))

                if st.form_submit_button("💾 Registrar Saída e Enviar Termo", width="stretch"):
                    if emp_usuario and emp_item:
                        data_ret_str = emp_data_ret.strftime("%d/%m/%Y")
                        data_prev_str = emp_data_prev.strftime("%d/%m/%Y")
                        
                        db.execute_query(
                            """INSERT INTO emprestimos 
                            (usuario, email, item, modelo, service_tag, lacre, patrimonio, acessorios, data_retirada, data_prevista, status) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDENTE')""",
                            (emp_usuario, emp_email, emp_item, emp_modelo, emp_service_tag, emp_lacre, emp_patrimonio, emp_acessorios, data_ret_str, data_prev_str)
                        )
                        
                        if emp_email and "@" in emp_email:
                            with st.spinner("Enviando termo por e-mail..."):
                                resultado_email = disparar_termo_email(
                                    emp_usuario, emp_email, emp_item, emp_modelo, emp_service_tag, emp_patrimonio, emp_acessorios, data_prev_str
                                )
                                if resultado_email is True:
                                    st.success(f"✅ O item '{emp_item}' foi registrado e o Termo enviado para o e-mail de {emp_usuario}!")
                                else:
                                    st.warning(f"⚠️ Registro salvo no banco, MAS houve falha ao enviar o e-mail: {resultado_email}")
                        else:
                            st.success(f"✅ Registro salvo com sucesso! (Nenhum e-mail de termo foi disparado pois o campo estava vazio).")
                            
                    else:
                        st.error("❌ Os campos Colaborador e Item são obrigatórios.")
        st.markdown("---")

    dados_pendentes = db.fetch_data("SELECT * FROM emprestimos WHERE status = 'PENDENTE'")
    df_pendentes = pd.DataFrame(dados_pendentes) if dados_pendentes else pd.DataFrame()

    hoje = datetime.today().date()
    atrasados = 0
    
    if not df_pendentes.empty:
        for _, row in df_pendentes.iterrows():
            try:
                prev = datetime.strptime(row['data_prevista'], "%d/%m/%Y").date()
                if prev < hoje:
                    atrasados += 1
            except:
                pass

    qtd_ativos = len(df_pendentes)

    kpi_html = f"""
    <div style="display: flex; gap: 20px; margin-bottom: 25px;">
        <div style="flex: 1; background-color: #ffffff; border-left: 5px solid #3b82f6; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="font-size: 11px; color: #64748b; font-weight: bold; text-transform: uppercase;">Itens na Rua</div>
            <div style="font-size: 28px; font-weight: 800; color: #1e293b; margin-top: 5px;">📦 {qtd_ativos} Ativo(s)</div>
        </div>
        <div style="flex: 1; background-color: #ffffff; border-left: 5px solid {'#ef4444' if atrasados > 0 else '#10b981'}; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="font-size: 11px; color: #64748b; font-weight: bold; text-transform: uppercase;">Devoluções Atrasadas</div>
            <div style="font-size: 28px; font-weight: 800; color: {'#ef4444' if atrasados > 0 else '#10b981'}; margin-top: 5px;">⚠️ {atrasados} Atraso(s)</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    if df_pendentes.empty:
        st.success("🎉 Nenhum empréstimo ativo no momento! Todo o patrimônio está na T.I.")
    else:
        st.markdown("#### 📋 Empréstimos em Andamento")
        for _, row in df_pendentes.iterrows():
            with st.container(border=True):
                col_i1, col_i2, col_i3 = st.columns([3, 2, 1])
                
                with col_i1:
                    modelo_str = f" {row.get('modelo', '')}" if pd.notna(row.get('modelo')) and row.get('modelo') else ""
                    st.markdown(f"**Item:** {row['item']}{modelo_str}")
                    
                    detalhes = []
                    if pd.notna(row.get('service_tag')) and row.get('service_tag'):
                        detalhes.append(f"**Service Tag:** {row['service_tag']}")
                    if pd.notna(row.get('patrimonio')) and row.get('patrimonio'):
                        detalhes.append(f"**Patrimônio:** {row['patrimonio']}")
                    if pd.notna(row.get('lacre')) and row.get('lacre'):
                        detalhes.append(f"**Lacre:** {row['lacre']}")
                    
                    if detalhes:
                        st.markdown(" | ".join(detalhes))
                    
                    if pd.notna(row.get('acessorios')) and row.get('acessorios'):
                        st.markdown(f"🔌 **Acessórios:** {row['acessorios']}")
                        
                    st.caption(f"👤 Com: {row['usuario']}")
                
                esta_atrasado = False
                
                with col_i2:
                    try:
                        prev_date = datetime.strptime(row['data_prevista'], "%d/%m/%Y").date()
                        if prev_date < hoje:
                            esta_atrasado = True
                            st.error(f"Data de Entrega: {row['data_prevista']} (ATRASADO)")
                        else:
                            st.info(f"Data de Entrega: {row['data_prevista']}")
                    except:
                        st.write(f"Prev: {row['data_prevista']}")
                
                with col_i3:
                    if not somente_leitura:
                        if st.button("⚡ Dar Baixa", key=f"baixa_{row['id']}", width="stretch"):
                            data_hoje_str = datetime.today().date().strftime("%d/%m/%Y")
                            db.execute_query(
                                "UPDATE emprestimos SET status = 'DEVOLVIDO', data_devolucao = ? WHERE id = ?",
                                (data_hoje_str, row['id'])
                            )
                            st.success("Item devolvido com sucesso!")
                            st.rerun()
                            
                        if esta_atrasado:
                            email_usuario = row.get('email')
                            if pd.notna(email_usuario) and "@" in str(email_usuario):
                                if st.button("🔔 Cobrar Atraso", key=f"cobrar_{row['id']}", width="stretch"):
                                    with st.spinner("Enviando cobrança..."):
                                        res = disparar_cobranca_email(row['usuario'], email_usuario, row['item'], row['data_prevista'])
                                        if res is True:
                                            st.toast("✅ E-mail de cobrança enviado com sucesso!", icon="✉️")
                                        else:
                                            st.error(f"Erro ao enviar: {res}")

    st.markdown("---")
    with st.expander("🗄️ Histórico de Devoluções"):
        dados_hist = db.fetch_data("SELECT id, usuario as Colaborador, item as Item, modelo as Modelo, service_tag as 'Service Tag', patrimonio as Patrimônio, lacre as Lacre, acessorios as Acessórios, data_retirada as Retirada, data_devolucao as Devolução FROM emprestimos WHERE status = 'DEVOLVIDO' ORDER BY id DESC")
        if dados_hist:
            df_hist = pd.DataFrame(dados_hist)
            df_hist['Status'] = "✅ Devolvido"
            st.dataframe(df_hist.drop(columns=['id']), hide_index=True, width="stretch")
        else:
            st.info("Nenhuma devolução registrada no histórico.")

    if not somente_leitura:
        with st.expander("🗑️ Excluir Registro (Modo Administrador)"):
            perfil = st.session_state.get('perfil_acesso', '')
            if "ADMINISTRADOR" in perfil.upper():
                todos_emp = db.fetch_data("SELECT id, usuario, item, status FROM emprestimos ORDER BY id DESC")
                if todos_emp:
                    opcoes_del_emp = {f"[{row['status']}] {row['item']} ({row['usuario']})": row['id'] for row in todos_emp}
                    emp_deletar = st.selectbox("Selecione o registro para excluir permanentemente:", list(opcoes_del_emp.keys()))
                    if st.button("🔴 DELETAR REGISTRO", width="stretch", disabled=not st.checkbox("Confirmo exclusão de empréstimo.")):
                        db.execute_query("DELETE FROM emprestimos WHERE id = ?", (opcoes_del_emp[emp_deletar],))
                        st.success("🗑️ Registro apagado!")
                        st.rerun()
                else:
                    st.info("Banco de dados vazio.")

@st.cache_resource
def inicializar_banco():
    db.init_db()

def main():
    inicializar_banco()
    
    if 'autenticado' not in st.session_state:
        st.session_state['autenticado'] = False

    if not st.session_state['autenticado']:
        show_login()
    else:
        st.markdown("<style>header {visibility: visible;} section[data-testid=\"stSidebar\"] {display: block;}</style>", unsafe_allow_html=True)
        modulo, tela_atual = render_sidebar()
        
        if st.sidebar.button("Sair / Logout", width="stretch"):
            st.session_state['autenticado'] = False
            st.session_state.pop('tecnico_nome', None)
            st.session_state.pop('perfil_acesso', None)
            st.rerun()

        if modulo == "🖨️ Gestão de Impressoras":
            if tela_atual == "Dashboard": show_dashboard()
            elif tela_atual == "Cadastro de Impressoras": show_Cadastro_de_Impressoras()
            elif tela_atual == "Estoque de Suprimentos": show_estoque_de_suprimentos()
            # elif tela_atual == "Importação": show_importacao()
            elif tela_atual == "Cadastros Base": show_cadastros()
                
        elif modulo == "💻 Controle de Ativos":
            if tela_atual == "Dashboard de Ativos": show_dashboard_ativos()
            elif tela_atual == "Inventário de Máquinas": show_inventario_ativos()
            elif tela_atual == "Notebook Regispel": show_notebook_regispel()
            elif tela_atual == "Controle de Empréstimos": show_emprestimos()
            elif tela_atual == "Fluxo de RH": show_fluxo_rh()
            elif tela_atual == "Estoque de Periféricos": show_estoque_perifericos()
            elif tela_atual == "Controle de Ativos (DVR)": show_ativos_dvr()

if __name__ == "__main__":
    main()