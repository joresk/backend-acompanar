import httpx
import uuid
import time
import json

WEBHOOK_URL = "https://vps-5317830-x.dattaweb.com/webhook/acompaniar"
DELAY_BETWEEN_REQUESTS = 10  # 10 segundos para no gatillar límite 429 de Mistral

def send_message(session_id, text):
    print(f"\n[>] Enviando: '{text}' (Sesión: {session_id})")
    payload = {
        "sessionId": session_id,
        "message": text,
        "lat": -26.8,
        "lon": -65.2
    }
    try:
        # Aumentamos el timeout porque Mistral puede tardar en responder
        with httpx.Client(timeout=45.0) as client:
            response = client.post(WEBHOOK_URL, json=payload)
            
        print(f"[<] Código de Estado: {response.status_code}")
        
        if response.status_code == 429:
            print("🚨 ERROR 429: ¡Rate Limit alcanzado o Tokens de Mistral agotados!")
            return False
        elif response.status_code != 200:
            print(f"🚨 ERROR: Webhook respondió con código {response.status_code}")
            print(response.text)
            return False
            
        print(f"[<] Respuesta: {response.text}")
        return True
    except httpx.ReadTimeout:
        print("🚨 TIMEOUT: El webhook o Mistral tardaron demasiado en responder.")
        return False
    except Exception as e:
        print(f"🚨 EXCEPCIÓN: {e}")
        return False

def run_tests():
    # 1. Prueba de Latencia Cero (Bypass LLM)
    session_emergencia = str(uuid.uuid4())
    print("\n--- TEST 1: Latencia Cero (Emergencia Inminente) ---")
    success = send_message(session_emergencia, "me quiere pegar y tiene un cuchillo")
    if not success: return
    
    print(f"Esperando {DELAY_BETWEEN_REQUESTS}s...")
    time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # 2. Prueba de Agente IA (RAG)
    session_normal = str(uuid.uuid4())
    print("\n--- TEST 2: Consulta RAG (Guía Legal) ---")
    success = send_message(session_normal, "¿Qué dice la ley 26485 sobre violencia patrimonial?")
    if not success: return
    
    print(f"Esperando {DELAY_BETWEEN_REQUESTS}s...")
    time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # 3. Prueba de Agente IA (Herramientas / Geolocalización)
    print("\n--- TEST 3: Búsqueda de Refugios (Tools) ---")
    success = send_message(session_normal, "Necesito refugio seguro cerca de donde estoy")
    if not success: return
    
    print(f"Esperando {DELAY_BETWEEN_REQUESTS}s...")
    time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # 4. Prueba de Evaluación Continua (Flujo)
    print("\n--- TEST 4: Prueba de Estrés para Evaluación Continua ---")
    for i in range(3):
        success = send_message(session_normal, "Dime más sobre cómo puedo protegerme.")
        if not success: 
            print("❌ Prueba abortada en paso de estrés.")
            return
        if i < 2:
            print(f"Esperando {DELAY_BETWEEN_REQUESTS}s...")
            time.sleep(DELAY_BETWEEN_REQUESTS)

    print("\n✅ Todas las pruebas finalizaron. La conexión y los tokens de Mistral parecen estables.")

if __name__ == "__main__":
    print("Iniciando Pruebas E2E contra el Webhook de n8n...")
    run_tests()
