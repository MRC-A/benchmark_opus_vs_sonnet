@echo off
REM Lance l'application dans le navigateur par defaut.
cd /d "%~dp0"
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
python -m streamlit run app.py
