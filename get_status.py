import os
import json
import boto3
from decimal import Decimal

TABLE_NAME = os.environ.get("TABLE_NAME", "centinela-integridad")
dynamodb = boto3.resource("dynamodb")
tabla = dynamodb.Table(TABLE_NAME)

ESTADO_A_STATUS = {
    "PENDIENTE":  "PENDING",
    "PROCESANDO": "PROCESSING",
    "COMPLETADO": "COMPLETED",
    "ERROR":      "ERROR",
}

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return super(DecimalEncoder, self).default(obj)

def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": True,
    }

def _to_contract(manuscript_id, item):
    estado = item.get("estado", "PENDIENTE")
    status = ESTADO_A_STATUS.get(estado, "PROCESSING")

    # 1. Obtenemos los valores reales desde DynamoDB
    total_refs = int(item.get("totalRefs", 0))
    refs_procesadas = int(item.get("refsProcesadas", 0))
    total_batches = int(item.get("totalBatches", 0))

    # 2. Calculamos los lotes procesados dividiendo las referencias entre 10
    procesadas = refs_procesadas // 10

    # 3. Aseguramos que la barra llegue al 100% (igualando al total de lotes) al finalizar
    if refs_procesadas > 0 and refs_procesadas >= total_refs:
        procesadas = total_batches
        status = "COMPLETED"

    indice = item.get("indiceIntegridad")
    indice = int(indice) if indice is not None else None

    topic = item.get("tema") or item.get("Topic")

    return {
        "manuscriptId": manuscript_id,
        "fileName": item.get("fileName", ""),
        "status": status,
        "progress": {
            "totalBatches": total_batches,
            "processedBatches": procesadas,
        },
        "globalIntegrityIndex": indice,
        "topic": topic,
    }

def lambda_handler(event, context):
    manuscript_id = event["pathParameters"]["id"]

    try:
        response = tabla.get_item(
            Key={"PK": f"MANUSCRIPT#{manuscript_id}", "SK": "METADATA"}
        )
        item = response.get("Item")

        if not item:
            return {
                "statusCode": 404,
                "headers": _cors_headers(),
                "body": json.dumps({"error": "Manuscrito no encontrado"})
            }

        return {
            "statusCode": 200,
            "headers": _cors_headers(),
            "body": json.dumps(_to_contract(manuscript_id, item), cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"[ERROR] get_status: {e}")
        return {
            "statusCode": 500,
            "headers": _cors_headers(),
            "body": json.dumps({"error": "Error interno del servidor"})
        }