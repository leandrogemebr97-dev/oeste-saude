# Oeste Saúde

Aplicação composta por um frontend web e uma API de consulta ao Rol ANS com chat AI via Playwright.

## Estrutura

```
oeste-saude/
├── backend/
│   ├── app/
│   │   ├── main.py        ← API FastAPI
│   │   └── load_rol.py    ← extrai PDFs → banco SQLite
│   ├── data/
│   │   ├── rol.db         ← gerado por load_rol.py
│   │   └── pdfs/
│   │       ├── Anexo_I_Rol_*.pdf
│   │       └── Anexo_II_DUT_*.pdf
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── .env.example
├── .gitignore
└── README.md
```

## Frontend

Sirva os arquivos estáticos com qualquer servidor HTTP. Exemplo rápido:

```bash
cd frontend
python -m http.server 3000
```

Acesse: http://localhost:3000

## Backend — API Rol ANS

### Instalar dependências

```bash
cd backend
pip install -r requirements.txt
```

### Gerar o banco (primeira vez ou ao atualizar os PDFs)

```bash
cd backend
python app/load_rol.py
```

### Subir a API

```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

Documentação interativa: http://localhost:8001/docs

### Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/procedimentos?q=hemograma` | Busca por nome parcial |
| GET | `/procedimentos?q=40301012` | Busca por código TUSS |
| GET | `/procedimentos/{codigo}` | Detalhe + DUT se houver |
| GET | `/dut/{codigo}` | Diretriz de utilização isolada |
| GET | `/stats` | Totais do banco |

## Deploy no Railway

### Pré-requisitos
- Conta no Railway (https://railway.app)
- Repositório no GitHub conectado ao Railway

### Passos para Deploy

1. **Conectar repositório no Railway**
   - Acesse https://railway.app
   - Clique em "New Project" → "Deploy from GitHub repo"
   - Selecione o repositório `oeste-saude`

2. **Configurar variáveis de ambiente**
   No painel do Railway, adicione as seguintes variáveis:
   
   ```
   PORT=8001
   GEMINI_API_KEY=sua_chave_aqui
   RAILWAY_ENVIRONMENT=production
   ```

3. **Arquivos de configuração**
   O projeto já inclui:
   - `nixpacks.toml` - Configuração do build
   - `Procfile` - Comando de inicialização
   - `railway.json` - Configuração do Railway
   - `requirements.txt` - Dependências Python

4. **Deploy automático**
   - O Railway detecta automaticamente os arquivos de configuração
   - O build instala as dependências e o Playwright Chromium
   - A aplicação inicia automaticamente com Gunicorn

5. **Acessar a aplicação**
   - O Railway fornece uma URL pública após o deploy
   - A aplicação estará disponível na URL gerada

### Notas Importantes

- O Playwright Chromium é instalado automaticamente durante o build
- A porta é definida pela variável de ambiente `PORT` do Railway
- O Gunicorn é usado como servidor de produção com 4 workers
- O banco de dados SQLite é recriado a cada deploy (para persistência, considere usar Railway PostgreSQL)

### Troubleshooting

Se houver erros no build:
- Verifique se `GEMINI_API_KEY` foi configurado
- Confirme que o Playwright Chromium está instalando corretamente
- Verifique os logs no painel do Railway
