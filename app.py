import streamlit as st

from agent import ejecutar_agente

st.set_page_config(page_title="Auditor de Facturación de Siniestros", page_icon="🔎")

st.title("🔎 Auditor Agéntico de Facturación de Siniestros")
st.caption("Pega el número de siniestro y el detalle de la factura enviada por el taller.")

api_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
if not api_key:
    api_key = st.text_input("API key de Groq", type="password", help="Gratis en console.groq.com")

mensaje = st.text_area(
    "Mensaje",
    placeholder=(
        "Siniestro SIN-2026-045. Factura del taller: "
        "Parachoques delantero, 1 unidad, $180. Pintura y laca, 1 unidad, $90."
    ),
    height=130,
)

if st.button("Auditar factura", type="primary"):
    if not api_key:
        st.error("Falta la API key de Groq.")
    elif not mensaje.strip():
        st.error("Escribe el detalle de la factura.")
    else:
        with st.spinner("Analizando factura..."):
            try:
                resultado = ejecutar_agente(mensaje, api_key)
            except Exception as e:
                st.error(f"Error al llamar al agente: {e}")
                resultado = None

        if resultado:
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

with st.expander("Ver tarifario y siniestros de prueba"):
    import json
    st.write("**Tarifario:**")
    st.json(json.load(open("data/tarifario.json", encoding="utf-8")))
    st.write("**Siniestros:**")
    st.json(json.load(open("data/siniestros.json", encoding="utf-8")))
