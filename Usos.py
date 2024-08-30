from flask import Flask, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO
import pandas as pd
import io
import xlsxwriter

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

def custom_date_parser(date_str):
    try:
        return pd.to_datetime(date_str, format='%d/%m/%Y %H:%M:%S')
    except ValueError:
        return pd.to_datetime(date_str, format='%d/%m/%Y %H:%M')

@app.route('/api/process-files', methods=['POST'])
def process_files():
    if 'file1' not in request.files or 'file2' not in request.files:
        return 'Missing files', 400

    file1 = request.files['file1']
    file2 = request.files['file2']

    # Leer archivos en pandas DataFrames
    tabla1 = pd.read_excel(file1, parse_dates=['Inicio Servicio Efectivo', 'Fin Servicio Efectivo'], date_parser=custom_date_parser)
    tabla2 = pd.read_excel(file2, parse_dates=['Fecha Uso'], date_parser=custom_date_parser)

    # Procesamiento de datos
    tabla1['Inicio Servicio Efectivo'] = pd.to_datetime(tabla1['Inicio Servicio Efectivo'])
    tabla1['Fin Servicio Efectivo'] = pd.to_datetime(tabla1['Fin Servicio Efectivo'])
    tabla2['Fecha Uso'] = pd.to_datetime(tabla2['Fecha Uso'])

    tabla1['Vehículos'] = tabla1['Vehículos'].str.replace('SAO-', '')
    tabla2['Equipo'] = tabla2['Equipo'].str.replace('SAO', '')

    usuarios_por_servicio = []

    for index, servicio in tabla1.iterrows():
        inicio_servicio = servicio['Inicio Servicio Efectivo']
        fin_servicio = servicio['Fin Servicio Efectivo']
        codigo_bus = servicio['Vehículos']
        distancia = servicio['Distancia']
        porcentaje_tiempo = servicio['% tiempo']
        porcentaje_paradas = servicio['% paradas']
        porcentaje_distancia = servicio['% distancia']
        linea = servicio['Línea']
        h_t = servicio['H-T']

        usuarios_servicio = tabla2[(tabla2['Fecha Uso'] >= inicio_servicio) &
                                   (tabla2['Fecha Uso'] <= fin_servicio) &
                                   (tabla2['Equipo'] == codigo_bus)]

        total_usuarios_servicio = len(usuarios_servicio)

        usuarios_por_servicio.append({
            'Servicio': index,
            'Vehículo': codigo_bus,
            'Inicio Servicio Efectivo': inicio_servicio,
            'Fin de Servicio Efectivo': fin_servicio,
            'Usuarios': total_usuarios_servicio,
            'Distancia': distancia,
            '%_tiempo': porcentaje_tiempo,
            'linea': linea,
            'H_T': h_t
        })
        

    usuarios_df = pd.DataFrame(usuarios_por_servicio)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        usuarios_df.to_excel(writer, index=False)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name='processed_file.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


