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
| PUT | `/jogadores/:id` | Sim | Atualizar perfil do jogador |
| GET | `/jogadores/:id/partidas` | Nao | Historico de partidas do jogador |
| GET | `/jogadores/:id/mmr-historico` | Nao | Historico de MMR para grafico |
| GET | `/jogadores/:id/conquistas` | Nao | Conquistas do jogador |
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

Retorna todas as partidas do jogador (onde ele jogou de brancas ou pretas), ordenadas da mais recente para a mais antiga.

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

### PUT `/jogadores/:id`

Atualiza campos do perfil do jogador. Requer autenticacao admin.

**Headers:**
```
Content-Type: application/json
X-Admin-Password: <senha>
```

**Request Body (todos os campos sao opcionais):**
```json
{
  "bio": "Xadrezista desde 2020",
  "curso": "Ciencia da Computacao",
  "semestre": "5"
}
```

**Response (200):**
```json
{
  "id": "uuid-do-jogador",
  "nome": "Gabriel",
  "mmr_atual": 650,
  "bio": "Xadrezista desde 2020",
  "curso": "Ciencia da Computacao",
  "semestre": "5"
}
```

**Erros:**
- `400` — Nenhum campo valido enviado
- `401` — Senha admin incorreta
- `404` — Jogador nao encontrado

---

### GET `/jogadores/:id/mmr-historico`

Reconstroi o historico de MMR do jogador a partir das partidas. Comeca em 500 e aplica cada variacao em ordem cronologica.

**Response (200):**
```json
[
  { "data": null, "mmr": 500 },
  { "data": "2026-01-15T10:30:00Z", "mmr": 550 },
  { "data": "2026-01-16T14:00:00Z", "mmr": 520 }
]
```

> O primeiro ponto sempre tem `data: null` e `mmr: 500` (ponto inicial de todo jogador).

---

### GET `/jogadores/:id/conquistas`

Computa conquistas on-the-fly a partir dos dados existentes do jogador. Nao armazena em tabela.

**Response (200):**
```json
[
  {
    "id": "estreante",
    "nome": "Estreante",
    "descricao": "Jogou sua primeira partida",
    "icone": "\u265f\ufe0f",
    "desbloqueada": true
  },
  {
    "id": "primeira_vitoria",
    "nome": "Primeira Vitoria",
    "descricao": "Venceu uma partida",
    "icone": "\ud83c\udfc6",
    "desbloqueada": false
  }
]
```

**Conquistas disponiveis:**

| ID | Nome | Criterio |
|----|------|----------|
| `estreante` | Estreante | 1+ partida jogada |
| `primeira_vitoria` | Primeira Vitoria | 1+ vitoria |
| `veterano` | Veterano | 20+ partidas |
| `lenda` | Lenda | 50+ partidas |
| `imbativel` | Imbativel | Winrate >= 70% com 10+ partidas |
| `pacifista` | Pacifista | 5+ empates |
| `rating_s` | Rating S | MMR >= 700 |
| `montanha_russa` | Montanha-Russa | Variacao de 50+ pts em uma partida |

**Erros:**
- `404` — Jogador nao encontrado

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
