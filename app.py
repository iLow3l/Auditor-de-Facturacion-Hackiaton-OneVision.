import csv
import io
import json

import streamlit as st

from agent import ejecutar_agente

st.set_page_config(page_title="Auditor de Facturación de Siniestros", page_icon="🔎")

st.title("🔎 Auditor Agéntico de Facturación de Siniestros")
st.caption("Pega el número de siniestro y el detalle de la factura enviada por el taller.")

if "historial_chat" not in st.session_state:
    st.session_state.historial_chat = None  # memoria del agente (formato Groq)
if "historial_auditorias" not in st.session_state:
    st.session_state.historial_auditorias = []  # para la tabla y el CSV

api_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
if not api_key:
    st.error(
        "Esta app no tiene configurada la API key de Groq. "
        "El propietario debe agregarla en Settings → Secrets de Streamlit Cloud "
        "como GROQ_API_KEY = \"...\"."
    )
    st.stop()

mensaje = st.text_area(
    "Mensaje",
    placeholder=(
        "Siniestro SIN-2026-045. Factura del taller: "
        "Parachoques delantero, 1 unidad, $180. Pintura y laca, 1 unidad, $90."
    ),
    height=130,
)

col1, col2 = st.columns([1, 1])
with col1:
    auditar = st.button("Auditar factura", type="primary")
with col2:
    if st.button("Nueva conversación (borrar memoria)"):
        st.session_state.historial_chat = None
        st.rerun()

if auditar:
    if not mensaje.strip():
        st.error("Escribe el detalle de la factura.")
    else:
        with st.spinner("Analizando factura..."):
            resultado, nuevo_historial = ejecutar_agente(
                mensaje, api_key, historial=st.session_state.historial_chat
            )
            st.session_state.historial_chat = nuevo_historial

        veredicto = resultado.get("veredicto", "pendiente")
        colores = {
            "aprobado_sin_observaciones": "green",
            "aprobado_con_observaciones": "orange",
            "rechazado": "red",
        }
        color = colores.get(veredicto, "gray")

        st.markdown(f"### Veredicto: :{color}[{veredicto}]")
        st.write(resultado.get("resumen", ""))

        discrepancias = resultado.get("discrepancias", [])
        if discrepancias:
            st.markdown("**Discrepancias encontradas:**")
            for d in discrepancias:
                st.write(f"- {d}")
        else:
            st.success("Sin discrepancias detectadas.")

        st.session_state.historial_auditorias.append(
            {
                "mensaje": mensaje.strip().replace("\n", " "),
                "veredicto": veredicto,
                "discrepancias": " | ".join(discrepancias) if discrepancias else "Ninguna",
            }
        )

if st.session_state.historial_chat:
    st.caption("💬 El agente recuerda las auditorías de esta sesión — puedes hacer preguntas de seguimiento arriba.")

if st.session_state.historial_auditorias:
    st.markdown("---")
    st.subheader("Historial de auditorías en esta sesión")
    st.table(st.session_state.historial_auditorias)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["mensaje", "veredicto", "discrepancias"])
    writer.writeheader()
    writer.writerows(st.session_state.historial_auditorias)

    st.download_button(
        "Descargar historial (CSV)",
        data=buffer.getvalue(),
        file_name="historial_auditorias.csv",
        mime="text/csv",
    )

with st.expander("Ver tarifario y siniestros de prueba"):
    st.write("**Tarifario:**")
    st.json(json.load(open("data/tarifario.json", encoding="utf-8")))
    st.write("**Siniestros:**")
    st.json(json.load(open("data/siniestros.json", encoding="utf-8")))
