import os
import json
import uuid
import boto3
from botocore.exceptions import ClientError

# Inicializar el cliente de S3
# En AWS Lambda, la región se infiere automáticamente, pero es buena práctica declararla
s3_client = boto3.client('s3')
BUCKET_NAME = os.environ.get('RAW_BUCKET_NAME')

def lambda_handler(event, context):
    try:
        # 1. Parsear el cuerpo de la petición (manejando tanto string como dict por seguridad)
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)

        file_name = body.get('fileName', 'documento_sin_nombre.pdf')

        # 2. Generar identificadores únicos
        manuscript_id = str(uuid.uuid4())

        # Extraer extensión y crear una ruta segura en S3
        ext = file_name.split('.')[-1] if '.' in file_name else 'pdf'
        file_key = f"uploads/{manuscript_id}.{ext}"

        # 3. Generar la Presigned URL para el método PUT
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': file_key,
                'ContentType': 'application/pdf' # Ajustable según el tipo real
            },
            ExpiresIn=900 # La URL es válida por 15 minutos (900 segundos)
        )

        # 4. Retornar la respuesta estructurada para el Frontend
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*", # Importante para CORS
                "Access-Control-Allow-Credentials": True,
            },
            "body": json.dumps({
                "message": "URL generada exitosamente",
                "manuscriptId": manuscript_id,
                "fileKey": file_key,
                "uploadUrl": presigned_url
            })
        }

    except ClientError as e:
        print(f"[ERROR] AWS ClientError: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error interno al generar URL de S3"})
        }
    except Exception as e:
        print(f"[ERROR] Excepción inesperada: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Petición mal formada"})
        }
