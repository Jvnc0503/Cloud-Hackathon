import os
import sys
import requests
import time

BASE_URL = os.environ.get("BASE_URL")

def test_pipeline_completo(file_path):
    if not BASE_URL:
        print("Error: La variable 'BASE_URL' no esta configurada.")
        return

    print(f"[INIT] Iniciando prueba completa: '{file_path}'")

    # 1. Obtener URL de subida
    print("[1] Solicitando URL de subida...")
    resp = requests.post(f"{BASE_URL}/api/v1/manuscripts/upload-url", json={"fileName": os.path.basename(file_path)})
    data = resp.json()
    manuscript_id = data["manuscriptId"]
    upload_url = data["uploadUrl"]

    # 2. Subir archivo a S3
    print(f"[2] Subiendo archivo a S3 (ID: {manuscript_id})...")
    with open(file_path, "rb") as f:
        requests.put(upload_url, data=f, headers={"Content-Type": "application/pdf"})
    
    print("    Subida exitosa. Iniciando Polling...")

    # 3. Consultar Estado (Polling Real)
    estado = "PROCESSING"
    while estado in ["PROCESSING", "PENDING"]:
        time.sleep(5)
        status_resp = requests.get(f"{BASE_URL}/api/v1/manuscripts/{manuscript_id}")
        status_data = status_resp.json()
        estado = status_data.get('status', 'PENDING')
        progreso = status_data.get('progress', {})
        print(f"    [POLLING] Estado: {estado} | Lotes procesados: {progreso.get('processedBatches', 0)}/{progreso.get('totalBatches', 0)}")

    # 4. Consultar Resultados (GET /manuscripts/{id}/results)
    print("\n[3] Consultando resultados finales...")
    res_resp = requests.get(f"{BASE_URL}/api/v1/manuscripts/{manuscript_id}/results")
    datos = res_resp.json()
    
    print(f"    Referencias evaluadas: {datos.get('totalEvaluated', 0)}")
    print(f"    Citas zombi detectadas: {datos.get('zombieCount', 0)}")
    
    citas = datos.get('results', [])
    if citas:
        print("\n    --- Detalle de Citas ---")
        for i, cita in enumerate(citas, 1):
            if cita.get('isZombie'):
                estado_icono = "[ZOMBI]"
            elif "progreso" in cita.get('analysisContext', '').lower():
                estado_icono = "[PENDIENTE]"
            else:
                estado_icono = "[OK]"
            
            texto_corto = cita.get('citationText', 'Sin texto')[:80]
            print(f"    {i}. {estado_icono} {texto_corto}...")
            
            if cita.get('isZombie'):
                contexto = cita.get('analysisContext', 'Sin contexto')
                print(f"       Analisis: {contexto}")
    
    print("\n[END] Prueba finalizada correctamente.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: BASE_URL='...' python test_upload.py <archivo.pdf>")
        sys.exit(1)
        
    test_pipeline_completo(sys.argv[1])