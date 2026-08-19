import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import database as db

# ===================================================
# 1. FUNÇÃO DE ALERTA DE ESTOQUE (Gestão)
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
    query = """
        SELECT s.categoria, s.cor_tipo, COALESCE(e.quantidade, 0) as qtd, COALESCE(e.obs_solicitacao, '') as obs 
        FROM suprimentos s 
        LEFT JOIN estoque_suprimentos e ON s.id = e.suprimento_id 
        WHERE qtd <= 2 ORDER BY s.categoria
    """
    itens = db.fetch_data(query)
    
    itens_criticos = [i for i in itens if i['obs'].strip() == '' and i['qtd'] <= 1]
    itens_atencao = [i for i in itens if i['obs'].strip() == '' and i['qtd'] == 2]
    itens_comprados = [i for i in itens if i['obs'].strip() != '']
    
    if not itens_criticos and not itens_atencao and not itens_comprados:
        print("Estoque perfeito. Nenhum email a enviar.")
        return

    # Monta o cabeçalho do e-mail
    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = ", ".join(destinos)
    msg['Subject'] = "📊 [REPORT AUTOMÁTICO] Posição de Estoque de Suprimentos"
    
    corpo_html = "<html><body style='font-family: Arial, sans-serif; color: #333; line-height: 1.5;'>"
    corpo_html += "<h2 style='color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; max-width: 750px;'>Status Atual do Estoque de Suprimentos</h2>"
    
    if itens_criticos:
        corpo_html += """
        <h3 style='color: #b91c1c; margin-top: 25px;'>🔴 AÇÃO URGENTE: Itens Críticos / Zerados</h3>
        <table style='width: 600px; border-collapse: collapse; border: 1px solid #fca5a5;'>
            <tr style='background-color: #fee2e2; border-bottom: 2px solid #ef4444;'>
                <th style='padding: 10px; text-align: left; width: 280px;'>Modelo / Insumo</th>
                <th style='padding: 10px; text-align: left; width: 220px;'>Cor / Tipo</th>
                <th style='padding: 10px; text-align: center; width: 100px;'>Qtd Atual</th>
            </tr>
        """
        for i in itens_criticos:
            corpo_html += f"""
            <tr style='border-bottom: 1px solid #fca5a5;'>
                <td style='padding: 10px; font-weight: bold;'>{i['categoria']}</td>
                <td style='padding: 10px;'>{i['cor_tipo']}</td>
                <td style='padding: 10px; text-align: center; color: #b91c1c; font-weight: bold; font-size: 16px;'>{i['qtd']}</td>
            </tr>
            """
        corpo_html += "</table>"

    if itens_atencao:
        corpo_html += """
        <h3 style='color: #a16207; margin-top: 25px;'>⚠️ ATENÇÃO: Chegando no Ponto de Pedido</h3>
        <table style='width: 600px; border-collapse: collapse; border: 1px solid #fde047;'>
            <tr style='background-color: #fef08a; border-bottom: 2px solid #eab308;'>
                <th style='padding: 10px; text-align: left; width: 280px;'>Modelo / Insumo</th>
                <th style='padding: 10px; text-align: left; width: 220px;'>Cor / Tipo</th>
                <th style='padding: 10px; text-align: center; width: 100px;'>Qtd Atual</th>
            </tr>
        """
        for i in itens_atencao:
            corpo_html += f"""
            <tr style='border-bottom: 1px solid #fde047;'>
                <td style='padding: 10px; font-weight: bold;'>{i['categoria']}</td>
                <td style='padding: 10px;'>{i['cor_tipo']}</td>
                <td style='padding: 10px; text-align: center; color: #a16207; font-weight: bold; font-size: 16px;'>{i['qtd']}</td>
            </tr>
            """
        corpo_html += "</table>"
        
    if itens_comprados:
        corpo_html += """
        <h3 style='color: #1d4ed8; margin-top: 35px;'>🛒 AGUARDANDO CHEGADA: Pedidos Já Solicitados</h3>
        <table style='width: 750px; border-collapse: collapse; border: 1px solid #bfdbfe;'>
            <tr style='background-color: #eff6ff; border-bottom: 2px solid #3b82f6;'>
                <th style='padding: 10px; text-align: left; width: 250px;'>Modelo / Insumo</th>
                <th style='padding: 10px; text-align: left; width: 200px;'>Cor / Tipo</th>
                <th style='padding: 10px; text-align: center; width: 100px;'>Qtd Atual</th>
                <th style='padding: 10px; text-align: left; width: 200px;'>Status do Pedido</th>
            </tr>
        """
        for i in itens_comprados:
            corpo_html += f"""
            <tr style='border-bottom: 1px solid #bfdbfe;'>
                <td style='padding: 10px; font-weight: bold;'>{i['categoria']}</td>
                <td style='padding: 10px;'>{i['cor_tipo']}</td>
                <td style='padding: 10px; text-align: center; color: #1e3a8a; font-weight: bold; font-size: 16px;'>{i['qtd']}</td>
                <td style='padding: 10px; color: #3b82f6; font-style: italic;'>{i['obs']}</td>
            </tr>
            """
        corpo_html += "</table>"
        
    corpo_html += """
        <br><hr style='border: 0; border-top: 1px solid #e2e8f0; margin-top: 30px; max-width: 750px;'>
        <p style='font-size: 11px; color: #94a3b8; max-width: 750px; text-align: center;'>Este é um e-mail automático gerado pelo sistema de gestão de ativos Regispel.</p>
    </body></html>
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
# EXECUÇÃO DIRETA (PARA O AGENDADOR DE TAREFAS)
# ===================================================
if __name__ == "__main__":
    from datetime import datetime
    
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