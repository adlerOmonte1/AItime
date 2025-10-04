import http.server
import socketserver
import json
import joblib
from scipy.interpolate import griddata
import numpy as np
import requests
from datetime import datetime
import os

# --- CONFIGURACIÓN ---
PORT = 8000
MODEL_FILE = 'datos_interpolacion.pkl'

# --- Carga el modelo una sola vez al iniciar el servidor ---
agente_interpolador = None
try:
    agente_interpolador = joblib.load(MODEL_FILE)
    print(f"✅ Agente '{MODEL_FILE}' cargado en memoria.")
except FileNotFoundError:
    print(f"❌ Error: El archivo del modelo '{MODEL_FILE}' no se encontró.")
    print("Asegúrate de que esté en la misma carpeta que app.py")

# --- FUNCIONES DE LÓGICA ---

def pronostico_con_tendencia(latitud, longitud, fecha_futura_str):
    """
    Pronostica la temperatura extrapolando la tendencia lineal de los datos históricos.
    """
    if agente_interpolador is None:
        return "Error: Modelo no cargado."

    try:
        fecha_obj = datetime.strptime(fecha_futura_str, '%Y-%m-%d')
        mes_dia = fecha_obj.strftime('%m-%d')
        anio_futuro = fecha_obj.year
    except ValueError:
        return "Formato de fecha inválido."

    temperaturas_historicas = []
    anios_historicos = []

    # 1. Recopila todos los datos históricos para ese día del año (ej. todos los '08-14')
    for anio in range(2015, 2025):
        fecha_historica_str = f"{anio}-{mes_dia}"
        if fecha_historica_str in agente_interpolador:
            datos_del_dia = agente_interpolador[fecha_historica_str]
            puntos_conocidos = datos_del_dia['puntos']
            valores_conocidos = datos_del_dia['valores']
            punto_deseado = (longitud, latitud)
            
            temp_estimada = griddata(puntos_conocidos, valores_conocidos, punto_deseado, method='cubic')
            
            if not np.isnan(temp_estimada):
                temperaturas_historicas.append(float(temp_estimada))
                anios_historicos.append(anio)

    # 2. Decide qué método usar
    if len(temperaturas_historicas) < 4: # Si hay muy pocos datos, no se puede calcular una tendencia fiable
        if not temperaturas_historicas:
            return f"No se encontraron datos históricos para el día {mes_dia}."
        # Si hay pocos datos, devolvemos el promedio simple (nuestro método anterior)
        pronostico_simple = np.mean(temperaturas_historicas)
        return f"{pronostico_simple:.2f}°C (Promedio simple, pocos datos para tendencia)"
    else:
        # 3. Calcula la regresión lineal (la línea de tendencia)
        # np.polyfit nos da la pendiente (m) y el intercepto (b) de la línea y = mx + b
        pendiente, intercepto = np.polyfit(anios_historicos, temperaturas_historicas, 1)
        
        # 4. Extrapola para predecir el valor en el año futuro
        pronostico_tendencia = (pendiente * anio_futuro) + intercepto
        return pronostico_tendencia

def obtener_ubicacion_osm(latitud, longitud):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitud}&lon={longitud}"
        headers = {'User-Agent': 'MiAppClimaUniversitaria/1.0 (tu.email@ejemplo.com)'}
        respuesta = requests.get(url, headers=headers)
        datos = respuesta.json()
        if 'address' in datos:
            address = datos['address']
            departamento = address.get('state', 'No encontrado')
            pais = address.get('country', 'No encontrado')
            return departamento, pais
        return "Desconocido", "Desconocido"
    except Exception:
        return "Error API", "Error API"

def obtener_temperatura_real(latitud, longitud, fecha_str):
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitud}&longitude={longitud}&start_date={fecha_str}&end_date={fecha_str}&daily=temperature_2m_mean"
    try:
        respuesta = requests.get(url)
        datos = respuesta.json()
        if 'daily' in datos and 'temperature_2m_mean' in datos['daily'] and datos['daily']['temperature_2m_mean']:
            return float(datos['daily']['temperature_2m_mean'][0])
        return "N/A (posiblemente fecha futura)"
    except Exception:
        return "Error API"

# --- Servidor HTTP ---
class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
        
    def do_GET(self):
        if self.path == '/': self.path = '/templates/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/api/get_location_data':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            lat, lon, fecha = data.get('latitude'), data.get('longitude'), data.get('date')
            print(f"Petición (con tendencia) recibida: Lat={lat}, Lon={lon}, Fecha={fecha}")

            departamento, pais = obtener_ubicacion_osm(lat, lon)
            prediccion = pronostico_con_tendencia(lat, lon, fecha)
            real = obtener_temperatura_real(lat, lon, fecha)

            response_data = {
                'departamento': departamento,
                'pais': pais,
                'prediccion_modelo': f"{prediccion:.2f}°C" if isinstance(prediccion, float) else prediccion,
                'temperatura_real': f"{real:.2f}°C" if isinstance(real, float) else real
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_error(404)

# --- Inicia el Servidor ---
if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"🚀 Servidor final (con tendencia) iniciado en http://localhost:{PORT}")
        httpd.serve_forever()