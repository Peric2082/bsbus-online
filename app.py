from flask import Flask, jsonify
from flask_cors import CORS
import requests
import math
import urllib3

# Desativa avisos de certificado
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

URL_SEMOB = "https://geoserver.semob.df.gov.br/geoserver/semob/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=semob%3Aultima_posicao&cql_filter=id_operadora='3450'&outputFormat=application/json"

# Lista de proxies gratuitos (o requests tentará usar estes para sair com outro IP)
PROXIES = {
    'http': 'http://185.162.229.40:80',
    'https': 'http://185.162.229.40:80'
}

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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        
        # Tenta a conexão através do proxy para esconder o IP do Render
        resposta = requests.get(URL_SEMOB, headers=headers, timeout=15, proxies=PROXIES, verify=False)
        
        dados = resposta.json()
        features = dados.get("features", [])
        lista_frota = []
        
        for item in features:
            props = item.get("properties", {})
            coords = item.get("geometry", {}).get("coordinates", [0, 0])
            lat, lon = coords[1], coords[0]
            
            prefixo = str(props.get("numero_veiculo") or props.get("prefixo") or "").strip()
            linha_bruta = (props.get("cd_linha") or props.get("numero_linha") or props.get("codigo_linha") or props.get("id_linha") or props.get("linha") or "")
            linha = str(linha_bruta).strip().replace(",", ".")
            
            na_garagem = any(math.sqrt((lat - g["lat"])**2 + (lon - g["lon"])**2) < RAIO_GARAGEM for g in GARAGENS)
            linha_invalida = not linha or linha in ["0", "None", "null", ""] or linha.upper() in ["ESP", "ESPECIAL", "RECOLHE"]
            
            if na_garagem:
                status, linha_exibicao = "garagem", "GARAGEM"
            elif not linha_invalida:
                status, linha_exibicao = "em_linha", linha
            else:
                status, linha_exibicao = "especial", "ESP"
                
            lista_frota.append({
                "prefixo": prefixo, "linha": linha_exibicao, "lat": lat, "lon": lon,
                "status": status, "velocidade": props.get("velocidade", "0"),
                "horario": props.get("datahora", "Recente")
            })
            
        return jsonify(lista_frota)
    except Exception as e:
        # Se falhar pelo proxy, tenta sem proxy direto (fallback)
        try:
            resposta = requests.get(URL_SEMOB, headers=headers, timeout=15, verify=False)
            return jsonify(resposta.json())
        except:
            return jsonify({"erro": f"Proxy falhou e conexão direta bloqueada: {str(e)}"}), 500
