import os
import json
import boto3
from decimal import Decimal

TABLE_NAME = os.environ.get("TABLE_NAME", "centinela-integridad")
dynamodb = boto3.resource("dynamodb")
tabla = dynamodb.Table(TABLE_NAME)

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
            
        item.pop("PK", None)
        item.pop("SK", None)
        item["manuscriptId"] = manuscript_id
        
        return {
            "statusCode": 200,
            "headers": _cors_headers(),
            "body": json.dumps(item, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"[ERROR] get_status: {e}")
        return {
            "statusCode": 500,
            "headers": _cors_headers(),
            "body": json.dumps({"error": "Error interno del servidor"})
        }