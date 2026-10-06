import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import database as db

# ===================================================
# 1. FUNÇÃO DE ALERTA DE ESTOQUE (Gestão) - NOVO VISUAL
# ===================================================
def rodar_robo():
    print(f"\n[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Iniciando disparo do relatório de estoque...")
    load_dotenv(override=True)
    
    server = os.getenv("EMAIL_HOST")
    porta = os.getenv("EMAIL_PORT")
    user = os.getenv("EMAIL_USER")
    senha = os.getenv("EMAIL_PASS")
    destino_raw = os.getenv("EMAIL_DESTINATARIO")
    
    if not all([server, porta, user, senha, destino_raw]):
        print("Erro: .env incompleto.")
        return

    destinos = [e.strip() for e in destino_raw.replace(";", ",").split(",") if e.strip()]
    
    # Conecta no banco de dados local
    db.init_db() 
    
    # 🧠 Busca todos os itens críticos (<=2) OU que já foram solicitados (obs não vazia)
    query = """
        SELECT s.categoria, s.cor_tipo, COALESCE(e.quantidade, 0) as qtd, COALESCE(e.obs_solicitacao, '') as obs 
        FROM suprimentos s 
        LEFT JOIN estoque_suprimentos e ON s.id = e.suprimento_id 
        WHERE COALESCE(e.quantidade, 0) <= 2 OR COALESCE(e.obs_solicitacao, '') != ''
        ORDER BY s.categoria
    """
    itens = db.fetch_data(query)
    
    itens_criticos = [i for i in itens if i['obs'].strip() == '' and i['qtd'] <= 1]
    itens_atencao = [i for i in itens if i['obs'].strip() == '' and i['qtd'] == 2]
    itens_comprados = [i for i in itens if i['obs'].strip() != '']
    
    if not itens_criticos and not itens_atencao and not itens_comprados:
        print("🟢 Tudo OK! Nenhum item crítico, em atenção ou pendente para envio de e-mail.")
        return

    # Monta o cabeçalho do e-mail
    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = ", ".join(destinos)
    msg['Subject'] = "📊 [REPORT AUTOMÁTICO] Posição de Estoque de Suprimentos"
    
    # --- HTML COM CABEÇALHO CORPORATIVO ---
    corpo_html = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5; background-color: #f8fafc; padding: 20px;">
        <div style="max-width: 800px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            
            <div style="background-color: #0369a1; padding: 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; letter-spacing: 1px;">PORTAL DE T.I. - REGISPEL</h1>
                <p style="color: #bae6fd; margin: 5px 0 0 0; font-size: 14px;">Report Semanal de Suprimentos</p>
            </div>
            
            <div style="padding: 30px;">
                <h2 style="color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-top: 0;">Status Atual do Estoque</h2>
                <p style="color: #475569;">Abaixo está a fotografia atualizada dos suprimentos de impressão que exigem monitoramento nesta semana.</p>
    """
    
    if itens_criticos:
        corpo_html += """
                <h3 style="color: #b91c1c; margin-top: 25px;">🔴 AÇÃO URGENTE: Itens Críticos / Zerados</h3>
                <table style="width:100%; border-collapse: collapse; margin-top: 10px; border: 1px solid #fca5a5; border-radius: 5px; overflow: hidden;">
                    <tr style="background-color: #fee2e2; border-bottom: 2px solid #ef4444;">
                        <th style="padding: 12px; text-align: left;">Modelo / Insumo</th>
                        <th style="padding: 12px; text-align: left;">Cor / Tipo</th>
                        <th style="padding: 12px; text-align: center; width: 100px;">Qtd Atual</th>
                    </tr>
        """
        for item in itens_criticos:
            corpo_html += f"""
                    <tr style="border-bottom: 1px solid #fca5a5;">
                        <td style="padding: 12px; font-weight: bold;">{item['categoria']}</td>
                        <td style="padding: 12px;">{item['cor_tipo']}</td>
                        <td style="padding: 12px; text-align: center; color: #b91c1c; font-weight: bold; font-size: 16px;">{item['qtd']}</td>
                    </tr>
            """
        corpo_html += "</table>"

    if itens_atencao:
        corpo_html += """
                <h3 style="color: #b45309; margin-top: 25px;">⚠️ ATENÇÃO: Chegando no Ponto de Pedido</h3>
                <table style="width:100%; border-collapse: collapse; margin-top: 10px; border: 1px solid #fde047; border-radius: 5px; overflow: hidden;">
                    <tr style="background-color: #fef08a; border-bottom: 2px solid #eab308;">
                        <th style="padding: 12px; text-align: left;">Modelo / Insumo</th>
                        <th style="padding: 12px; text-align: left;">Cor / Tipo</th>
                        <th style="padding: 12px; text-align: center; width: 100px;">Qtd Atual</th>
                    </tr>
        """
        for item in itens_atencao:
            corpo_html += f"""
                    <tr style="border-bottom: 1px solid #fde047;">
                        <td style="padding: 12px; font-weight: bold;">{item['categoria']}</td>
                        <td style="padding: 12px;">{item['cor_tipo']}</td>
                        <td style="padding: 12px; text-align: center; color: #b45309; font-weight: bold; font-size: 16px;">{item['qtd']}</td>
                    </tr>
            """
        corpo_html += "</table>"
        
    if itens_comprados:
        corpo_html += """
                <h3 style="color: #1d4ed8; margin-top: 35px;">🛒 AGUARDANDO CHEGADA: Pedidos Já Solicitados</h3>
                <table style="width:100%; border-collapse: collapse; margin-top: 10px; border: 1px solid #bfdbfe; border-radius: 5px; overflow: hidden;">
                    <tr style="background-color: #eff6ff; border-bottom: 2px solid #3b82f6;">
                        <th style="padding: 12px; text-align: left;">Modelo / Insumo</th>
                        <th style="padding: 12px; text-align: left;">Cor / Tipo</th>
                        <th style="padding: 12px; text-align: center; width: 80px;">Qtd Atual</th>
                        <th style="padding: 12px; text-align: left;">Status do Pedido</th>
                    </tr>
        """
        for item in itens_comprados:
            corpo_html += f"""
                    <tr style="border-bottom: 1px solid #bfdbfe;">
                        <td style="padding: 12px; font-weight: bold;">{item['categoria']}</td>
                        <td style="padding: 12px;">{item['cor_tipo']}</td>
                        <td style="padding: 12px; text-align: center; color: #1e3a8a; font-weight: bold; font-size: 16px;">{item['qtd']}</td>
                        <td style="padding: 12px; color: #3b82f6; font-style: italic;">{item['obs']}</td>
                    </tr>
            """
        corpo_html += "</table>"

    # --- MINI DASHBOARD: CONSUMO DOS ÚLTIMOS 7 DIAS ---
    data_limite = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    try:
        query_semana = f"SELECT departamento, item, quantidade FROM historico_saidas WHERE data_saida >= '{data_limite}'"
        saidas_semana = db.fetch_data(query_semana)
    except Exception as e:
        saidas_semana = []
        
    if saidas_semana:
        consumo_por_dpto = {}
        consumo_por_item = {}
        total_semana = 0
        
        for saida in saidas_semana:
            qtd = int(saida.get('quantidade', 0) if isinstance(saida, dict) else getattr(saida, 'quantidade', 0))
            dpto = saida.get('departamento', '-') if isinstance(saida, dict) else getattr(saida, 'departamento', '-')
            item = saida.get('item', '-') if isinstance(saida, dict) else getattr(saida, 'item', '-')
            
            consumo_por_dpto[dpto] = consumo_por_dpto.get(dpto, 0) + qtd
            consumo_por_item[item] = consumo_por_item.get(item, 0) + qtd
            total_semana += qtd
            
        top_dpto = max(consumo_por_dpto, key=consumo_por_dpto.get) if consumo_por_dpto else "-"
        top_dpto_qtd = consumo_por_dpto.get(top_dpto, 0)
        top_item = max(consumo_por_item, key=consumo_por_item.get) if consumo_por_item else "-"
        top_item_qtd = consumo_por_item.get(top_item, 0)

        corpo_html += f"""
                <h3 style="color: #15803d; margin-top: 40px; border-top: 2px dashed #e2e8f0; padding-top: 30px;">📦 MOVIMENTAÇÃO DA SEMANA (ÚLTIMOS 7 DIAS)</h3>
                
                <table style="width:100%; margin-bottom: 20px; border-collapse: separate; border-spacing: 15px 0; margin-left: -15px; margin-right: -15px;">
                    <tr>
                        <td style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 20px 10px; text-align: center; border-radius: 8px; width: 33%; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <span style="color: #166534; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Total Retirado</span><br>
                            <span style="color: #15803d; font-size: 28px; font-weight: bold; display: block; margin: 8px 0;">{total_semana}</span>
                            <span style="color: #166534; font-size: 12px;">unidades</span>
                        </td>
                        <td style="background-color: #eff6ff; border: 1px solid #bfdbfe; padding: 20px 10px; text-align: center; border-radius: 8px; width: 33%; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <span style="color: #1e3a8a; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Maior Consumidor</span><br>
                            <span style="color: #1d4ed8; font-size: 18px; font-weight: bold; display: block; margin: 8px 0;">{top_dpto}</span>
                            <span style="color: #3b82f6; font-size: 12px;">({top_dpto_qtd} un.)</span>
                        </td>
                        <td style="background-color: #fffbeb; border: 1px solid #fde68a; padding: 20px 10px; text-align: center; border-radius: 8px; width: 33%; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                            <span style="color: #92400e; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Item Mais Pedido</span><br>
                            <span style="color: #d97706; font-size: 14px; font-weight: bold; display: block; margin: 8px 0; line-height: 1.2;">{top_item}</span>
                            <span style="color: #f59e0b; font-size: 12px;">({top_item_qtd} un.)</span>
                        </td>
                    </tr>
                </table>

                <table style="width:100%; border-collapse: collapse; margin-top: 15px; border: 1px solid #bbf7d0; border-radius: 5px; overflow: hidden;">
                    <tr style="background-color: #f0fdf4; border-bottom: 2px solid #22c55e;">
                        <th style="padding: 12px; text-align: left;">Departamento Destino</th>
                        <th style="padding: 12px; text-align: left;">Item / Modelo Consumido</th>
                        <th style="padding: 12px; text-align: center; width: 100px;">Qtd Entregue</th>
                    </tr>
        """
        for saida in saidas_semana:
            dpto_val = saida.get('departamento', '-') if isinstance(saida, dict) else getattr(saida, 'departamento', '-')
            item_val = saida.get('item', '-') if isinstance(saida, dict) else getattr(saida, 'item', '-')
            qtd_val = saida.get('quantidade', 0) if isinstance(saida, dict) else getattr(saida, 'quantidade', 0)
            
            corpo_html += f"""
                    <tr style="border-bottom: 1px solid #bbf7d0;">
                        <td style="padding: 12px; font-weight: bold;">{dpto_val}</td>
                        <td style="padding: 12px;">{item_val}</td>
                        <td style="padding: 12px; text-align: center; color: #166534; font-weight: bold; font-size: 16px;">{qtd_val}</td>
                    </tr>
            """
        corpo_html += "</table>"
    else:
        corpo_html += """
                <h3 style="color: #15803d; margin-top: 40px; border-top: 2px dashed #e2e8f0; padding-top: 30px;">📦 MOVIMENTAÇÃO DA SEMANA (ÚLTIMOS 7 DIAS)</h3>
                <p style="color: #64748b; font-style: italic; background-color: #f1f5f9; padding: 15px; border-radius: 5px; text-align: center;">
                    Nenhuma saída de suprimento foi registrada nos últimos 7 dias.
                </p>
        """
    
    corpo_html += """
            </div>
            <div style="background-color: #f1f5f9; padding: 30px; text-align: center; border-top: 1px solid #e2e8f0;">
                <p style="color: #64748b; font-size: 14px; margin-bottom: 20px;">Este relatório foi gerado e enviado automaticamente pelo sistema.</p>
                <a href="https://ti-regispel.streamlit.app" style="display: inline-block; padding: 14px 28px; background-color: #0369a1; color: #ffffff; text-decoration: none; font-weight: bold; border-radius: 6px; letter-spacing: 0.5px;">Acessar Portal de T.I.</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
    
    try:
        smtp = smtplib.SMTP(server, int(porta))
        smtp.starttls()
        smtp.login(user, senha)
        smtp.sendmail(user, destinos, msg.as_string())
        smtp.quit()
        print("✅ Report de estoque automático enviado com sucesso!")
    except Exception as e:
        print(f"❌ Falha ao enviar report de estoque: {e}")

# ===================================================
# 2. FUNÇÃO DE COBRANÇA AUTOMÁTICA (Usuários)
# ===================================================
def cobrar_emprestimos_atrasados():
    print(f"\n[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Iniciando varredura de empréstimos atrasados...")
    load_dotenv(override=True)
    
    server = os.getenv("EMAIL_HOST")
    porta = os.getenv("EMAIL_PORT")
    user = os.getenv("EMAIL_USER")
    senha = os.getenv("EMAIL_PASS")
    destino_ti_raw = os.getenv("EMAIL_DESTINATARIO", "") 
    
    if not all([server, porta, user, senha]):
        print("Erro: .env incompleto para enviar cobranças.")
        return

    lista_cc = [e.strip() for e in destino_ti_raw.replace(";", ",").split(",") if e.strip()]

    db.init_db()
    pendentes = db.fetch_data("SELECT usuario, email, item, data_prevista FROM emprestimos WHERE status = 'PENDENTE'")
    
    if not pendentes:
        print("Nenhum equipamento na rua no momento.")
        return

    hoje = datetime.today().date()
    qtd_cobrancas = 0

    for linha in pendentes:
        usuario = linha.get('usuario')
        email_destino = linha.get('email')
        item = linha.get('item')
        data_prev_str = linha.get('data_prevista')

        if not email_destino or "@" not in str(email_destino):
            continue 

        try:
            data_prevista = datetime.strptime(data_prev_str, "%d/%m/%Y").date()
            
            if data_prevista < hoje:
                print(f"⚠️ Atraso de {usuario} ({item}). Disparando cobrança...")
                
                assunto = f"⚠️ Lembrete de Devolução de Equipamento T.I. ({item})"
                
                corpo_html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; color: #333333; line-height: 1.6;">
                    <p>Olá, <b>{usuario}</b>.</p>
                    
                    <p>Consta em nosso sistema que o prazo para devolução do seguinte equipamento expirou:</p>
                    
                    <p style="font-size: 15px;">📋 <b>DADOS DO ITEM:</b> {item}</p>
                    
                    <p style="font-size: 16px; background-color: #fef2f2; padding: 10px; border-left: 4px solid #ef4444; width: fit-content;">
                        📅 <b>DATA DE ENTREGA DA DEVOLUÇÃO PREVISTA ERA:</b> <span style="color: #dc2626; font-weight: bold;">{data_prev_str}</span>
                    </p>
                    
                    <p>Por favor, providencie a devolução do equipamento ao Departamento de T.I. o mais breve possível.<br>
                    Caso você já tenha devolvido ou necessite de uma prorrogação do prazo, responda a este e-mail para que possamos atualizar o sistema.</p>
                    
                    <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-top: 25px;">
                    <p style="font-size: 13px;">
                        Atenciosamente,<br>
                        <b>Departamento de Tecnologia da Informação</b>
                    </p>
                </body>
                </html>
                """

                msg = MIMEMultipart()
                msg['From'] = user
                msg['To'] = email_destino
                msg['Subject'] = assunto
                
                if lista_cc:
                    msg['Cc'] = ", ".join(lista_cc)

                msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))

                smtp = smtplib.SMTP(server, int(porta))
                smtp.starttls()
                smtp.login(user, senha)
                
                destinatarios_totais = [email_destino] + lista_cc
                smtp.sendmail(user, destinatarios_totais, msg.as_string())
                smtp.quit()
                
                qtd_cobrancas += 1
                
        except Exception as e:
            print(f"Erro ao processar cobrança do item {item}: {e}")
            
    print(f"Varredura concluída. {qtd_cobrancas} e-mail(s) de cobrança enviado(s) hoje.")


# ===================================================
# EXECUÇÃO DIRETA (PARA O AGENDADOR DE TAREFAS / GITHUB ACTIONS)
# ===================================================
if __name__ == "__main__":
    
    print("Iniciando rotinas do Robô...")
    
    # 1º A cobrança roda TODO DIA
    cobrar_emprestimos_atrasados()
    
    # 2º O Relatório checa que dia é hoje (0 = Segunda, 1 = Terça, 2 = Quarta...)
    dia_da_semana = datetime.today().weekday()
    
    if dia_da_semana == 0:  # Se for igual a 0, é Segunda-feira!
        print("Hoje é segunda-feira! Disparando o relatório de estoque para a gestão...")
        rodar_robo()
    else:
        print("Hoje não é segunda-feira. O relatório de estoque semanal foi ignorado.")
    
    print("\nTodas as rotinas finalizadas com sucesso.")