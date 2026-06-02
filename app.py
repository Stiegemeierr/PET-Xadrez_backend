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
        # Pega as últimas 20 partidas gerais
        response = supabase.table('partidas').select('*').order('created_at', desc=True).limit(20).execute()
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/jogadores/<id>/partidas', methods=['GET'])
def listar_partidas_de_jogador(id):
    try:
        # Retorna o histórico de partidas onde o ID é brancas ou pretas
        # Supabase Python usa .or_ para filtros com OR
        response = supabase.table('partidas').select('*').or_(f"jogador_brancas_id.eq.{id},jogador_pretas_id.eq.{id}").order('created_at', desc=True).limit(10).execute()
        return jsonify(response.data), 200
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

if __name__ == '__main__':
    # Roda o servidor na porta 5000 (padrão do Flask)
    app.run(debug=True, port=5000)
