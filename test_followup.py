import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.db.session import SessionLocal
from sqlalchemy import text
from datetime import datetime

db = SessionLocal()
try:
    db.execute(text("ALTER TABLE perfiles_seguridad ADD COLUMN IF NOT EXISTS ultimo_checkin TIMESTAMP;"))
    db.commit()

    user = db.execute(text("SELECT id FROM usuarios LIMIT 1")).fetchone()
    if user:
        uid = user[0]
        db.execute(text('''
            INSERT INTO perfiles_seguridad (usuario_id, nivel_riesgo, tipo_violencia, notas_contexto, ultima_interaccion)
            VALUES (:uid, 5, 'Física', 'Test', NOW() - INTERVAL '15 minutes')
            ON CONFLICT (usuario_id) DO UPDATE SET 
            nivel_riesgo = 5,
            ultima_interaccion = NOW() - INTERVAL '15 minutes',
            ultimo_checkin = NULL;
        '''), {"uid": uid})
        db.commit()

        candidatos = db.execute(text('''
            SELECT usuario_id FROM perfiles_seguridad 
            WHERE nivel_riesgo >= 4 
            AND ultima_interaccion < NOW() - INTERVAL '10 minutes'
            AND (ultimo_checkin IS NULL OR ultimo_checkin < NOW() - INTERVAL '24 hours')
        ''')).fetchall()

        print(f"Candidatos encontrados: {len(candidatos)}")

        for cand in candidatos:
            cuid = cand[0]
            
            # Create a dummy location raw SQL
            ubicacion_id = db.execute(text('''
                INSERT INTO ubicaciones (direccion, latitud, longitud)
                VALUES ('Desconocida (Follow-up automático)', 0, 0)
                RETURNING id
            ''')).fetchone()[0]
            
            db.execute(text('''
                INSERT INTO peticiones (usuario_id, ubicacion_id, estado_code, creado_en, mensaje)
                VALUES (:uid, :loc, 'pendiente', NOW(), 'Alerta Automática: Sesión de chatbot de alto riesgo abandonada sin resolución.')
            '''), {"uid": cuid, "loc": ubicacion_id})
            
            db.execute(text('''
                UPDATE perfiles_seguridad SET ultimo_checkin = NOW() WHERE usuario_id = :uid
            '''), {"uid": cuid})

        db.commit()

        pets = db.execute(text("SELECT * FROM peticiones WHERE mensaje LIKE 'Alerta Automática%' AND usuario_id = :uid"), {"uid": uid}).fetchall()
        print(f"Peticiones de alerta generadas: {len(pets)}")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
