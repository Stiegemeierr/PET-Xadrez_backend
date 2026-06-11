# API Reference — PET-Xadrez Backend

> Documentacao de todos os endpoints da API REST.
>
> **Base URL:** `https://petxadrez-api.onrender.com`

---

## Resumo dos Endpoints

| Metodo | Rota | Admin | Descricao |
|--------|------|-------|-----------|
| GET | `/` | Nao | Health check |
| GET | `/jogadores` | Nao | Listar todos os jogadores |
| POST | `/jogadores` | Sim | Criar novo jogador |
| GET | `/jogadores/:id` | Nao | Obter jogador por ID |
| GET | `/jogadores/:id/partidas` | Nao | Historico de partidas do jogador |
| GET | `/partidas` | Nao | Listar todas as partidas |
| POST | `/partidas` | Sim | Registrar partida |
| DELETE | `/partidas/:id` | Sim | Excluir partida e recalcular historico |
| POST | `/auth/login` | Nao | Validar senha de admin |

---

## Autenticacao

Rotas marcadas como **Admin** exigem o header:

```
X-Admin-Password: <senha_admin>
```

Se ausente ou incorreto, retorna `401`:
```json
{ "error": "Acesso negado. Senha de administrador incorreta ou ausente." }
```

---

## Endpoints

### GET `/`

Health check basico.

**Response (200):**
```json
{ "message": "Hello World! O backend Flask do PETXadrez está rodando." }
```

---

### GET `/jogadores`

Retorna todos os jogadores, ordenados pelo MMR (maior para menor).

**Response (200):**
```json
[
  {
    "id": "uuid-do-jogador",
    "nome": "Gabriel",
    "mmr_atual": 650,
    "vitorias": 5,
    "derrotas": 2,
    "empates": 1
  }
]
```

---

### POST `/jogadores`

Cria um novo jogador. Requer autenticacao admin.

**Headers:**
```
Content-Type: application/json
X-Admin-Password: <senha>
```

**Request Body:**
```json
{ "nome": "Novo Jogador" }
```

**Response (201):**
```json
{
  "id": "uuid-gerado",
  "nome": "Novo Jogador",
  "mmr_atual": 500,
  "vitorias": 0,
  "derrotas": 0,
  "empates": 0
}
```

**Erros:**
- `400` — Campo `nome` ausente ou jogador ja existe (UNIQUE constraint)
- `401` — Senha admin incorreta

---

### GET `/jogadores/:id`

Retorna os dados de um jogador especifico.

**Response (200):**
```json
{
  "id": "uuid-do-jogador",
  "nome": "Gabriel",
  "mmr_atual": 650,
  "vitorias": 5,
  "derrotas": 2,
  "empates": 1
}
```

**Erros:**
- `404` — Jogador nao encontrado

---

### GET `/jogadores/:id/partidas`

Retorna as ultimas 10 partidas do jogador (onde ele jogou de brancas ou pretas).

**Response (200):**
```json
[
  {
    "id": "uuid-da-partida",
    "jogador_brancas_id": "uuid",
    "jogador_pretas_id": "uuid",
    "resultado": 1,
    "variacao_mmr_brancas": 42,
    "variacao_mmr_pretas": -42,
    "created_at": "2026-01-15T10:30:00Z"
  }
]
```

---

### GET `/partidas`

Retorna todas as partidas, ordenadas da mais recente para a mais antiga.

**Response (200):**
```json
[
  {
    "id": "uuid-da-partida",
    "jogador_brancas_id": "uuid",
    "jogador_pretas_id": "uuid",
    "resultado": 0.5,
    "variacao_mmr_brancas": 5,
    "variacao_mmr_pretas": -5,
    "created_at": "2026-01-15T10:30:00Z"
  }
]
```

---

### POST `/partidas`

Registra uma nova partida e recalcula o MMR dos dois jogadores. Requer autenticacao admin.

**Headers:**
```
Content-Type: application/json
X-Admin-Password: <senha>
```

**Request Body:**
```json
{
  "jogador_brancas_id": "uuid-brancas",
  "jogador_pretas_id": "uuid-pretas",
  "resultado": 1
}
```

> **Valores de `resultado`:** `1` (brancas vencem), `0` (pretas vencem), `0.5` (empate)

**Response (201):**
```json
{
  "message": "Partida registrada com sucesso!",
  "jogadores_atualizados": {
    "brancas": {
      "id": "uuid-brancas",
      "mmr_antigo": 500,
      "novo_mmr": 550,
      "variacao": 50
    },
    "pretas": {
      "id": "uuid-pretas",
      "mmr_antigo": 500,
      "novo_mmr": 450,
      "variacao": -50
    }
  }
}
```

**Erros:**
- `400` — Dados obrigatorios ausentes
- `401` — Senha admin incorreta
- `404` — Um ou ambos os jogadores nao encontrados

---

### DELETE `/partidas/:id`

Exclui uma partida e **recalcula todo o historico do zero**. Requer autenticacao admin.

**Funcionamento:**
1. Deleta a partida selecionada
2. Reseta TODOS os jogadores para MMR=500, V/D/E=0
3. Re-simula todas as partidas restantes em ordem cronologica
4. Atualiza o estado final de cada jogador e as variacoes de MMR

**Headers:**
```
X-Admin-Password: <senha>
```

**Response (200):**
```json
{
  "message": "Partida excluída com sucesso. Todo o histórico foi recalculado.",
  "jogadores_recalculados": 8,
  "partidas_restantes": 15
}
```

**Erros:**
- `401` — Senha admin incorreta
- `404` — Partida nao encontrada

---

### POST `/auth/login`

Valida a senha de administrador. Usada pelo frontend para autenticar antes de acessar funcoes admin.

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{ "senha": "sua_senha_admin" }
```

**Response (200):**
```json
{ "message": "Login autorizado" }
```

**Erros:**
- `401` — Senha incorreta
