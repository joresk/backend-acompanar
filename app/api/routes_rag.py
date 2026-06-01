from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from app.db.session import get_db
from groq import Groq
import os

router = APIRouter()

class IngestarRequest(BaseModel):
    chunks: list[str]
    source: str = "Google Doc"

class ConsultarRequest(BaseModel):
    query: str

@router.post("/ingestar")
def ingestar_datos(payload: IngestarRequest, db: Session = Depends(get_db)):
    # 1. Limpiar chunks anteriores de la misma fuente
    db.execute(text("DELETE FROM rag_chunks WHERE source = :source"), {"source": payload.source})
    
    # 2. Insertar nuevos chunks
    for chunk in payload.chunks:
        db.execute(
            text("INSERT INTO rag_chunks (content, source) VALUES (:content, :source)"),
            {"content": chunk, "source": payload.source}
        )
    db.commit()
    return {"success": True, "inserted": len(payload.chunks)}

@router.post("/consultar")
def consultar_rag(payload: ConsultarRequest, db: Session = Depends(get_db)):
    query_text = payload.query.strip()
    
    # 1. Buscar chunks relevantes usando FTS de PostgreSQL en español
    result = db.execute(text("""
        SELECT content FROM rag_chunks
        WHERE to_tsvector('spanish', content) @@ plainto_tsquery('spanish', :query)
        LIMIT 3
    """), {"query": query_text}).fetchall()
    
    chunks = [row[0] for row in result]
    
    # Fallback: si FTS no devolvió nada, buscar con ILIKE por cada palabra clave larga
    if not chunks:
        words = [w for w in query_text.split() if len(w) > 4]
        if words:
            like_clauses = " OR ".join([f"content ILIKE :w{i}" for i in range(len(words))])
            params = {f"w{i}": f"%{word}%" for i, word in enumerate(words)}
            result = db.execute(text(f"""
                SELECT content FROM rag_chunks
                WHERE {like_clauses}
                LIMIT 3
            """), params).fetchall()
            chunks = [row[0] for row in result]
            
    # Fallback 2: si aún no hay contexto, buscar los primeros 3 chunks
    if not chunks:
        result = db.execute(text("SELECT content FROM rag_chunks LIMIT 3")).fetchall()
        chunks = [row[0] for row in result]
        
    context = "\n---\n".join(chunks)
    
    # 2. Consultar a Groq con el contexto recuperado
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {
            "query": payload.query,
            "respuesta": "Lo siento, la clave de API del chatbot no está configurada.",
            "context_used": False
        }
        
    client = Groq(api_key=api_key)
    
    system_prompt = """
    Eres 'Acompañar', un asistente virtual empático, seguro y comprensivo para mujeres que sufren violencia de género en Tucumán.
    
    Usa el siguiente contexto de la 'Guía de Bolsillo' para responder a la pregunta de la usuaria de manera precisa y empática:
    {context}
    
    REGLAS IMPORTANTES:
    1. Responde de forma muy humana, cálida y sin juzgar.
    2. Si la información proporcionada en el contexto no contiene la respuesta a la pregunta, di amablemente que no posees ese dato exacto, pero facilítale el contacto general de ayuda: llamar a la Línea 144 (atención 24hs nacional) o acudir a la Secretaría de la Mujer de Tucumán.
    3. NUNCA inventes números de teléfono, direcciones ni nombres de leyes que no estén explícitamente en el contexto.
    """.format(context=context if context else "No hay información disponible.")
    
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload.query}
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.3
    )
    
    respuesta = chat_completion.choices[0].message.content
    
    return {
        "query": payload.query,
        "respuesta": respuesta,
        "context_used": bool(context)
    }
