# Auditor Agéntico de Facturación de Siniestros

Agente de IA que recibe, en texto libre, el número de un siniestro y el detalle de una factura
enviada por un taller, y la audita automáticamente contra el tarifario acordado y los ítems
autorizados de ese siniestro — detectando precios fuera de tolerancia, ítems no reconocidos o no
autorizados, cobros duplicados, cantidades sospechosas y totales de factura que no cuadran.

🔗 **App en vivo: https://auditor-de-facturacion-hackiaton-onevision-cvrsvgatvywgzq33a24.streamlit.app/

---

## Cómo usarlo (para quien evalúa el proyecto)

1. Abre el enlace de la app. No necesitas crear ninguna cuenta ni configurar nada — la API key
   ya está configurada del lado del servidor.
2. En el campo de texto, escribe el número de siniestro y el detalle de la factura, por ejemplo:
   ```
   Siniestro SIN-2026-045. Factura del taller: Parachoques delantero, 1 unidad, $180.
   Pintura y laca, 1 unidad, $90.
   ```
3. Clic en **"Auditar factura"**. En unos segundos verás el veredicto (aprobado, aprobado con
   observaciones, o rechazado) y la lista de discrepancias si las hay.
4. Puedes seguir escribiendo más facturas en la misma sesión — el agente recuerda el contexto
   de auditorías anteriores, y puedes hacerle preguntas de seguimiento.
5. Al final de la página hay un botón para **descargar el historial de la sesión en CSV**, y un
   panel desplegable con el tarifario y los siniestros de prueba, para que puedas ver contra qué
   se está comparando cada factura.

**Casos de prueba sugeridos** (ver `INFORME.md` para la lista completa con resultado esperado):
- Un ítem con precio distinto al tarifario → debe marcar la discrepancia con el % de diferencia.
- Un ítem inventado que no existe en el tarifario → debe marcarlo como "no reconocido", nunca
  aprobarlo a ciegas.
- Un número de siniestro que no existe → debe rechazar de inmediato.

---

## Arquitectura

```
Usuario escribe la factura en texto libre
            │
            ▼
      app.py (Streamlit)
            │
            ▼
   agent.py → Groq (tool-calling)
            │
            ▼
   auditar_factura() ── revisa data/tarifario.json y data/siniestros.json
            │            (precios, autorización, duplicados — 100% determinístico)
            ▼
   El modelo redacta el veredicto final en JSON
```

La parte que decide si algo está mal (precios, duplicados, autorización, totales) es código
Python normal, no el LLM — así el resultado es siempre consistente. El modelo solo se usa para
entender el texto libre de la factura y redactar el resumen final. Ver `INFORME.md` para el
detalle completo de cada regla de validación.

---

## Cómo correrlo localmente (para desarrollo)

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Conseguir una API key de Groq (gratis, sin tarjeta de crédito)
Ve a [console.groq.com](https://console.groq.com), crea una cuenta y genera una API key en
la sección "API Keys".

### 3. Guardar la key para desarrollo local
Crea el archivo `.streamlit/secrets.toml` (no lo subas a git, ya está en `.gitignore`):
```toml
GROQ_API_KEY = "tu-api-key-aqui"
```

### 4. Correr la app
```bash
streamlit run app.py
```
Se abre en `http://localhost:8501`.

### 5. Correr las pruebas (no requieren API key ni internet)
```bash
python3 test_agent.py
python3 test_robustez.py
python3 test_auditoria_real.py
```
Los 18 casos deben pasar — validan toda la lógica de negocio de forma aislada.

---

## Cómo desplegarlo (enlace público)

1. Sube el proyecto a un repositorio de GitHub (sin el archivo `secrets.toml`).
2. Ve a [share.streamlit.io](https://share.streamlit.io) y conecta tu cuenta de GitHub.
3. **Create app** → selecciona el repo, branch `main`, main file `app.py`.
4. En **Advanced settings → Secrets**, pega:
   ```toml
   GROQ_API_KEY = "tu-api-key-aqui"
   ```
5. Deploy. Obtienes una URL pública permanente (`https://tu-app.streamlit.app`) que no requiere
   que la persona que la abre configure nada — esa es la que se comparte como "agente funcional".

---

## Estructura del proyecto

```
├── app.py                    # Interfaz Streamlit
├── agent.py                  # Lógica del agente (herramienta + tool-calling con Groq)
├── requirements.txt          # Dependencias
├── INFORME.md                # Explicación técnica detallada de cada componente y regla
├── README.md                 # Este archivo
├── test_agent.py             # Pruebas: casos base
├── test_robustez.py          # Pruebas: variaciones de texto y datos incompletos
├── test_auditoria_real.py    # Pruebas: tolerancia de precio, cantidad, total declarado
└── data/
    ├── tarifario.json        # 27 ítems con su precio acordado
    └── siniestros.json       # 5 siniestros de ejemplo con sus ítems autorizados
```

## Personalizar los datos

Para agregar más ítems o siniestros, edita directamente `data/tarifario.json` y
`data/siniestros.json` — son arrays JSON simples, no requieren ninguna base de datos externa.
No hace falta reiniciar nada: al hacer push, Streamlit Cloud redespliega solo.
