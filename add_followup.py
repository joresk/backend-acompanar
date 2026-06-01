import sys

file_path = "f:/0- Acompañar/Acompaniar-bf/backend-acompanar/app/api/routes_chatbot.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add endpoint at the end if not exists
if "/trigger-followup" not in content:
    endpoint_code = """
@router.post("/trigger-followup")
def trigger_followup(db: Session = Depends(get_db)):
    try:
        # Asegurarnos de que exista la columna ultimo_checkin en perfiles_seguridad
        db.execute(text("ALTER TABLE perfiles_seguridad ADD COLUMN IF NOT EXISTS ultimo_checkin TIMESTAMP;"))
        db.commit()
        
        # Buscar usuarios con riesgo >= 4, inactivos por más de 10 mins, y que no hayan recibido checkin en las ultimas 24 hs.
        query = text(\"\"\"
            SELECT usuario_id FROM perfiles_seguridad 
            WHERE nivel_riesgo >= 4 
            AND ultima_interaccion < NOW() - INTERVAL '10 minutes'
            AND (ultimo_checkin IS NULL OR ultimo_checkin < NOW() - INTERVAL '24 hours')
        \"\"\")
        
        candidatos = db.execute(query).fetchall()
        alertas_creadas = 0
        
        for cand in candidatos:
            uid = cand[0]
            
            # Crear peticion (Alerta para el Operador)
            insert_peticion = text(\"\"\"
                INSERT INTO peticiones (usuario_id, estado_code, mensaje, creado_en)
                VALUES (:uid, 'pendiente', 'Alerta Automática: Sesión de chatbot de alto riesgo abandonada sin resolución.', NOW())
            \"\"\")
            db.execute(insert_peticion, {"uid": uid})
            
            # Actualizar ultimo_checkin
            update_perfil = text(\"\"\"
                UPDATE perfiles_seguridad SET ultimo_checkin = NOW() WHERE usuario_id = :uid
            \"\"\")
            db.execute(update_perfil, {"uid": uid})
            
            alertas_creadas += 1
            
        db.commit()
        return {"success": True, "alertas_creadas": alertas_creadas}
    except Exception as e:
        db.rollback()
        logger.error(f"Error en trigger_followup: {e}")
        return {"success": False, "error": str(e)}
"""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(endpoint_code)
    print("Endpoint /trigger-followup added successfully.")
else:
    print("Endpoint /trigger-followup already exists.")
