from agent import auditar_factura

print("=== Caso A: mismo item, mayusculas/minusculas distintas ===")
r = auditar_factura("SIN-2026-045", [
    {"item": "PARACHOQUES DELANTERO", "cantidad": 1, "precio_unitario": 180},
])
print(r["discrepancias"])
assert r["discrepancias"] == [], "Deberia reconocerlo pese al cambio de mayusculas"

print("\n=== Caso B: item con typo leve ===")
r = auditar_factura("SIN-2026-045", [
    {"item": "Parachoque delantero", "cantidad": 1, "precio_unitario": 180},  # falta la 's'
])
print(r["discrepancias"])
assert r["discrepancias"] == [], "Deberia tolerar el typo leve"

print("\n=== Caso C: item totalmente inventado (no debe inventar precio) ===")
r = auditar_factura("SIN-2026-045", [
    {"item": "Motor nuevo completo", "cantidad": 1, "precio_unitario": 5000},
])
print(r["discrepancias"])
assert any("no reconocido" in d for d in r["discrepancias"]), "Debe marcarlo como no reconocido, no aprobarlo"

print("\n=== Caso D: falta el precio_unitario ===")
r = auditar_factura("SIN-2026-045", [
    {"item": "Parachoques delantero", "cantidad": 1},
])
print(r["discrepancias"])
assert any("faltante" in d or "invalido" in d for d in r["discrepancias"])

print("\n=== Caso E: factura vacia ===")
r = auditar_factura("SIN-2026-045", [])
print(r["discrepancias"])
assert r["discrepancias"] != []

print("\n=== Caso F: linea con formato invalido (no es un dict) ===")
r = auditar_factura("SIN-2026-045", ["esto no es un item valido"])
print(r["discrepancias"])
assert r["discrepancias"] != []

print("\n=== Caso G: numero de siniestro con espacios/case distinto ===")
r = auditar_factura("  sin-2026-045  ", [
    {"item": "Parachoques delantero", "cantidad": 1, "precio_unitario": 180},
])
print("siniestro_encontrado:", r["siniestro_encontrado"])
assert r["siniestro_encontrado"] is True

print("\n✅ Todos los casos de robustez pasaron.")
