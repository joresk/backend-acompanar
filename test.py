import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Token de admin (debes obtenerlo primero con login)
headers = {
    "Authorization": "Bearer TeyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwNTJiOTM2NS04MDIyLTRlMWUtOTI3MS02NWU5ZjYyZDU4ZjUiLCJlbWFpbCI6Imp1YW5AZXhhbXBsZS5jb20iLCJpc19hbm9ueW1vdXMiOmZhbHNlLCJkZXZpY2VfaWQiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJmaXJzdF9hY2Nlc3MiOjE3MzU2ODk2MDAwMDAsImNpdHkiOiJTYW4gTWlndWVsIGRlIFR1Y3VtXHUwMGUxbiIsImNvdW50cnkiOiJBcmdlbnRpbmEiLCJsYXQiOi0yNi44MjQxLCJsb24iOi02NS4yMjI2LCJleHAiOjE3NTgwODQ5MTJ9.m4SaLvrf_qKUi1wx4JXpH5VYPntLjyKUtyZKpqs8OBY"
}

# Test: Obtener categorías
print("1. Obteniendo categorías...")
response = requests.get(f"{BASE_URL}/centros/categorias")
print(f"Status: {response.status_code}")
print(f"Categorías: {json.dumps(response.json(), indent=2)}")

# Test: Obtener centros
print("\n2. Obteniendo centros...")
response = requests.get(f"{BASE_URL}/centros")
print(f"Status: {response.status_code}")
print(f"Total centros: {response.json()['total']}")

# Test: Buscar centros cercanos (coordenadas de ejemplo)
print("\n3. Buscando centros cercanos...")
params = {
    "lat": -26.8241,  # Tucumán
    "lon": -65.2226,
    "radius": 50
}
response = requests.get(f"{BASE_URL}/centros/cercanos", params=params)
print(f"Status: {response.status_code}")
print(f"Centros encontrados: {len(response.json())}")

print("\nTodos los tests completados!")