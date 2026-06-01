import pytest
from app.models.user import User
import uuid

# Generamos UUIDs
USER_ID = str(uuid.uuid4())

def setup_user(db_session):
    user = User(id=uuid.UUID(USER_ID), full_name="Usuaria Test")
    db_session.add(user)
    db_session.commit()

def test_obtener_perfil_vacio(client, db_session):
    setup_user(db_session)
    response = client.get(f"/api/v1/chatbot/perfil/{USER_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["notas_contexto"] == "Ninguno"
    assert data["nivel_riesgo"] == 1

def test_actualizar_perfil_concatenacion(client, db_session):
    setup_user(db_session)
    
    # Primera actualización
    payload1 = {
        "id_sesion": USER_ID,
        "notas_contexto": "Usuaria reporta discusiones frecuentes.",
        "nivel_riesgo": 2,
        "tipo_violencia": "Psicológica"
    }
    resp1 = client.post("/api/v1/chatbot/perfil/actualizar", json=payload1)
    assert resp1.status_code == 200
    
    # Segunda actualización (debería concatenarse)
    payload2 = {
        "id_sesion": USER_ID,
        "notas_contexto": "Hoy la amenazó verbalmente.",
        "nivel_riesgo": 3,
        "tipo_violencia": "Psicológica"
    }
    resp2 = client.post("/api/v1/chatbot/perfil/actualizar", json=payload2)
    assert resp2.status_code == 200
    
    # Verificar la base de datos a través de la API
    resp_get = client.get(f"/api/v1/chatbot/perfil/{USER_ID}")
    data = resp_get.json()
    assert data["nivel_riesgo"] == 3
    assert "Usuaria reporta discusiones frecuentes." in data["notas_contexto"]
    assert "Hoy la amenazó verbalmente." in data["notas_contexto"]
    assert "\\n---\\n" in data["notas_contexto"] or "\n---\n" in data["notas_contexto"]

def test_evaluar_test_deteccion_critico(client, db_session):
    setup_user(db_session)
    
    payload = {
        "id_sesion": USER_ID,
        "nivel_riesgo": 5,
        "tipo_violencia": "Física y Psicológica"
    }
    
    response = client.post("/api/v1/chatbot/evaluar", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["nivel_riesgo"] == 5
    assert "911" in data["recomendaciones"] or "OVD" in data["recomendaciones"]
    
    # Validar persistencia
    resp_get = client.get(f"/api/v1/chatbot/perfil/{USER_ID}")
    assert resp_get.json()["nivel_riesgo"] == 5
