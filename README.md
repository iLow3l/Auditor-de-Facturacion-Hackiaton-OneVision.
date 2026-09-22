# Auditor Agéntico de Facturación de Siniestros

Agente que recibe en texto libre el número de siniestro y el detalle de una factura de taller,
y usa un LLM (Groq / Llama 3.3) con tool-calling para verificarla contra el tarifario acordado
y los ítems autorizados del siniestro, detectando precios distintos, cobros duplicados e ítems
no autorizados.

## Arquitectura

```
Usuario escribe la factura en texto libre
            │
            ▼
      app.py (Streamlit)
            │
            ▼
   agent.py → Groq (Llama 3.3) con tool-calling
            │
            ▼
   auditar_factura() ── revisa data/tarifario.json y data/siniestros.json
            │            (precios, autorización, duplicados — 100% determinístico)
            ▼
   Groq redacta el veredicto final en JSON
```

La parte que decide si algo está mal (precios, duplicados, autorización) es código Python
normal, no el LLM — así el resultado es siempre consistente. El LLM solo se usa para entender
el texto libre de la factura y redactar el resumen final.

## 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 2. Conseguir tu API key de Groq (gratis)

Ve a [console.groq.com](https://console.groq.com), crea una cuenta y genera una API key.

## 3. Correr localmente

```bash
streamlit run app.py
```

Se abre en `http://localhost:8501`. Pega tu API key en el campo de la interfaz, o guárdala
en `.streamlit/secrets.toml` (no lo subas a GitHub):

```toml
GROQ_API_KEY = "tu-api-key-aqui"
```

## 4. Probar

Escribe en el mensaje algo como:

```
Siniestro SIN-2026-045. Factura del taller: Parachoques delantero, 1 unidad, $180.
Pintura y laca, 1 unidad, $90.
```

Debe dar `aprobado_sin_observaciones` (los precios y los ítems coinciden con los datos de prueba).

Otros casos para probar:
- Cambia un precio (ej. $250 en vez de $180) → debe marcar discrepancia de precio.
- Repite el mismo ítem dos veces → debe marcar cobro duplicado.
- Usa un ítem que no está en `items_autorizados` de ese siniestro → debe marcarlo como no autorizado.
- Usa un número de siniestro que no existe → debe rechazar de inmediato.

## 5. Publicar (enlace público gratis)

1. Sube este proyecto a un repositorio de GitHub.
2. Ve a [share.streamlit.io](https://share.streamlit.io), conecta tu cuenta de GitHub, y selecciona
   el repo + `app.py` como archivo principal.
3. En **Advanced settings → Secrets**, agrega:
   ```toml
   GROQ_API_KEY = "tu-api-key-aqui"
   ```
4. Deploy. Streamlit te da una URL pública permanente (`https://tu-app.streamlit.app`) —
   esa es la que entregas como "agente funcional". No necesitas mantener tu computadora
   encendida ni usar túneles.

## Archivos del proyecto

- `app.py` — interfaz de Streamlit.
- `agent.py` — lógica del agente: el tool `auditar_factura` (determinístico) y el loop de
  tool-calling con Groq.
- `data/tarifario.json` — precios acordados por ítem.
- `data/siniestros.json` — siniestros e ítems autorizados por cada uno.
- `test_agent.py` — pruebas de la lógica determinística (`python3 test_agent.py`).

## Personalizar los datos

Para agregar más ítems o siniestros, edita directamente `data/tarifario.json` y
`data/siniestros.json` — son arrays JSON simples, no requieren ninguna base de datos externa.
