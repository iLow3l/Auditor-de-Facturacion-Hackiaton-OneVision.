import difflib
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "data", "tarifario.json"), encoding="utf-8") as f:
    TARIFARIO = json.load(f)

with open(os.path.join(BASE_DIR, "data", "siniestros.json"), encoding="utf-8") as f:
    SINIESTROS = json.load(f)

UMBRAL_SIMILITUD = 0.6
TOLERANCIA_PRECIO = 0.05  # 5% -- redondeos y variaciones normales no son fraude
CANTIDAD_SOSPECHOSA = 4   # mas de esto en una pieza fisica amerita revisar


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


def _sugerir_similar(item_nombre: str):
    """Devuelve el item del tarifario mas parecido aunque no supere el umbral
    de confianza, para dar una pista util al auditor humano (ej. 'quisiste
    decir X?'). No se usa para aprobar nada, solo como sugerencia."""
    item_norm = (item_nombre or "").lower().strip()
    mejor, mejor_score = None, 0.0
    for entry in TARIFARIO:
        score = _similitud(item_norm, entry["item"].lower())
        if score > mejor_score:
            mejor, mejor_score = entry, score
    if mejor and 0.3 <= mejor_score < UMBRAL_SIMILITUD:
        return mejor["item"]
    return None


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


def auditar_factura(numero_siniestro: str, items_factura: list, total_declarado: float = None) -> dict:
    """Herramienta deterministica: valida una factura contra el tarifario
    acordado y los items autorizados del siniestro. Nunca lanza excepcion:
    cualquier dato faltante o mal formado se reporta como discrepancia en
    vez de romper la ejecucion.

    total_declarado: opcional -- si el usuario menciona el total de la
    factura, se compara contra la suma calculada de cantidad x precio.
    """
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
    subtotal_calculado = 0.0

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

        try:
            cantidad = float(linea.get("cantidad", 1))
        except (TypeError, ValueError):
            cantidad = 1.0

        if cantidad > CANTIDAD_SOSPECHOSA and "mano de obra" not in key:
            discrepancias.append(
                f'Cantidad inusualmente alta para "{nombre}": {cantidad} unidades. Requiere verificacion.'
            )

        precio_info = _buscar_precio(nombre)
        if precio_info is None:
            sugerencia = _sugerir_similar(nombre)
            if sugerencia:
                discrepancias.append(
                    f'Item no reconocido en el tarifario: "{nombre}". ¿Sera "{sugerencia}"? Requiere revision manual.'
                )
            else:
                discrepancias.append(f'Item no reconocido en el tarifario: "{nombre}". Requiere revision manual.')
        else:
            precio_acordado = float(precio_info["precio_acordado"])
            precio_cobrado_raw = linea.get("precio_unitario")
            try:
                precio_cobrado = float(precio_cobrado_raw)
            except (TypeError, ValueError):
                discrepancias.append(f'Precio unitario faltante o invalido para "{nombre}".')
                precio_cobrado = None

            if precio_cobrado is not None:
                subtotal_calculado += cantidad * precio_cobrado
                diferencia_relativa = abs(precio_cobrado - precio_acordado) / precio_acordado if precio_acordado else 1
                if diferencia_relativa > TOLERANCIA_PRECIO:
                    discrepancias.append(
                        f'Precio distinto al tarifario en "{nombre}": cobrado ${precio_cobrado:.2f}, '
                        f'acordado ${precio_acordado:.2f} (diferencia de {diferencia_relativa * 100:.0f}%, '
                        f'tolerancia permitida {TOLERANCIA_PRECIO * 100:.0f}%).'
                    )

        if not _esta_autorizado(nombre, autorizados):
            discrepancias.append(f'Item no autorizado para este siniestro: "{nombre}".')

    if total_declarado is not None:
        try:
            total_declarado = float(total_declarado)
            diferencia_total = abs(total_declarado - subtotal_calculado)
            tolerancia_total = subtotal_calculado * 0.08 + 0.5  # deja margen para ITBMS/redondeo
            if diferencia_total > tolerancia_total:
                discrepancias.append(
                    f'El total declarado en la factura (${total_declarado:.2f}) no coincide con la suma '
                    f'de cantidad x precio de los items (${subtotal_calculado:.2f}). Verificar calculo o impuestos.'
                )
        except (TypeError, ValueError):
            pass

    return {
        "siniestro_encontrado": True,
        "taller_reportado": siniestro["taller"],
        "vehiculo": siniestro["vehiculo"],
        "items_autorizados": autorizados,
        "subtotal_calculado": round(subtotal_calculado, 2),
        "discrepancias": discrepancias,
    }


SYSTEM_PROMPT = """Eres un auditor agentico de facturacion de siniestros para una aseguradora.
Recibiras un mensaje en texto libre con el numero de siniestro y el detalle de
una factura enviada por un taller (items, cantidades, precios, y a veces un total).

Extrae esos datos y llama SIEMPRE a la herramienta auditar_factura con:
- numero_siniestro
- items_factura: lista de objetos {item, cantidad, precio_unitario}
- total_declarado: si el mensaje menciona un total de factura, inclúyelo; si no, omitelo

Reglas importantes:
- Nunca inventes un precio, una autorizacion o un resultado que la herramienta
  no te haya devuelto. Si la herramienta dice que un item no fue reconocido o
  no esta autorizado, eso es informacion valida: repórtalo como discrepancia,
  no lo ignores ni lo apruebes.
- La herramienta ya aplica una tolerancia razonable de precio (variaciones
  pequeñas por redondeo o impuestos no se marcan como discrepancia). Confia
  en su criterio, no relajes ni endurezcas tu propio juicio sobre los precios.
- Si el mensaje del usuario no trae numero de siniestro o items claros, usa
  igual la herramienta con lo que puedas extraer; si no se puede extraer nada
  util, responde con veredicto "pendiente" explicando que faltan datos.
- Si hay memoria de auditorias previas en esta conversacion, puedes usarla
  para responder preguntas de seguimiento sin volver a llamar la herramienta.

Con el resultado de la herramienta, redacta un veredicto final:
- "aprobado_sin_observaciones" si no hay discrepancias
- "aprobado_con_observaciones" si hay discrepancias menores (ej. un item no
  reconocido que amerita revision, pero el resto esta correcto)
- "rechazado" si el siniestro no existe, hay items no autorizados, precios
  fuera de tolerancia, o el total declarado no cuadra con los items

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
                    "total_declarado": {
                        "type": "number",
                        "description": "Total de la factura si el mensaje lo menciona explicitamente. Omitir si no se menciona.",
                    },
                },
                "required": ["numero_siniestro", "items_factura"],
            },
        },
    }
]


def ejecutar_agente(mensaje_usuario: str, api_key: str, historial: list = None, modelo: str = "openai/gpt-oss-120b"):
    """Nunca lanza excepcion hacia afuera: cualquier fallo (red, parseo,
    argumentos invalidos del modelo) devuelve un resultado seguro en vez de
    romper la interfaz.

    historial: lista opcional de mensajes previos (formato OpenAI/Groq) para
    dar memoria conversacional -- si se pasa, el agente recuerda auditorias
    anteriores de la misma sesion. Devuelve (resultado_dict, historial_actualizado).
    """
    from groq import Groq

    try:
        client = Groq(api_key=api_key)
        mensajes = list(historial) if historial else [{"role": "system", "content": SYSTEM_PROMPT}]
        mensajes.append({"role": "user", "content": mensaje_usuario})

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
                            args.get("total_declarado"),
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
            return (
                {
                    "veredicto": "pendiente",
                    "discrepancias": [],
                    "resumen": "El agente no pudo completar el analisis en los intentos disponibles.",
                },
                mensajes,
            )

        try:
            return json.loads(contenido_final), mensajes
        except (json.JSONDecodeError, TypeError):
            return {"veredicto": "pendiente", "discrepancias": [], "resumen": contenido_final}, mensajes

    except Exception as e:
        return (
            {
                "veredicto": "pendiente",
                "discrepancias": [],
                "resumen": f"Ocurrio un error tecnico al analizar la factura: {e}. Requiere revision manual.",
            },
            historial or [],
        )
