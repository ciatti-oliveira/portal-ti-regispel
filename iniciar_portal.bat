@echo off
echo Iniciando o Portal T.I. e o Robo de E-mail...

:: 1. Muda para a unidade C:
C:

:: 2. Entra na pasta exata do seu projeto
cd "C:\Users\loliveira\Documents\sistema-impressoras"

:: 3. Executa o Portal (Streamlit) em uma nova janela
start "Portal TI" streamlit run app.py

:: 4. Executa o Robo de E-mail na janela atual
echo.
echo Iniciando o script robo_email.py...
python robo_email.py

:: 5. Pausa a tela para voce conseguir ler possiveis erros
pause