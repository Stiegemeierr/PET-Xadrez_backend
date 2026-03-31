import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
# Permite que o React converse com esta API
CORS(app)

# Aqui nós consertamos os nomes para puxar exatamente o que você tem no seu .env
url: str = os.environ.get("VITE_SUPABASE_URL")
key: str = os.environ.get("VITE_SUPABASE_ANON_KEY")

# Conecta ao banco de dados
supabase: Client = create_client(url, key)

# --- ROTA 1: O "Batimento Cardíaco" para o seu navegador ---
@app.route('/', methods=['GET'])
def home():
    return "<h1>🟢 O Backend do PETXadrez está rodando perfeitamente!</h1>"

# --- ROTA 2: A Rota de Registrar Partida (Invisível no navegador) ---
@app.route('/api/partidas', methods=['POST'])
def registrar_partida():
    # 1. O React manda os dados da partida em formato JSON
    dados = request.get_json()
    id_brancas = dados.get('brancas_id')
    id_pretas = dados.get('pretas_id')
    resultado = dados.get('resultado') 

    # 2. O Flask pega os IDs, vai no Supabase e descobre o MMR atual deles
    jogadores_res = supabase.table('jogadores').select('*').in_('id', [id_brancas, id_pretas]).execute()
    jogadores = {j['id']: j for j in jogadores_res.data}
    
    # ... aqui aconteceria toda aquela matemática do Elo ...
    
    # 3. O Flask devolve uma resposta de sucesso para o React
    return jsonify({
        "mensagem": "Partida recebida pelo Python com sucesso!",
        "brancas": id_brancas,
        "pretas": id_pretas
    }), 201

if __name__ == '__main__':
    app.run(debug=True, port=8080)