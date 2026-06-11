import os
from flask import Flask, jsonify, request
from functools import wraps
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client

from elo_calculator import calcular_expectativa, calcular_novo_mmr

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
# Habilita CORS para permitir requisições do frontend React
CORS(app)

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Verifica se as chaves foram carregadas corretamente
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("As variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY precisam estar configuradas no arquivo .env.")

if not ADMIN_PASSWORD:
    print("AVISO: ADMIN_PASSWORD não configurada no .env. Uma senha padrão ('admin123') será usada para testes.")
    ADMIN_PASSWORD = "admin123"

# Inicializa o cliente do Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def requer_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        senha = request.headers.get('X-Admin-Password')
        if not senha or senha != ADMIN_PASSWORD:
            return jsonify({"error": "Acesso negado. Senha de administrador incorreta ou ausente."}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET'])
def hello_world():
    return jsonify({"message": "Hello World! O backend Flask do PETXadrez está rodando."})

@app.route('/jogadores', methods=['GET'])
def listar_jogadores():
    try:
        # Busca todos os jogadores, ordenados pelo MMR (maior para menor)
        response = supabase.table('jogadores').select('*').order('mmr_atual', desc=True).execute()
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/jogadores', methods=['POST'])
@requer_admin
def criar_jogador():
    try:
        dados = request.get_json()
        nome = dados.get('nome')
        if not nome:
            return jsonify({"error": "O campo 'nome' é obrigatório."}), 400
            
        # Tenta inserir. Se der erro de duplicate key, tratamos no except
        response = supabase.table('jogadores').insert({'nome': nome}).execute()
        return jsonify(response.data[0]), 201
    except Exception as e:
        erro_str = str(e).lower()
        if 'duplicate key' in erro_str or 'unique constraint' in erro_str:
            return jsonify({"error": "Já existe um jogador com este nome."}), 400
        return jsonify({"error": str(e)}), 500

@app.route('/jogadores/<id>', methods=['GET'])
def obter_jogador(id):
    try:
        response = supabase.table('jogadores').select('*').eq('id', id).execute()
        if not response.data:
            return jsonify({"error": "Jogador não encontrado."}), 404
        return jsonify(response.data[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/partidas', methods=['GET'])
def listar_partidas_recentes():
    try:
        # Retorna todas as partidas, ordenadas da mais recente para a mais antiga
        response = supabase.table('partidas').select('*').order('created_at', desc=True).execute()
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/jogadores/<id>/partidas', methods=['GET'])
def listar_partidas_de_jogador(id):
    try:
        # Retorna o histórico de partidas onde o ID é brancas ou pretas
        # Supabase Python usa .or_ para filtros com OR
        response = supabase.table('partidas').select('*').or_(f"jogador_brancas_id.eq.{id},jogador_pretas_id.eq.{id}").order('created_at', desc=True).execute()
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/jogadores/<id>', methods=['PUT'])
@requer_admin
def atualizar_jogador(id):
    """Atualiza campos do perfil do jogador (bio, curso, semestre)."""
    try:
        dados = request.get_json()
        campos_permitidos = ['bio', 'curso', 'semestre']
        atualizacao = {k: v for k, v in dados.items() if k in campos_permitidos}

        if not atualizacao:
            return jsonify({"error": "Nenhum campo válido para atualizar. Campos aceitos: bio, curso, semestre."}), 400

        response = supabase.table('jogadores').update(atualizacao).eq('id', id).execute()
        if not response.data:
            return jsonify({"error": "Jogador não encontrado."}), 404
        return jsonify(response.data[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/jogadores/<id>/mmr-historico', methods=['GET'])
def mmr_historico(id):
    """
    Reconstrói o histórico de MMR do jogador a partir das partidas.
    Começa em 500 e aplica cada variação em ordem cronológica.
    """
    try:
        # Busca todas as partidas do jogador em ordem cronológica
        response = supabase.table('partidas').select('*').or_(
            f"jogador_brancas_id.eq.{id},jogador_pretas_id.eq.{id}"
        ).order('created_at', desc=False).execute()

        mmr = 500
        historico = [{"data": None, "mmr": 500}]  # Ponto inicial

        for partida in response.data:
            if partida['jogador_brancas_id'] == id:
                variacao = partida['variacao_mmr_brancas']
            else:
                variacao = partida['variacao_mmr_pretas']

            mmr += variacao
            historico.append({
                "data": partida['created_at'],
                "mmr": mmr
            })

        return jsonify(historico), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/jogadores/<id>/conquistas', methods=['GET'])
def conquistas_jogador(id):
    """
    Computa conquistas on-the-fly a partir dos dados existentes do jogador.
    Nenhuma tabela extra necessária.
    """
    try:
        # Busca dados do jogador
        res_jogador = supabase.table('jogadores').select('*').eq('id', id).execute()
        if not res_jogador.data:
            return jsonify({"error": "Jogador não encontrado."}), 404

        jogador = res_jogador.data[0]
        total_partidas = jogador['vitorias'] + jogador['derrotas'] + jogador['empates']
        winrate = (jogador['vitorias'] / total_partidas * 100) if total_partidas > 0 else 0

        # Busca partidas para verificar conquistas que dependem do histórico
        res_partidas = supabase.table('partidas').select('variacao_mmr_brancas,variacao_mmr_pretas,jogador_brancas_id').or_(
            f"jogador_brancas_id.eq.{id},jogador_pretas_id.eq.{id}"
        ).execute()

        # Verifica se teve variação >= 50 em alguma partida
        teve_variacao_grande = False
        for p in res_partidas.data:
            variacao = p['variacao_mmr_brancas'] if p['jogador_brancas_id'] == id else p['variacao_mmr_pretas']
            if abs(variacao) >= 50:
                teve_variacao_grande = True
                break

        # Definição das conquistas
        conquistas = [
            {
                "id": "estreante",
                "nome": "Estreante",
                "descricao": "Jogou sua primeira partida",
                "icone": "♟️",
                "desbloqueada": total_partidas >= 1
            },
            {
                "id": "primeira_vitoria",
                "nome": "Primeira Vitória",
                "descricao": "Venceu uma partida",
                "icone": "🏆",
                "desbloqueada": jogador['vitorias'] >= 1
            },
            {
                "id": "veterano",
                "nome": "Veterano",
                "descricao": "Jogou 20 ou mais partidas",
                "icone": "🎖️",
                "desbloqueada": total_partidas >= 20
            },
            {
                "id": "lenda",
                "nome": "Lenda",
                "descricao": "Jogou 50 ou mais partidas",
                "icone": "⭐",
                "desbloqueada": total_partidas >= 50
            },
            {
                "id": "imbativel",
                "nome": "Imbatível",
                "descricao": "Winrate de 70%+ com 10 ou mais partidas",
                "icone": "🛡️",
                "desbloqueada": winrate >= 70 and total_partidas >= 10
            },
            {
                "id": "pacifista",
                "nome": "Pacifista",
                "descricao": "Empatou 5 ou mais partidas",
                "icone": "🕊️",
                "desbloqueada": jogador['empates'] >= 5
            },
            {
                "id": "rating_s",
                "nome": "Rating S",
                "descricao": "Alcançou MMR 700 ou superior",
                "icone": "👑",
                "desbloqueada": jogador['mmr_atual'] >= 700
            },
            {
                "id": "montanha_russa",
                "nome": "Montanha-Russa",
                "descricao": "Teve variação de 50+ pontos em uma partida",
                "icone": "🎢",
                "desbloqueada": teve_variacao_grande
            }
        ]

        return jsonify(conquistas), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        senha = dados.get('senha')
        if senha == ADMIN_PASSWORD:
            return jsonify({"message": "Login autorizado"}), 200
        return jsonify({"error": "Senha incorreta"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/partidas', methods=['POST'])
@requer_admin
def registrar_partida():
    try:
        dados = request.get_json()
        
        # Validar dados de entrada
        id_brancas = dados.get('jogador_brancas_id')
        id_pretas = dados.get('jogador_pretas_id')
        resultado = dados.get('resultado') # 1 (Brancas), 0 (Pretas), 0.5 (Empate)
        
        if not id_brancas or not id_pretas or resultado is None:
            return jsonify({"error": "Faltam dados obrigatórios (jogador_brancas_id, jogador_pretas_id, resultado)."}), 400
            
        # Buscar jogadores no banco
        res_brancas = supabase.table('jogadores').select('*').eq('id', id_brancas).execute()
        res_pretas = supabase.table('jogadores').select('*').eq('id', id_pretas).execute()
        
        if not res_brancas.data or not res_pretas.data:
            return jsonify({"error": "Um ou ambos os jogadores não foram encontrados."}), 404
            
        jogador_brancas = res_brancas.data[0]
        jogador_pretas = res_pretas.data[0]
        
        mmr_brancas = jogador_brancas['mmr_atual']
        mmr_pretas = jogador_pretas['mmr_atual']
        
        # Calcular expectativas
        exp_brancas = calcular_expectativa(mmr_brancas, mmr_pretas)
        exp_pretas = calcular_expectativa(mmr_pretas, mmr_brancas)
        
        # Calcular novos MMRs
        novo_mmr_brancas = calcular_novo_mmr(mmr_brancas, exp_brancas, resultado)
        # Se brancas ganha (1), pretas perde (0). Se brancas perde (0), pretas ganha (1). Empate é 0.5.
        resultado_pretas = 1 - resultado 
        novo_mmr_pretas = calcular_novo_mmr(mmr_pretas, exp_pretas, resultado_pretas)
        
        # Variação de MMR individual
        variacao_mmr_brancas = novo_mmr_brancas - mmr_brancas
        variacao_mmr_pretas = novo_mmr_pretas - mmr_pretas
        
        # Determinar acréscimo de vitórias/derrotas/empates
        # Brancas
        v_brancas = jogador_brancas['vitorias'] + (1 if resultado == 1 else 0)
        d_brancas = jogador_brancas['derrotas'] + (1 if resultado == 0 else 0)
        e_brancas = jogador_brancas['empates'] + (1 if resultado == 0.5 else 0)
        
        # Pretas
        v_pretas = jogador_pretas['vitorias'] + (1 if resultado_pretas == 1 else 0)
        d_pretas = jogador_pretas['derrotas'] + (1 if resultado_pretas == 0 else 0)
        e_pretas = jogador_pretas['empates'] + (1 if resultado_pretas == 0.5 else 0)
        
        # Iniciar as atualizações no banco
        
        # Atualiza brancas
        supabase.table('jogadores').update({
            'mmr_atual': novo_mmr_brancas,
            'vitorias': v_brancas,
            'derrotas': d_brancas,
            'empates': e_brancas
        }).eq('id', id_brancas).execute()
        
        # Atualiza pretas
        supabase.table('jogadores').update({
            'mmr_atual': novo_mmr_pretas,
            'vitorias': v_pretas,
            'derrotas': d_pretas,
            'empates': e_pretas
        }).eq('id', id_pretas).execute()
        
        # Insere histórico da partida
        supabase.table('partidas').insert({
            'jogador_brancas_id': id_brancas,
            'jogador_pretas_id': id_pretas,
            'resultado': resultado,
            'variacao_mmr_brancas': variacao_mmr_brancas,
            'variacao_mmr_pretas': variacao_mmr_pretas
        }).execute()
        
        return jsonify({
            "message": "Partida registrada com sucesso!",
            "jogadores_atualizados": {
                "brancas": {
                    "id": id_brancas,
                    "mmr_antigo": mmr_brancas,
                    "novo_mmr": novo_mmr_brancas,
                    "variacao": variacao_mmr_brancas
                },
                "pretas": {
                    "id": id_pretas,
                    "mmr_antigo": mmr_pretas,
                    "novo_mmr": novo_mmr_pretas,
                    "variacao": variacao_mmr_pretas
                }
            }
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/partidas/<id>', methods=['DELETE'])
@requer_admin
def excluir_partida(id):
    """
    Exclui uma partida e recalcula TODO o histórico do zero.
    Fluxo:
      1. Verifica se a partida existe
      2. Deleta a partida
      3. Reseta todos os jogadores para o estado base (MMR=500, V/D/E=0)
      4. Re-simula todas as partidas restantes em ordem cronológica
      5. Atualiza o estado final de cada jogador e as variações de MMR de cada partida
    """
    try:
        # 1. Verificar se a partida existe
        res_partida = supabase.table('partidas').select('*').eq('id', id).execute()
        if not res_partida.data:
            return jsonify({"error": "Partida não encontrada."}), 404

        # 2. Deletar a partida
        supabase.table('partidas').delete().eq('id', id).execute()

        # 3. Buscar todos os jogadores
        res_jogadores = supabase.table('jogadores').select('*').execute()
        jogadores = res_jogadores.data

        # Criar estado em memória: cada jogador começa com MMR=500, V/D/E=0
        estado = {}
        for j in jogadores:
            estado[j['id']] = {
                'mmr_atual': 500,
                'vitorias': 0,
                'derrotas': 0,
                'empates': 0
            }

        # 4. Buscar todas as partidas restantes em ordem cronológica (mais antiga primeiro)
        res_partidas = supabase.table('partidas').select('*').order('created_at', desc=False).execute()
        partidas_restantes = res_partidas.data

        # 5. Re-simular cada partida em ordem
        for partida in partidas_restantes:
            id_brancas = partida['jogador_brancas_id']
            id_pretas = partida['jogador_pretas_id']
            resultado = partida['resultado']

            # Pegar MMRs atuais da memória
            mmr_brancas = estado[id_brancas]['mmr_atual']
            mmr_pretas = estado[id_pretas]['mmr_atual']

            # Calcular expectativas
            exp_brancas = calcular_expectativa(mmr_brancas, mmr_pretas)
            exp_pretas = calcular_expectativa(mmr_pretas, mmr_brancas)

            # Calcular novos MMRs
            novo_mmr_brancas = calcular_novo_mmr(mmr_brancas, exp_brancas, resultado)
            resultado_pretas = 1 - resultado
            novo_mmr_pretas = calcular_novo_mmr(mmr_pretas, exp_pretas, resultado_pretas)

            # Calcular variações
            variacao_brancas = novo_mmr_brancas - mmr_brancas
            variacao_pretas = novo_mmr_pretas - mmr_pretas

            # Atualizar estado em memória
            estado[id_brancas]['mmr_atual'] = novo_mmr_brancas
            estado[id_pretas]['mmr_atual'] = novo_mmr_pretas

            # Atualizar contadores V/D/E
            if resultado == 1:
                estado[id_brancas]['vitorias'] += 1
                estado[id_pretas]['derrotas'] += 1
            elif resultado == 0:
                estado[id_brancas]['derrotas'] += 1
                estado[id_pretas]['vitorias'] += 1
            else:
                estado[id_brancas]['empates'] += 1
                estado[id_pretas]['empates'] += 1

            # Atualizar variações de MMR desta partida no banco
            supabase.table('partidas').update({
                'variacao_mmr_brancas': variacao_brancas,
                'variacao_mmr_pretas': variacao_pretas
            }).eq('id', partida['id']).execute()

        # 6. Salvar estado final de todos os jogadores no banco
        for jogador_id, dados in estado.items():
            supabase.table('jogadores').update(dados).eq('id', jogador_id).execute()

        return jsonify({
            "message": "Partida excluída com sucesso. Todo o histórico foi recalculado.",
            "jogadores_recalculados": len(estado),
            "partidas_restantes": len(partidas_restantes)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Roda o servidor na porta 5000 (padrão do Flask)
    app.run(debug=True, port=5000)
