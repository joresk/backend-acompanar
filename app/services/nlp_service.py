import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class NLPService:
    def __init__(self):
        # Cargamos un modelo multilenguaje muy ligero y rápido en memoria RAM
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        self.frases_ancla = [
            "me quiere pegar",
            "tiene un arma",
            "ayuda urgente",
            "por favor necesito ayuda me está atacando",
            "llamá a la policía",
            "emergencia inminente peligro de vida",
            "auxilio me está pegando",
            "tiene un cuchillo",
            "me amenazó de muerte"
        ]
        
        # Precomputar los embeddings de las frases ancla para máxima velocidad
        self.ancla_embeddings = self.model.encode(self.frases_ancla)
        logger.info("NLP Service inicializado con modelo MiniLM cargado.")

    def evaluar_latencia_cero(self, mensaje: str, umbral: float = 0.55) -> dict:
        """
        Evalúa si el mensaje es extremadamente similar a situaciones de peligro físico inminente.
        Devuelve dict con resultado booleano y el score.
        """
        if not mensaje or len(mensaje.strip()) == 0:
            return {"es_emergencia": False, "score": 0.0}
            
        mensaje_embedding = self.model.encode([mensaje])
        
        # Calcular similitud del mensaje contra todas las frases ancla
        similitudes = cosine_similarity(mensaje_embedding, self.ancla_embeddings)
        max_score = float(similitudes.max())
        
        logger.info(f"Latencia Cero NLP -> Mensaje: '{mensaje}', Max Score: {max_score:.3f}")
        
        return {
            "es_emergencia": max_score >= umbral,
            "score": max_score
        }

# Instancia global del servicio que se inicializa al importar
nlp_service = NLPService()
