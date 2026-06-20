import os
import sys
import boto3
from urllib.parse import unquote_plus

cur_dir = os.path.dirname(os.path.abspath(__file__))
markitdown_path = os.path.join(cur_dir, 'markitdown-deps') 
sys.path.insert(0, markitdown_path) # Aseguramos que el módulo MarkItDown esté en el path para importarlo sin problemas

from markitdown import MarkItDown

# Inicializamos el cliente de S3
s3_client = boto3.client('s3')

# Extraemos el bucket de destino desde las variables de entorno
MD_BUCKET = os.environ.get('MD_BUCKET_NAME')

def lambda_handler(event, context):
    try:
        # 1. Analizar el evento asíncrono de S3
        # Iteramos sobre los records (usualmente viene 1, pero es buena práctica)
        for record in event.get('Records', []):
            source_bucket = record['s3']['bucket']['name']
            # unquote_plus maneja caracteres especiales o espacios en el nombre del archivo
            file_key = unquote_plus(record['s3']['object']['key'])
            
            print(f"[INFO] Iniciando conversión para: s3://{source_bucket}/{file_key}")
            
            # 2. Definir rutas temporales en el almacenamiento efímero de Lambda (/tmp)
            file_name = os.path.basename(file_key)
            base_name = os.path.splitext(file_name)[0]
            
            local_input_path = f"/tmp/{file_name}"
            local_output_path = f"/tmp/{base_name}.md"
            
            # El archivo procesado se guardará en la raíz del bucket MD con el mismo UUID
            md_file_key = f"{base_name}.md"

            # 3. Descargar el archivo original (PDF, DOCX, etc.)
            s3_client.download_file(source_bucket, file_key, local_input_path)
            print(f"[INFO] Archivo descargado exitosamente en {local_input_path}")

            # 4. Transformación mágica con MarkItDown
            md_converter = MarkItDown()
            conversion_result = md_converter.convert(local_input_path)
            
            # Guardar el contenido convertido en un archivo .md local
            with open(local_output_path, "w", encoding="utf-8") as f:
                f.write(conversion_result.text_content)
            
            # 5. Subir el nuevo archivo Markdown al bucket MD
            s3_client.upload_file(local_output_path, MD_BUCKET, md_file_key)
            print(f"[SUCCESS] Archivo convertido y subido a s3://{MD_BUCKET}/{md_file_key}")
            
            # 6. Limpieza de entorno (Buenas prácticas de Lambda)
            if os.path.exists(local_input_path):
                os.remove(local_input_path)
            if os.path.exists(local_output_path):
                os.remove(local_output_path)

        return {
            'statusCode': 200,
            'body': 'Conversión completada con éxito.'
        }

    except Exception as e:
        print(f"[ERROR] Fallo crítico durante la conversión: {str(e)}")
        # Propagamos el error para que CloudWatch y el mecanismo de reintentos lo registren
        raise e