from agent import auditar_factura

print("=== Caso 1: sin discrepancias esperado ===")
r1 = auditar_factura("SIN-2026-045", [
    {"item": "Parachoques delantero", "cantidad": 1, "precio_unitario": 180},
    {"item": "Pintura y laca", "cantidad": 1, "precio_unitario": 90},
])
print(r1)
assert r1["siniestro_encontrado"] is True
assert r1["discrepancias"] == []

print("\n=== Caso 2: precio distinto esperado ===")
r2 = auditar_factura("SIN-2026-045", [
    {"item": "Parachoques delantero", "cantidad": 1, "precio_unitario": 250},
])
print(r2)
assert any("Precio distinto" in d for d in r2["discrepancias"])

print("\n=== Caso 3: cobro duplicado esperado ===")
r3 = auditar_factura("SIN-2026-045", [
    {"item": "Pintura y laca", "cantidad": 1, "precio_unitario": 90},
    {"item": "Pintura y laca", "cantidad": 1, "precio_unitario": 90},
])
print(r3)
assert any("duplicado" in d for d in r3["discrepancias"])

print("\n=== Caso 4: item no autorizado esperado ===")
r4 = auditar_factura("SIN-2026-046", [
    {"item": "Parachoques delantero", "cantidad": 1, "precio_unitario": 180},
])
print(r4)
assert any("no autorizado" in d for d in r4["discrepancias"])

print("\n=== Caso 5: siniestro inexistente esperado ===")
r5 = auditar_factura("SIN-9999", [{"item": "X", "cantidad": 1, "precio_unitario": 1}])
print(r5)
assert r5["siniestro_encontrado"] is False

print("\n✅ Los 5 casos pasaron.")
