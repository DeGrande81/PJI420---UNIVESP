# Dashboard de alagamento de Sorocaba — instalação e correções

## Diagnóstico

O arquivo original compila, mas não inicia no VS Code quando o ambiente Python não possui as bibliotecas externas. Na verificação do ambiente, os erros foram:

```text
ModuleNotFoundError: No module named 'streamlit'
ModuleNotFoundError: No module named 'folium'
ModuleNotFoundError: No module named 'streamlit_folium'
```

`pandas` e `numpy` estavam disponíveis, mas `numpy` não era usado pelo dashboard e foi removido da versão corrigida.

## Erros/problemas e solução

1. **Dependências não instaladas**
   - O script importa `streamlit`, `folium` e `streamlit_folium`.
   - Solução: abrir o terminal na pasta do projeto e instalar pelo mesmo interpretador selecionado no VS Code:

   ```bash
   python -m pip install -r requirements.txt
   ```

   No Linux/macOS, se o comando `python` não existir, use:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. **Interpretador Python diferente do terminal**
   - É comum instalar a biblioteca em um Python e o VS Code executar outro.
   - Solução: `Ctrl+Shift+P` → **Python: Select Interpreter** → escolha o ambiente do projeto. Depois confira:

   ```bash
   python -c "import sys; print(sys.executable)"
   python -m pip show streamlit folium streamlit-folium
   ```

3. **Execução incorreta do Streamlit**
   - Um aplicativo Streamlit não deve ser executado apenas com `python dashboard_alagamento_sorocaba.py`.
   - Solução:

   ```bash
   python -m streamlit run dashboard_alagamento_sorocaba.py
   ```

4. **Caminhos fixos que não existem no computador**
   - O código original procurava os CSVs somente em `/home/workdir/artifacts` e `/home/workdir/attachments`.
   - Solução aplicada: a versão corrigida procura primeiro na pasta do script, depois em `dados/` e, por compatibilidade, nos caminhos antigos.

5. **CSV ausente ou com colunas diferentes**
   - Sem os CSVs, o dashboard ainda abre, mas mostra valores padrão e não exibe o histórico.
   - Para histórico, coloque `dados_exemplo_alagamento_sorocaba.csv` na pasta do projeto ou em `dados/`.
   - Para SIBH, coloque `sibh_data_eawz4ux.csv` na pasta do projeto ou em `dados/`.
   - O CSV de histórico precisa conter: `data_hora`, `chuva_1h`, `chuva_3h`, `chuva_6h`, `chuva_24h`, `nivel_rio`.
   - O CSV SIBH precisa conter: `Data`, `Valor`, com datas no formato `AAAA/MM/DD HH:MM`.

## Procedimento recomendado no VS Code

```bash
mkdir dashboard-alagamento
cd dashboard-alagamento
# copie aqui dashboard_alagamento_sorocaba.py e requirements.txt
python -m venv .venv
```

Ativação do ambiente:

- Windows PowerShell: `\.venv\Scripts\Activate.ps1`
- Windows CMD: `.venv\Scripts\activate.bat`
- Linux/macOS: `source .venv/bin/activate`

Instalação e execução:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run dashboard_alagamento_sorocaba.py
```

Depois abra o endereço informado no terminal, normalmente `http://localhost:8501`.

## Validação rápida

```bash
python -m py_compile dashboard_alagamento_sorocaba.py
python -c "import streamlit, folium, streamlit_folium, pandas; print('Dependências OK')"
```

A versão corrigida também elimina o `numpy` que não era usado, trata CSV ausente/corrompido e evita falha quando o histórico não está disponível.

> Os níveis e regras de risco são protótipo acadêmico; não substituem alertas oficiais da Defesa Civil.
