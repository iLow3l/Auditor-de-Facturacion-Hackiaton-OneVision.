import difflib
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "data", "tarifario.json"), encoding="utf-8") as f:
    TARIFARIO = json.load(f)

with open(os.path.join(BASE_DIR, "data", "siniestros.json"), encoding="utf-8") as f:
    SINIESTROS = json.load(f)

UMBRAL_SIMILITUD = 0.6


def _similitud(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _buscar_precio(item_nombre: str):
    """Busca un item en el tarifario. Usa coincidencia por substring primero
    (rapida y exacta) y si no encuentra nada, coincidencia difusa (tolera
    typos y variaciones de redaccion). Si nada supera el umbral, devuelve
    None -- eso es correcto, significa que el item de verdad no esta."""
    item_norm = (item_nombre or "").lower().strip()
    if not item_norm:
        return None

    for entry in TARIFARIO:
        entry_nombre = entry["item"].lower()
        if item_norm in entry_nombre or entry_nombre in item_norm:
            return entry

    mejor, mejor_score = None, 0.0
    for entry in TARIFARIO:
        score = _similitud(item_norm, entry["item"].lower())
        if score > mejor_score:
            mejor, mejor_score = entry, score

    return mejor if mejor_score >= UMBRAL_SIMILITUD else None


def _buscar_siniestro(numero: str):
    numero_norm = (numero or "").lower().strip()
    for s in SINIESTROS:
        if s["numero_siniestro"].lower() == numero_norm:
            return s
    return None


def _esta_autorizado(item_nombre: str, autorizados: list) -> bool:
    item_norm = (item_nombre or "").lower().strip()
    for a in autorizados:
        a_norm = a.lower().strip()
        if item_norm in a_norm or a_norm in item_norm:
            return True
        if _similitud(item_norm, a_norm) >= UMBRAL_SIMILITUD:
            return True
    return False


def auditar_factura(numero_siniestro: str, items_factura: list) -> dict:
    """Herramienta deterministica: valida una factura contra el tarifario
    acordado y los items autorizados del siniestro. Nunca lanza excepcion:
    cualquier dato faltante o mal formado se reporta como discrepancia en
    vez de romper la ejecucion."""
    try:
        siniestro = _buscar_siniestro(numero_siniestro)
    except Exception:
        siniestro = None

    if siniestro is None:
        return {
            "siniestro_encontrado": False,
            "discrepancias": [f'No se encontro un siniestro con el numero "{numero_siniestro}".'],
        }

    autorizados = siniestro["items_autorizados"]
    discrepancias = []
    vistos = {}

    if not isinstance(items_factura, list) or len(items_factura) == 0:
        return {
            "siniestro_encontrado": True,
            "taller_reportado": siniestro["taller"],
            "vehiculo": siniestro["vehiculo"],
            "items_autorizados": autorizados,
            "discrepancias": ["La factura no incluye items para revisar."],
        }

    for linea in items_factura:
        if not isinstance(linea, dict):
            discrepancias.append(f"Linea de factura con formato invalido: {linea}")
            continue

        nombre = str(linea.get("item", "")).strip()
        if not nombre:
            discrepancias.append("Se recibio una linea de factura sin nombre de item.")
            continue

        key = nombre.lower()
        vistos[key] = vistos.get(key, 0) + 1
        if vistos[key] > 1:
            discrepancias.append(f'Cobro duplicado: "{nombre}" aparece {vistos[key]} veces en la factura.')

        precio_info = _buscar_precio(nombre)
        if precio_info is None:
            discrepancias.append(f'Item no reconocido en el tarifario: "{nombre}". Requiere revision manual.')
        else:
            precio_acordado = precio_info["precio_acordado"]
            precio_cobrado_raw = linea.get("precio_unitario")
            try:
                precio_cobrado = float(precio_cobrado_raw)
            except (TypeError, ValueError):
                discrepancias.append(f'Precio unitario faltante o invalido para "{nombre}".')
                precio_cobrado = None

            if precio_cobrado is not None and precio_cobrado != float(precio_acordado):
                discrepancias.append(
                    f'Precio distinto al tarifario en "{nombre}": cobrado ${precio_cobrado}, acordado ${precio_acordado}.'
                )

        if not _esta_autorizado(nombre, autorizados):
            discrepancias.append(f'Item no autorizado para este siniestro: "{nombre}".')

    return {
        "siniestro_encontrado": True,
        "taller_reportado": siniestro["taller"],
        "vehiculo": siniestro["vehiculo"],
        "items_autorizados": autorizados,
        "discrepancias": discrepancias,
    }


SYSTEM_PROMPT = """Eres un auditor agentico de facturacion de siniestros para una aseguradora.
Recibiras un mensaje en texto libre con el numero de siniestro y el detalle de
una factura enviada por un taller (items, cantidades, precios).

Extrae esos datos y llama SIEMPRE a la herramienta auditar_factura con:
- numero_siniestro
- items_factura: lista de objetos {item, cantidad, precio_unitario}

Reglas importantes:
- Nunca inventes un precio, una autorizacion o un resultado que la herramienta
  no te haya devuelto. Si la herramienta dice que un item no fue reconocido o
  no esta autorizado, eso es informacion valida: repórtalo como discrepancia,
  no lo ignores ni lo apruebes.
- Si el mensaje del usuario no trae numero de siniestro o items claros, usa
  igual la herramienta con lo que puedas extraer; si no se puede extraer nada
  util, responde con veredicto "pendiente" explicando que faltan datos.

Con el resultado de la herramienta, redacta un veredicto final:
- "aprobado_sin_observaciones" si no hay discrepancias
- "aprobado_con_observaciones" si hay discrepancias menores (ej. un item no
  reconocido que amerita revision, pero el resto esta correcto)
- "rechazado" si el siniestro no existe, hay items no autorizados, o precios
  muy distintos a los acordados

Responde UNICAMENTE con este JSON, sin texto adicional ni markdown:
{"veredicto": "...", "discrepancias": ["..."], "resumen": "una o dos frases explicando el veredicto"}
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "auditar_factura",
            "description": (
                "Valida los items de una factura de taller contra el tarifario acordado "
                "y los items autorizados del siniestro. Devuelve discrepancias encontradas "
                "(precios distintos, items no autorizados, cobros duplicados o items desconocidos)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "numero_siniestro": {
                        "type": "string",
                        "description": "Numero del siniestro, ej. SIN-2026-045",
                    },
                    "items_factura": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item": {"type": "string"},
                                "cantidad": {"type": "number"},
                                "precio_unitario": {"type": "number"},
                            },
                            "required": ["item", "cantidad", "precio_unitario"],
                        },
                    },
                },
                "required": ["numero_siniestro", "items_factura"],
            },
        },
    }
]


def ejecutar_agente(mensaje_usuario: str, api_key: str, modelo: str = "llama-3.3-70b-versatile") -> dict:
    """Nunca lanza excepcion hacia afuera: cualquier fallo (red, parseo,
    argumentos invalidos del modelo) devuelve un resultado seguro en vez de
    romper la interfaz."""
    from groq import Groq

    try:
        client = Groq(api_key=api_key)
        mensajes = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": mensaje_usuario},
        ]

        contenido_final = None

        for _ in range(4):
            respuesta = client.chat.completions.create(
                model=modelo,
                messages=mensajes,
                tools=TOOLS,
                tool_choice="auto",
            )
            msg = respuesta.choices[0].message
            mensajes.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                contenido_final = msg.content
                break

            for tool_call in msg.tool_calls:
                if tool_call.function.name == "auditar_factura":
                    try:
                        args = json.loads(tool_call.function.arguments)
                        resultado = auditar_factura(
                            args.get("numero_siniestro", ""),
                            args.get("items_factura", []),
                        )
                    except Exception as e:
                        resultado = {
                            "siniestro_encontrado": False,
                            "discrepancias": [f"No se pudieron interpretar los datos de la factura: {e}"],
                        }
                    mensajes.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(resultado, ensure_ascii=False),
                        }
                    )

        if contenido_final is None:
            return {
                "veredicto": "pendiente",
                "discrepancias": [],
                "resumen": "El agente no pudo completar el analisis en los intentos disponibles.",
            }

        try:
            return json.loads(contenido_final)
        except (json.JSONDecodeError, TypeError):
            return {"veredicto": "pendiente", "discrepancias": [], "resumen": contenido_final}

    except Exception as e:
        return {
            "veredicto": "pendiente",
            "discrepancias": [],
            "resumen": f"Ocurrio un error tecnico al analizar la factura: {e}. Requiere revision manual.",
        }
