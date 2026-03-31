import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

load_dotenv()

SUPABASE_URL: str = os.environ.get("VITE_SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise EnvironmentError(
        "As variáveis de ambiente VITE_SUPABASE_URL e SUPABASE_SERVICE_KEY "
        "não foram encontradas. Verifique o seu arquivo .env."
    )

# Debug: confirmar que as chaves corretas foram carregadas
print(f"✓ Supabase URL carregada: {SUPABASE_URL[:50]}...")
print(f"✓ Service Key carregada: {SUPABASE_SERVICE_KEY[:20]}...")

# Tenta criar cliente sem headers customizados primeiro (service key pode não precisar)
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("✓ Cliente Supabase criado com sucesso (sem headers customizados)")
except Exception as e:
    print(f"✗ Erro ao criar cliente: {e}")
    # Se falhar, tenta com headers customizados
    options = ClientOptions(
        headers={
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        }
    )
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, options=options)
    print("✓ Cliente Supabase criado com sucesso (com headers customizados)")

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas as rotas

# ---------------------------------------------------------------------------
# Constantes do Sistema Elo
# ---------------------------------------------------------------------------

K = 32          # Fator K padrão
MMR_INICIAL = 1200


# ---------------------------------------------------------------------------
# Funções auxiliares — Matemática do Sistema Elo
# ---------------------------------------------------------------------------

def calcular_expectativa(mmr_jogador: int, mmr_adversario: int) -> float:
    """Retorna a expectativa de vitória de `jogador` contra `adversario`."""
    return 1 / (1 + 10 ** ((mmr_adversario - mmr_jogador) / 400))


def calcular_novo_mmr(mmr_atual: int, resultado: float, expectativa: float) -> int:
    """Aplica a fórmula Elo e retorna o novo MMR arredondado."""
    return round(mmr_atual + K * (resultado - expectativa))


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.route("/api/partidas", methods=["POST"])
def registrar_partida():
    """
    Registra o resultado de uma partida, recalcula o MMR de ambos os
    jogadores usando o Sistema Elo e persiste tudo no Supabase.

    Payload esperado:
        {
            "brancas_id": "<uuid>",
            "pretas_id":  "<uuid>",
            "resultado":  1 | 0 | 0.5
        }

    resultado:
        1   → vitória das brancas
        0   → vitória das pretas
        0.5 → empate
    """

    # ------------------------------------------------------------------
    # 1. Parse e validação do payload
    # ------------------------------------------------------------------
    dados = request.get_json(silent=True)

    if not dados:
        return jsonify({"erro": "Payload JSON inválido ou ausente."}), 400

    brancas_id = dados.get("brancas_id")
    pretas_id  = dados.get("pretas_id")
    resultado  = dados.get("resultado")

    if not brancas_id or not pretas_id:
        return jsonify({"erro": "Os campos 'brancas_id' e 'pretas_id' são obrigatórios."}), 400

    if resultado is None:
        return jsonify({"erro": "O campo 'resultado' é obrigatório."}), 400

    if resultado not in (0, 0.5, 1):
        return jsonify({"erro": "Valor de 'resultado' inválido. Use 1 (brancas), 0 (pretas) ou 0.5 (empate)."}), 400

    if brancas_id == pretas_id:
        return jsonify({"erro": "Os IDs dos jogadores não podem ser iguais."}), 400

    # ------------------------------------------------------------------
    # 2. Buscar dados dos dois jogadores no Supabase
    # ------------------------------------------------------------------
    try:
        resp_brancas = (
            supabase.table("jogadores")
            .select("id, nome, mmr_atual, vitorias, derrotas, empates")
            .eq("id", brancas_id)
            .single()
            .execute()
        )
        resp_pretas = (
            supabase.table("jogadores")
            .select("id, nome, mmr_atual, vitorias, derrotas, empates")
            .eq("id", pretas_id)
            .single()
            .execute()
        )
    except Exception as exc:
        return jsonify({"erro": "Erro ao consultar jogadores no banco de dados.", "detalhe": str(exc)}), 500

    jogador_brancas = resp_brancas.data
    jogador_pretas  = resp_pretas.data

    if not jogador_brancas:
        return jsonify({"erro": f"Jogador com id '{brancas_id}' não encontrado."}), 404
    if not jogador_pretas:
        return jsonify({"erro": f"Jogador com id '{pretas_id}' não encontrado."}), 404

    mmr_brancas: int = jogador_brancas["mmr_atual"]
    mmr_pretas:  int = jogador_pretas["mmr_atual"]

    # ------------------------------------------------------------------
    # 3. Calcular expectativa de vitória de cada jogador
    # ------------------------------------------------------------------
    e_brancas = calcular_expectativa(mmr_brancas, mmr_pretas)
    e_pretas  = calcular_expectativa(mmr_pretas,  mmr_brancas)

    # ------------------------------------------------------------------
    # 4. Calcular novos MMRs (K = 32)
    # ------------------------------------------------------------------
    novo_mmr_brancas = calcular_novo_mmr(mmr_brancas, resultado,       e_brancas)
    novo_mmr_pretas  = calcular_novo_mmr(mmr_pretas,  1 - resultado,   e_pretas)

    # ------------------------------------------------------------------
    # 5. Calcular a variação absoluta de MMR
    #    (usamos a variação do jogador com pontos, convenção: brancas)
    # ------------------------------------------------------------------
    variacao_mmr: int = abs(novo_mmr_brancas - mmr_brancas)

    # ------------------------------------------------------------------
    # 6. Determinar incremento de vitórias / derrotas / empates
    # ------------------------------------------------------------------
    if resultado == 1:          # Brancas vencem
        delta_b = {"vitorias": jogador_brancas["vitorias"] + 1, "derrotas": jogador_brancas["derrotas"], "empates": jogador_brancas["empates"]}
        delta_p = {"vitorias": jogador_pretas["vitorias"],  "derrotas": jogador_pretas["derrotas"] + 1,  "empates": jogador_pretas["empates"]}
    elif resultado == 0:        # Pretas vencem
        delta_b = {"vitorias": jogador_brancas["vitorias"], "derrotas": jogador_brancas["derrotas"] + 1, "empates": jogador_brancas["empates"]}
        delta_p = {"vitorias": jogador_pretas["vitorias"] + 1, "derrotas": jogador_pretas["derrotas"],   "empates": jogador_pretas["empates"]}
    else:                       # Empate (0.5)
        delta_b = {"vitorias": jogador_brancas["vitorias"], "derrotas": jogador_brancas["derrotas"], "empates": jogador_brancas["empates"] + 1}
        delta_p = {"vitorias": jogador_pretas["vitorias"],  "derrotas": jogador_pretas["derrotas"],  "empates": jogador_pretas["empates"]  + 1}

    # ------------------------------------------------------------------
    # 7. Persistir as alterações no Supabase
    # ------------------------------------------------------------------
    try:
        # Atualiza jogador das brancas
        supabase.table("jogadores").update({
            "mmr_atual": novo_mmr_brancas,
            **delta_b,
        }).eq("id", brancas_id).execute()

        # Atualiza jogador das pretas
        supabase.table("jogadores").update({
            "mmr_atual": novo_mmr_pretas,
            **delta_p,
        }).eq("id", pretas_id).execute()

        # Insere o registro da partida
        resp_partida = supabase.table("partidas").insert({
            "jogador_brancas_id": brancas_id,
            "jogador_pretas_id":  pretas_id,
            "resultado":          resultado,
            "variacao_mmr":       variacao_mmr,
        }).execute()

    except Exception as exc:
        return jsonify({
            "erro":    "Erro ao persistir os dados no banco de dados.",
            "detalhe": str(exc),
        }), 500

    partida_registrada = resp_partida.data[0] if resp_partida.data else {}

    # ------------------------------------------------------------------
    # 8. Resposta de sucesso
    # ------------------------------------------------------------------
    return jsonify({
        "mensagem": "Partida registrada com sucesso!",
        "partida": {
            "id":          partida_registrada.get("id"),
            "created_at":  partida_registrada.get("created_at"),
            "resultado":   resultado,
            "variacao_mmr": variacao_mmr,
        },
        "brancas": {
            "id":       brancas_id,
            "nome":     jogador_brancas["nome"],
            "mmr_anterior": mmr_brancas,
            "mmr_novo":     novo_mmr_brancas,
            "variacao":     novo_mmr_brancas - mmr_brancas,
        },
        "pretas": {
            "id":       pretas_id,
            "nome":     jogador_pretas["nome"],
            "mmr_anterior": mmr_pretas,
            "mmr_novo":     novo_mmr_pretas,
            "variacao":     novo_mmr_pretas - mmr_pretas,
        },
    }), 201


# ---------------------------------------------------------------------------
# Health-check (útil para testes rápidos)
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "servico": "PETXadrez API"}), 200


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)