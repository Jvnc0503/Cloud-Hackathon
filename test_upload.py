import os
import sys
import requests

# ---------------------------------------------------------
# Configuración del entorno de pruebas
# ---------------------------------------------------------
# Extraemos la URL desde las variables de entorno
API_URL = os.environ.get("API_URL")

def test_pipeline_subida(file_path):
    # 1. Validación de seguridad de la URL
    if not API_URL:
        print("❌ Error crítico: La variable de entorno 'API_URL' no está configurada.")
        print("💡 Ejecuta el script de la siguiente manera:")
        print(f"   API_URL='https://tu-api.amazonaws.com/...' python {sys.argv[0]} {file_path}\n")
        return

    # 2. Validación de existencia del archivo
    if not os.path.exists(file_path):
        print(f"❌ Error crítico: No se encontró el archivo '{file_path}' en tu sistema.")
        print("💡 Verifica la ruta y vuelve a intentarlo.\n")
        return

    print(f"🚀 Iniciando prueba automatizada para: '{file_path}'\n")

    # 3. Obtener la URL pre-firmada desde API Gateway
    print("1️⃣  Solicitando autorización al Backend (GetUploadURL)...")
    payload = {"fileName": os.path.basename(file_path)}
    
    response = requests.post(API_URL, json=payload)

    if response.status_code != 200:
        print(f"❌ Falló la comunicación con la API: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    upload_url = data.get("uploadUrl")
    manuscript_id = data.get("manuscriptId")
    
    print(f"✅ Autorización concedida. ID asignado: {manuscript_id}\n")

    # 4. Leer el archivo binario y subirlo directamente a S3
    print("2️⃣  Subiendo el documento directamente a S3 RAW...")
    
    try:
        with open(file_path, "rb") as file_data:
            # S3 exige que el Content-Type coincida exactamente con el que firmó la Lambda
            headers = {"Content-Type": "application/pdf"}
            
            s3_response = requests.put(upload_url, data=file_data, headers=headers)
            
            if s3_response.status_code == 200:
                print("✅ ¡Subida a S3 exitosa!")
                print(f"⏳ La cadena de eventos asíncrona de AWS ha comenzado para {manuscript_id}.")
                print("   (Revisa los logs con: sls logs -f ConvertManuscript -t)")
            else:
                print(f"❌ S3 rechazó el archivo. Código HTTP: {s3_response.status_code}")
                print(s3_response.text)
                
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado al subir a S3: {str(e)}")

if __name__ == "__main__":
    # Capturar y validar los argumentos de la terminal
    # sys.argv[0] es el nombre del script (test_upload.py)
    # sys.argv[1] será el primer argumento (la ruta del archivo)
    
    if len(sys.argv) < 2:
        print("❌ Error: Faltan argumentos.")
        print(f"💡 Uso correcto: python {sys.argv[0]} <ruta_al_archivo.pdf>")
        sys.exit(1)
        
    archivo_a_subir = sys.argv[1]
    test_pipeline_subida(archivo_a_subir)