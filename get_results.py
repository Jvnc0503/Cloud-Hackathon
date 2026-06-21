import os
import json
import boto3
from boto3.dynamodb.conditions import Key
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
        response = tabla.query(
            KeyConditionExpression=Key("PK").eq(f"MANUSCRIPT#{manuscript_id}") & Key("SK").begins_with("REF#")
        )
        items = response.get("Items", [])
        
        for item in items:
            item.pop("PK", None)
            item["refId"] = item.pop("SK", "").replace("REF#", "")
            
        return {
            "statusCode": 200,
            "headers": _cors_headers(),
            "body": json.dumps(items, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"[ERROR] get_results: {e}")
        return {
            "statusCode": 500,
            "headers": _cors_headers(),
            "body": json.dumps({"error": "Error interno del servidor"})
        }