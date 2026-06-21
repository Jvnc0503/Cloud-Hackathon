import os
import json
import time
import urllib.parse
import urllib.request
import urllib.error
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TABLE_NAME = os.environ["TABLE_NAME"]
GROQ_MODEL = os.environ["GROQ_MODEL"]
CONTACT_EMAIL = os.environ["CONTACT_EMAIL"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

tabla = boto3.resource("dynamodb").Table(TABLE_NAME)

PROMPTS_POR_TEMA = {
    "medicina": "Eres un revisor experto en medicina y ciencias clinicas.",
    "biotecnologia": "Eres un revisor experto en biotecnologia y ciencias moleculares.",
    "ingenieria": "Eres un revisor experto en ingenieria y ciencias aplicadas.",
    "computacion": "Eres un revisor experto en computacion e informatica.",
}
PROMPT_DEFECTO = "Eres un revisor experto en integridad cientifica."

INSTRUCCION = (
    " El articulo citado fue RETRACTADO. Analiza como lo usa el autor y responde "
    "UNICAMENTE con un JSON valido con esta forma: "
    '{"veredicto": "ignora_retraccion" | "cita_como_error" | "incierto", '
    '"justificacion": "<una frase breve>", "confianza": <numero entre 0 y 1>}. '
    'Usa "ignora_retraccion" si el autor lo presenta como evidencia valida sin notar '
    'que fue retractado; usa "cita_como_error" si lo menciona justamente como ejemplo '
    "de error, fraude o caso retractado."
)


def lambda_handler(event, context):
    fallidas = []
    total_mensajes = len(event["Records"])
    
    print(f"[INIT] Procesando lote de {total_mensajes} mensajes SQS.")
    
    for record in event["Records"]:
        try:
            _procesar(json.loads(record["body"]))
        except Exception as e:
            print(f"[ERROR] Fallo en mensaje {record['messageId']}: {e}")
            fallidas.append({"itemIdentifier": record["messageId"]})
            
    print(f"[END] Lote finalizado. Mensajes fallidos devueltos a SQS: {len(fallidas)}")
    return {"batchItemFailures": fallidas}


def _procesar(msg):
    manuscript_id = msg["manuscriptId"]
    ref_id = msg["refId"]
    tema = msg.get("tema", "General")
    doi = msg.get("doi")

    print(f"[INFO] Evaluando MS: {manuscript_id} | REF: {ref_id} | DOI: {doi}")

    retraccion = _consultar_crossref(doi)
    veredicto = None

    if retraccion.get("retractada"):
        estado = "RETRACTADA"
        print(f"[ALERT] DOI {doi} retractado. Iniciando validacion semantica (Groq).")
        veredicto = _juzgar_con_groq(tema, msg.get("citaCruda", ""), msg.get("contexto", ""))
        print(f"[LLM] Veredicto: {veredicto.get('veredicto')} | Confianza: {veredicto.get('confianza')}")
        
    elif not retraccion.get("verificada"):
        estado = "NO_VERIFICADA"
        print(f"[WARN] DOI {doi} no registrado en Crossref.")
    else:
        estado = "OK"
        print(f"[OK] DOI {doi} verificado sin retractaciones.")

    primera_vez = _guardar_resultado(manuscript_id, ref_id, estado, retraccion, veredicto)
    
    if primera_vez:
        _sumar_procesada(manuscript_id, bool(retraccion.get("retractada")))


def _consultar_crossref(doi):
    if not doi:
        return {"verificada": False}

    url = ("https://api.crossref.org/works/"
           + urllib.parse.quote(doi, safe="")
           + "?mailto=" + urllib.parse.quote(CONTACT_EMAIL))
    req = urllib.request.Request(
        url, headers={"User-Agent": f"CentinelaIntegridad/1.0 (mailto:{CONTACT_EMAIL})"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"verificada": False}     
        print(f"[ERROR] Crossref HTTP {e.code} para DOI {doi}.")
        raise                                

    actualizaciones = data.get("message", {}).get("updated-by", []) or []
    retracciones = [u for u in actualizaciones if u.get("type") == "retraction"]
    preocupaciones = [u for u in actualizaciones if "concern" in (u.get("type") or "")]
    return {
        "verificada": True,
        "retractada": len(retracciones) > 0,
        "expresionPreocupacion": len(preocupaciones) > 0,
    }


def _juzgar_con_groq(tema, cita, contexto):
    sistema = PROMPTS_POR_TEMA.get(tema, PROMPT_DEFECTO) + INSTRUCCION
    usuario = (f"Entrada bibliografica:\n{cita}\n\n"
               f"Contexto donde aparece la cita:\n{contexto}")
    cuerpo = json.dumps({
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        GROQ_URL, data=cuerpo, method="POST",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "CentinelaIntegridad/1.0",
        },
    )

    for intento in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                contenido = data["choices"][0]["message"]["content"]
                return json.loads(contenido, parse_float=Decimal)
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento < 2:
                print(f"[WARN] Limite Groq alcanzado (429). Reintento en {2 ** intento}s.")
                time.sleep(2 ** intento)
                continue
            print(f"[ERROR] Groq HTTP {e.code}.")
            raise


def _guardar_resultado(manuscript_id, ref_id, estado, retraccion, veredicto):
    expr = "SET #estado = :e, estaRetractada = :r, verificada = :v"
    vals = {
        ":e": estado,
        ":r": bool(retraccion.get("retractada")),
        ":v": bool(retraccion.get("verificada")),
        ":pendiente": "PENDIENTE",
    }
    if veredicto is not None:
        expr += ", veredictoLLM = :vd"
        vals[":vd"] = veredicto
    try:
        tabla.update_item(
            Key={"PK": f"MANUSCRIPT#{manuscript_id}", "SK": f"REF#{ref_id}"},
            UpdateExpression=expr,
            ConditionExpression="#estado = :pendiente",   
            ExpressionAttributeNames={"#estado": "estado"},
            ExpressionAttributeValues=vals,
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print(f"[IDEMPOTENCIA] REF#{ref_id} previamente procesada. Omitiendo reconteo.")
            return False
        raise


def _sumar_procesada(manuscript_id, retractada):
    resp = tabla.update_item(
        Key={"PK": f"MANUSCRIPT#{manuscript_id}", "SK": "METADATA"},
        UpdateExpression="ADD refsProcesadas :uno, refsRetractadas :r",
        ExpressionAttributeValues={":uno": 1, ":r": (1 if retractada else 0)},
        ReturnValues="ALL_NEW",   
    )
    item = resp["Attributes"]
    total = int(item.get("totalRefs", 0))
    procesadas = int(item.get("refsProcesadas", 0))
    
    print(f"[DB] Progreso MS {manuscript_id}: {procesadas}/{total} completadas.")
    
    if total and procesadas >= total:
        _cerrar_manuscrito(manuscript_id, total, int(item.get("refsRetractadas", 0)))


def _cerrar_manuscrito(manuscript_id, total, retractadas):
    indice = int(round((1 - retractadas / total) * 100)) if total else 0
    tabla.update_item(
        Key={"PK": f"MANUSCRIPT#{manuscript_id}", "SK": "METADATA"},
        UpdateExpression="SET #estado = :c, indiceIntegridad = :i",
        ExpressionAttributeNames={"#estado": "estado"},
        ExpressionAttributeValues={":c": "COMPLETADO", ":i": indice},
    )
    print(f"[CIERRE] MS {manuscript_id} finalizado. Indice Integridad: {indice}%. Retractadas: {retractadas}/{total}")