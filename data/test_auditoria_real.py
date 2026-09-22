from agent import auditar_factura

print("=== Caso H: precio con variacion pequena (dentro de tolerancia, NO debe marcar) ===")
r = auditar_factura("SIN-2026-045", [
    {"item": "Parachoques delantero", "cantidad": 1, "precio_unitario": 185},  # 2.7% mas, tolerancia 5%
])
print(r["discrepancias"])
assert not any("Precio distinto" in d for d in r["discrepancias"]), "No deberia marcar, esta dentro de tolerancia"

print("\n=== Caso I: precio fuera de tolerancia (SI debe marcar) ===")
r = auditar_factura("SIN-2026-045", [
    {"item": "Parachoques delantero", "cantidad": 1, "precio_unitario": 220},  # 22% mas
])
print(r["discrepancias"])
assert any("Precio distinto" in d for d in r["discrepancias"])

print("\n=== Caso J: cantidad sospechosa en pieza fisica ===")
r = auditar_factura("SIN-2026-045", [
    {"item": "Parachoques delantero", "cantidad": 6, "precio_unitario": 180},
])
print(r["discrepancias"])
assert any("Cantidad inusualmente alta" in d for d in r["discrepancias"])

print("\n=== Caso K: mano de obra con muchas horas NO debe marcarse por cantidad ===")
r = auditar_factura("SIN-2026-045", [
    {"item": "Mano de obra pintura", "cantidad": 8, "precio_unitario": 25},
])
print(r["discrepancias"])
assert not any("Cantidad inusualmente alta" in d for d in r["discrepancias"])

print("\n=== Caso L: total declarado no cuadra con la suma de items ===")
r = auditar_factura("SIN-2026-045", [
    {"item": "Parachoques delantero", "cantidad": 1, "precio_unitario": 180},
    {"item": "Pintura y laca", "cantidad": 1, "precio_unitario": 90},
], total_declarado=500)  # deberia ser ~270, no 500
print(r["discrepancias"], "subtotal_calculado:", r["subtotal_calculado"])
assert any("total declarado" in d for d in r["discrepancias"])

print("\n=== Caso M: total declarado SI cuadra (con margen de ITBMS) ===")
r = auditar_factura("SIN-2026-045", [
    {"item": "Parachoques delantero", "cantidad": 1, "precio_unitario": 180},
    {"item": "Pintura y laca", "cantidad": 1, "precio_unitario": 90},
], total_declarado=289)  # 270 + 7% ITBMS = 288.9
print(r["discrepancias"], "subtotal_calculado:", r["subtotal_calculado"])
assert not any("total declarado" in d for d in r["discrepancias"])

print("\n✅ Todos los casos de auditoria real pasaron.")
