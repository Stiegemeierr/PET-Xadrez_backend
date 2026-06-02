import os
from flask import Flask, jsonify, request
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

# Verifica se as chaves foram carregadas corretamente
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("As variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY precisam estar configuradas no arquivo .env.")

# Inicializa o cliente do Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

@app.route('/partidas', methods=['POST'])
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
        
        # Variação de MMR sob o ponto de vista das brancas
        variacao_mmr = novo_mmr_brancas - mmr_brancas
        
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
        # Supabase não suporta transações diretamente pelo cliente REST da mesma forma que SQL raw facilmente sem RPC,
        # então faremos chamadas sequenciais. O ideal seria uma RPC, mas faremos chamadas individuais aqui.
        
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
            'variacao_mmr': variacao_mmr
        }).execute()
        
        return jsonify({
            "message": "Partida registrada com sucesso!",
            "jogadores_atualizados": {
                "brancas": {
                    "id": id_brancas,
                    "mmr_antigo": mmr_brancas,
                    "novo_mmr": novo_mmr_brancas,
                    "variacao": variacao_mmr
                },
                "pretas": {
                    "id": id_pretas,
                    "mmr_antigo": mmr_pretas,
                    "novo_mmr": novo_mmr_pretas,
                    "variacao": -variacao_mmr
                }
            }
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Roda o servidor na porta 5000 (padrão do Flask)
    app.run(debug=True, port=5000)
