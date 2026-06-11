# Arquitetura — PET-Xadrez Backend

> Documento de referencia tecnica. Leia este arquivo para entender a estrutura completa do backend sem precisar ler o codigo-fonte.

---

## Visao Geral

API REST construida em Flask que gerencia o ranking de xadrez do PET Ciencia da Computacao. Responsavel por:

- CRUD de jogadores
- Registro e exclusao de partidas
- Calculo automatico de MMR (sistema Elo)
- Autenticacao simples de administrador

---

## Stack Tecnica

| Tecnologia | Versao | Uso |
|------------|--------|-----|
| Python | 3.x | Linguagem principal |
| Flask | 3.0.0 | Framework web (API REST) |
| flask-cors | 4.0.0 | Habilitar CORS para o frontend |
| supabase-py | latest | Cliente Python para o banco Supabase |
| python-dotenv | 1.0.0 | Carregar variaveis de ambiente do `.env` |
| gunicorn | latest | Servidor WSGI para producao (Render) |

**Deploy:** Render (https://petxadrez-api.onrender.com)

---

## Mapa de Arquivos

```
PET-Xadrez-backend-/
|-- app.py                # Servidor Flask: todas as rotas e logica de negocio
|-- elo_calculator.py     # Funcoes puras de calculo Elo (expectativa + novo MMR)
|-- requirements.txt      # Dependencias Python
|-- .env                  # Variaveis de ambiente (NAO commitado)
|-- .gitignore            # Ignora .env
```

### Descricao detalhada de cada arquivo

#### `app.py` (312 linhas)
Arquivo principal. Contem:
- Inicializacao do Flask e CORS
- Conexao com Supabase via `create_client()`
- Decorator `@requer_admin` para proteger rotas administrativas
- 8 endpoints REST (ver API_REFERENCE.md)
- Logica completa de registro de partida com calculo de MMR
- Logica de exclusao de partida com recalculo total do historico

#### `elo_calculator.py` (19 linhas)
Modulo isolado com duas funcoes puras:
- `calcular_expectativa(mmr_jogador, mmr_oponente)` — Formula Elo padrao: `1 / (1 + 10^((oponente - jogador) / 400))`
- `calcular_novo_mmr(mmr_atual, expectativa, resultado, k=100)` — Aplica `MMR + K * (Resultado - Expectativa)`, retorna arredondado

---

## Modelo de Dados (Supabase / PostgreSQL)

### Tabela `jogadores`

| Coluna | Tipo | Default | Descricao |
|--------|------|---------|-----------|
| `id` | UUID | auto | Chave primaria |
| `nome` | TEXT | — | Nome unico do jogador (UNIQUE constraint) |
| `mmr_atual` | INTEGER | 500 | Rating atual do jogador |
| `vitorias` | INTEGER | 0 | Total de vitorias |
| `derrotas` | INTEGER | 0 | Total de derrotas |
| `empates` | INTEGER | 0 | Total de empates |

### Tabela `partidas`

| Coluna | Tipo | Default | Descricao |
|--------|------|---------|-----------|
| `id` | UUID | auto | Chave primaria |
| `jogador_brancas_id` | UUID (FK) | — | Referencia `jogadores.id` |
| `jogador_pretas_id` | UUID (FK) | — | Referencia `jogadores.id` |
| `resultado` | NUMERIC | — | 1 (brancas vencem), 0 (pretas vencem), 0.5 (empate) |
| `variacao_mmr_brancas` | INTEGER | — | Pontos ganhos/perdidos pelas brancas |
| `variacao_mmr_pretas` | INTEGER | — | Pontos ganhos/perdidos pelas pretas |
| `created_at` | TIMESTAMP | now() | Data/hora do registro |

> **Restricao:** CHECK constraint impede que `jogador_brancas_id == jogador_pretas_id`.

---

## Fluxo de Dados

```
[Frontend React]
       |
       | fetch() com JSON
       v
[Flask API — app.py]
       |
       | supabase-py (select/insert/update/delete)
       v
[Supabase PostgreSQL]
```

### Fluxo de Registro de Partida (POST /partidas)

1. Frontend envia `jogador_brancas_id`, `jogador_pretas_id`, `resultado`
2. Backend busca os dois jogadores no banco
3. Calcula expectativa de vitoria para cada um (formula Elo)
4. Calcula novo MMR de cada jogador (K=100)
5. Atualiza MMR e contadores V/D/E dos dois jogadores
6. Insere registro da partida com a variacao de MMR

### Fluxo de Exclusao de Partida (DELETE /partidas/:id)

1. Verifica se a partida existe
2. Deleta a partida
3. Reseta TODOS os jogadores para estado base (MMR=500, V/D/E=0)
4. Busca todas as partidas restantes em ordem cronologica
5. Re-simula cada partida em ordem, recalculando tudo
6. Salva o estado final de cada jogador no banco

> **Importante:** A exclusao e uma operacao custosa que recalcula o historico inteiro. Isso garante consistencia total dos dados.

---

## Autenticacao

O sistema usa autenticacao simples por senha compartilhada:

- A senha admin e definida na variavel de ambiente `ADMIN_PASSWORD`
- Se nao configurada, usa `admin123` como fallback (apenas para testes)
- Rotas protegidas exigem o header `X-Admin-Password` com a senha correta
- O decorator `@requer_admin` verifica o header e retorna 401 se invalido

**Rotas protegidas:** `POST /jogadores`, `POST /partidas`, `DELETE /partidas/:id`

---

## Variaveis de Ambiente

| Variavel | Obrigatoria | Descricao |
|----------|-------------|-----------|
| `SUPABASE_URL` | Sim | URL do projeto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Sim | Chave de servico do Supabase (acesso total) |
| `ADMIN_PASSWORD` | Nao | Senha para acesso admin (default: `admin123`) |

---

## Padroes e Convencoes

- **Linguagem do codigo:** Portugues (variaveis, comentarios, mensagens de erro)
- **Formato de resposta:** Todas as rotas retornam JSON
- **Tratamento de erros:** Try/catch em todas as rotas, retorno `{"error": "mensagem"}` com status HTTP adequado
- **MMR inicial:** 500 pontos para novos jogadores
- **Fator K:** 100 (alta volatilidade, adequado para microcomunidades)
- **Ordenacao padrao:** Jogadores por MMR desc, partidas por created_at desc
