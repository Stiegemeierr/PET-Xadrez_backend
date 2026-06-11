# PETXadrez — Backend (API)

> API REST que gerencia o ranking de xadrez do PET Ciencia da Computacao.

**Status:** MVP funcional | **Deploy:** [Render](https://petxadrez-api.onrender.com)

---

## Documentacao

- [ARCHITECTURE.md](./ARCHITECTURE.md) — Mapa completo do projeto (estrutura, fluxos, banco de dados)
- [API_REFERENCE.md](./API_REFERENCE.md) — Documentacao de todos os endpoints

---

## Stack

- Python 3 + Flask 3.0
- Supabase (PostgreSQL)
- Deploy: Render (gunicorn)

---

## Como Rodar Localmente

### Pre-requisitos
- Python 3.8+
- pip

### Passos

1. Clone o repositorio:
```bash
git clone https://github.com/Stiegemeierr/PET-Xadrez-backend-.git
cd PET-Xadrez-backend-
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Instale as dependencias:
```bash
pip install -r requirements.txt
```

4. Configure as variaveis de ambiente. Crie um arquivo `.env` na raiz:
```env
SUPABASE_URL=sua_url_aqui
SUPABASE_SERVICE_ROLE_KEY=sua_chave_aqui
ADMIN_PASSWORD=sua_senha_aqui
```

5. Rode o servidor:
```bash
python app.py
```

O servidor estara disponivel em `http://localhost:5000`.

---

## Deploy

O backend esta hospedado no [Render](https://render.com) usando gunicorn como servidor WSGI. A URL de producao e:

```
https://petxadrez-api.onrender.com
```

As variaveis de ambiente (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ADMIN_PASSWORD`) devem ser configuradas no painel do Render.

---

## Estrutura do Projeto

```
PET-Xadrez-backend-/
|-- app.py                # Servidor Flask (rotas + logica de negocio)
|-- elo_calculator.py     # Funcoes de calculo Elo
|-- requirements.txt      # Dependencias Python
|-- .env                  # Variaveis de ambiente (nao commitado)
|-- .gitignore            # Ignora .env
```

Para detalhes completos sobre a arquitetura, leia o [ARCHITECTURE.md](./ARCHITECTURE.md).
