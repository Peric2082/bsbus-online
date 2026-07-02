from flask import Flask, jsonify
from flask_cors import CORS
import requests
import math

app = Flask(__name__)
CORS(app)

# URL da API SEMOB-DF
URL_SEMOB = (
    "https://geoserver.semob.df.gov.br/geoserver/semob/ows"
    "?service=WFS&version=1.1.0&request=GetFeature"
    "&typeName=semob%3Aultima_posicao"
    "&cql_filter=id_operadora='3450'"
    "&outputFormat=application/json"
)

# Coordenadas das garagens
GARAGENS = [
    {"nome": "Garagem Setor O 2", "lat": -15.787509, "lon": -48.134744},
    {"nome": "Garagem Recanto", "lat": -15.922641, "lon": -48.108743},
    {"nome": "Garagem SOF Sul", "lat": -15.821254, "lon": -47.954418},
    {"nome": "Garagem QNR", "lat": -15.807516, "lon": -48.157667},
    {"nome": "Garagem Setor O 1", "lat": -15.788000, "lon": -48.135000},
    {"nome": "Garagem Brazlândia", "lat": -15.681840, "lon": -48.188312}
]

RAIO_GARAGEM = 0.004 

@app.route('/api/bsbus/frota', methods=['GET'])
def obter_frota():
    try:
        # Busca dados na API da SEMOB
        resposta = requests.get(URL_SEMOB, timeout=30)
        dados = resposta.json()
        features = dados.get("features", [])
        lista_frota = []
        
        for item in features:
            props = item.get("properties", {})
            coords = item.get("geometry", {}).get("coordinates", [0, 0])
            lat, lon = coords[1], coords[0]
            
            # Limpeza do prefixo
            prefixo = str(props.get("numero_veiculo") or props.get("prefixo") or "").strip()
            
            # Limpeza do número da linha
            linha_bruta = (props.get("cd_linha") or props.get("numero_linha") or 
                           props.get("codigo_linha") or props.get("id_linha") or 
                           props.get("linha") or "")
            linha = str(linha_bruta).strip().replace(",", ".")
            
            # Checagem de proximidade com garagens
            na_garagem = any(math.sqrt((lat - g["lat"])**2 + (lon - g["lon"])**2) < RAIO_GARAGEM for g in GARAGENS)
            
            # Validação de linha
            linha_invalida = not linha or linha in ["0", "None", "null", ""] or linha.upper() in ["ESP", "ESPECIAL", "RECOLHE"]
            
            # Lógica de status e formatação para o Frontend
            if na_garagem:
                status = "garagem"
                linha_exibicao = "GARAGEM"
            elif not linha_invalida:
                status = "em_linha"
                linha_exibicao = linha # Enviamos o número puro para a busca funcionar
            else:
                status = "especial"
                linha_exibicao = "ESP"
                
            lista_frota.append({
                "prefixo": prefixo, 
                "linha": linha_exibicao, 
                "lat": lat, 
                "lon": lon,
                "status": status, 
                "velocidade": props.get("velocidade", "0"),
                "horario": props.get("datahora", "Recente")
            })
            
        return jsonify(lista_frota)
    except Exception as e:
        print(f"Erro no servidor: {e}")
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    # Roda o servidor localmente na porta 5000
    app.run(debug=True, port=5000)
