# 📜 Contrato de API: Proyecto "Centinela"

**Versión:** 1.0.0
**Protocolo:** HTTPS / REST
**Formato de Intercambio:** `application/json`

Este documento es la fuente de verdad para la comunicación entre el Frontend (AWS Amplify) y el Backend (AWS API Gateway + Lambda). La implementación técnica sigue estrictamente la especificación definida en `openapi.yml`.

## 🚀 Flujo de Trabajo (Frontend ↔ Backend)

1. **Solicitud de Subida:** El Frontend envía el nombre del archivo a `/api/v1/manuscripts/upload-url`.
2. **Autorización:** El Backend devuelve un `manuscriptId` único y una `uploadUrl` (URL pre-firmada de S3).
3. **Subida:** El Frontend realiza un `PUT` binario directamente a la `uploadUrl` obtenida.
4. **Polling:** El Frontend consulta periódicamente (cada 3s) el endpoint `/api/v1/manuscripts/{id}` para actualizar la barra de progreso (campo `status` y `progress`).
5. **Resultados:** Una vez que el estado sea `COMPLETED`, el Frontend consulta `/api/v1/manuscripts/{id}/results` para renderizar los hallazgos.

---

## 🛠️ Definición de Endpoints

### 1. Generación de URL de Subida

Inicia el proceso registrando el archivo y obteniendo permisos temporales para S3.

* **Endpoint:** `POST /api/v1/manuscripts/upload-url`
* **Request Body:**
```json
{ "fileName": "tesis_medicina_2024.pdf" }
```


* **Respuesta (200 OK):**
```json
{
  "message": "URL generada exitosamente",
  "manuscriptId": "8d0f2b7b-6cc7-4c06-8c9e-74e3ee2e0ae9",
  "fileKey": "uploads/8d0f2b7b-6cc7-4c06-8c9e-74e3ee2e0ae9.pdf",
  "uploadUrl": "https://bucket-name.s3.amazonaws.com/uploads/..."
}
```



### 2. Consulta de Estado

Endpoint utilizado para *polling* o para mostrar detalles generales del manuscrito.

* **Endpoint:** `GET /api/v1/manuscripts/{id}`
* **Respuesta (200 OK):**
```json
{
  "manuscriptId": "8d0f2b7b-6cc7-4c06-8c9e-74e3ee2e0ae9",
  "fileName": "tesis_medicina_2024.pdf",
  "status": "PROCESSING",
  "progress": { "totalBatches": 4, "processedBatches": 2 }
}
```



### 3. Obtención de Resultados

Retorna el desglose de referencias evaluadas una vez finalizado el proceso.

* **Endpoint:** `GET /api/v1/manuscripts/{id}/results`
* **Respuesta (200 OK):**
```json
[
  {
    "refId": "123",
    "citationText": "Smith, J. (2021). Journal of Fake Science, 12.",
    "isZombie": true,
    "analysisContext": "El artículo original fue retractado por manipulación de datos."
  },
  {
    "refId": "124",
    "citationText": "Doe, E. (2023). Nature Tech, 45.",
    "isZombie": false,
    "analysisContext": "Cita válida y vigente."
  }
]
```



---

## 💻 Instrucciones para los Equipos

### Para el Equipo de Frontend (Mocking)

No esperen a que el backend esté listo. Simulen la lógica de polling en su estado de React:

```javascript
// Simulación para trabajo en paralelo con React/Vite
export const getManuscriptStatus = async (id) => {
  return {
    manuscriptId: id,
    status: "PROCESSING",
    progress: { totalBatches: 5, processedBatches: 2 }
  };
};
```

### Para el Equipo de Backend

1. **Validación:** Todo input debe ser validado contra el esquema definido en `openapi.yml`.
2. **CORS:** Aseguren habilitar CORS en API Gateway para permitir peticiones desde el dominio de AWS Amplify.
3. **Consistencia:** Mantener siempre el formato `camelCase` en las respuestas JSON (ej. `manuscriptId`, `isZombie`).
4. **Fuente de la Verdad:** Cualquier cambio en la estructura de datos debe actualizar primero el archivo `openapi.yml` para evitar discrepancias entre el contrato y la implementación.