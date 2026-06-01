import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.nlp_service import nlp_service

print(nlp_service.evaluar_latencia_cero("me quieren pegar ayuda urgente"))
print(nlp_service.evaluar_latencia_cero("ayer vi una película de terror y me dio miedo"))
print(nlp_service.evaluar_latencia_cero("auxilio tiene un cuchillo"))
