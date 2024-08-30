from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def custom_date_parser(date_str):
    try:
        return pd.to_datetime(date_str, format='%d/%m/%Y %H:%M:%S')
    except ValueError:
        try:
            return pd.to_datetime(date_str, format='%d/%m/%Y %H:%M')
        except ValueError:
            try:
                date_str_fixed = date_str.replace(' 24:', '00:', 1)
                return pd.to_datetime(date_str_fixed, format='%d/%m/%Y %H:%M')
            except ValueError:
                return None

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        file1 = request.files.get('file1')
        file2 = request.files.get('file2')

        if not file1 or not file2:
            return jsonify({'error': 'Both files are required'}), 400

        file1_path = os.path.join(UPLOAD_FOLDER, file1.filename)
        file2_path = os.path.join(UPLOAD_FOLDER, file2.filename)

        file1.save(file1_path)
        file2.save(file2_path)

        return jsonify({'status': 'files saved', 'file1_path': file1_path, 'file2_path': file2_path})

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process_files():
    try:
        data = request.get_json()
        file1_path = data['file1_path']
        file2_path = data['file2_path']

        try:
            tabla1 = pd.read_excel(file1_path)
            tabla2 = pd.read_excel(file2_path)
        except Exception as e:
            return jsonify({'error': f"Error reading Excel files: {str(e)}"}), 500

        required_columns_tabla1 = ['Fecha Contabilización', 'Fecha Uso', 'Equipo']
        required_columns_tabla2 = ['Fecha Uso', 'Equipo']

        for col in required_columns_tabla1:
            if col not in tabla1.columns:
                tabla1[col] = pd.NA

        for col in required_columns_tabla2:
            if col not in tabla2.columns:
                tabla2[col] = pd.NA

        if 'Fecha Contabilización' in tabla1.columns:
            tabla1['Fecha Contabilización'] = pd.to_datetime(tabla1['Fecha Contabilización'], errors='coerce').dt.floor('T')
        if 'Fecha Uso' in tabla1.columns:
            tabla1['Fecha Uso'] = pd.to_datetime(tabla1['Fecha Uso'], errors='coerce').dt.floor('T')
        if 'Fecha Uso' in tabla2.columns:
            tabla2['Fecha Uso'] = pd.to_datetime(tabla2['Fecha Uso'], errors='coerce').dt.floor('T')

        if 'Equipo' in tabla1.columns:
            tabla1['Equipo'] = tabla1['Equipo'].str.replace('SAO-', '', regex=False)
        if 'Equipo' in tabla2.columns:
            tabla2['Equipo'] = tabla2['Equipo'].str.replace('SAO', '', regex=False)

        if 'Fecha Contabilización' in tabla1.columns:
            tabla1.sort_values(by=['Equipo', 'Fecha Contabilización'], inplace=True)

        usuarios_sin_servicio = []
        total_rows = len(tabla2)
        for index, uso in tabla2.iterrows():
            fecha_uso = uso['Fecha Uso']
            codigo_equipo = uso['Equipo']

            if pd.isna(fecha_uso) or pd.isna(codigo_equipo):
                continue

            servicio = tabla1[(tabla1['Equipo'] == codigo_equipo) & 
                              (tabla1['Fecha Contabilización'] <= fecha_uso) & 
                              (tabla1['Fecha Uso'] >= fecha_uso)]
            
            if servicio.empty:
                usuarios_sin_servicio.append(uso)

        usuarios_sin_servicio_df = pd.DataFrame(usuarios_sin_servicio)

        columns_to_keep = ['Fecha Contabilización', 'Fecha Uso', 'Equipo']
        usuarios_sin_servicio_df = usuarios_sin_servicio_df[columns_to_keep].copy()

        output_file = 'usos_sin_servicioss.xlsx'
        output_path = os.path.join(UPLOAD_FOLDER, output_file)
        usuarios_sin_servicio_df.to_excel(output_path, index=False)

        return jsonify({'file': output_file})

    except Exception as e:
        print(f"Error occurred during processing: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        print(f"Error occurred during file download: {str(e)}")
        return jsonify({'error': str(e)}), 500
