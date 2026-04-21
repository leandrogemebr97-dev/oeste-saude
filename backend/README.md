# Oeste Saúde

Aplicação composta por um frontend web e uma API de consulta ao Rol ANS.

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
