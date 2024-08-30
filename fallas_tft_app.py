from flask import Flask, request, send_file
from flask_cors import CORS
import pandas as pd
import re
import os

app = Flask(__name__)
CORS(app)

# Configura las carpetas para almacenar archivos cargados y resultados
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

# Crea las carpetas si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.route('/upload_fallas_tft', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    if file and file.filename.endswith('.xlsx'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        # Procesa el archivo y guarda el resultado
        process_file(file_path)
        
        result_file = os.path.join(app.config['RESULT_FOLDER'], 'tft_lista_julio.xlsx')
        
        # Verifica si el archivo procesado existe antes de enviarlo
        if os.path.exists(result_file):
            return send_file(result_file, as_attachment=True)
        else:
            return 'Error processing file', 500
    else:
        return 'Invalid file format', 400

def process_file(file_path):
    # Inicializar listas para almacenar unidades e incidencias
    unidades = []
    incidencias = []

    # Expresión regular para encontrar la palabra clave "unidades_" seguida de números de vehículos
    patron_unidades = re.compile(r'unidades_([\d.,\s-]+)', re.IGNORECASE)

    # Leer el archivo
    df = pd.read_excel(file_path)

    # Iterar sobre cada fila del DataFrame
    for index, row in df.iterrows():
        incidencia = row['ID']
        observaciones = row['Observaciones']
        codigo_vehiculo = row['Código Vehículo']

        if codigo_vehiculo == "N.D.":
            # Buscar la palabra clave "unidades_" en las observaciones
            match = patron_unidades.search(observaciones)
            if match:
                # Extraer los números de vehículos
                numeros_vehiculo = re.findall(r'\d+', match.group(1))
                # Relacionar cada número de vehículo con la incidencia correspondiente
                for numero in numeros_vehiculo:
                    unidades.append(numero.strip())  # Eliminar espacios en blanco alrededor de los números
                    incidencias.append(incidencia)
        else:
            # Si el valor en 'Código Vehículo' no es "N.D.", 
            # eliminar el prefijo "SAO -" y agregar el número a la lista de unidades
            numero_vehiculo = re.search(r'\d+', codigo_vehiculo).group()
            unidades.append(numero_vehiculo)
            incidencias.append(incidencia)

    # Crear un nuevo DataFrame con las unidades y sus incidencias asociadas
    nuevo_df = pd.DataFrame({'unidad': unidades, 'incidencia': incidencias})

    nuevo_df['unidad'] = nuevo_df['unidad'].astype(int)
    nuevo_df['incidencia'] = nuevo_df['incidencia'].astype(str)

    # Guardar el nuevo DataFrame como un archivo Excel
    result_file = os.path.join(app.config['RESULT_FOLDER'], 'tft_lista_julio.xlsx')
    nuevo_df.to_excel(result_file, index=False)
    print('Archivo procesado con éxito')

