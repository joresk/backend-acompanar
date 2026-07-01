from fastapi import APIRouter
from app.api import (
    routes_auth,
    routes_users,
    routes_contacts,
    routes_emergency,
    routes_centros, routes_chatbot, routes_rag, routes_faq,
    routes_estadisticas
)

api_router = APIRouter()

# Incluir todos los routers
api_router.include_router(
    routes_auth.router,
    prefix="/auth",
    tags=["Autenticación"]
)

api_router.include_router(
    routes_users.router,
    prefix="/users",
    tags=["Usuarios"]
)

api_router.include_router(
    routes_contacts.router,
    prefix="/contacts",
    tags=["Contactos"]
)

api_router.include_router(
    routes_emergency.router,
    prefix="/emergency",
    tags=["Emergencias"]
)

api_router.include_router(
    routes_centros.router,
    prefix="/centros",
    tags=["Centros de Ayuda"]
)

api_router.include_router(
    routes_chatbot.router,
    prefix="/chatbot",
    tags=["Chatbot"]
)
api_router.include_router(
    routes_rag.router,
    prefix="/rag",
    tags=["RAG"]
)
api_router.include_router(
    routes_faq.router,
    prefix="/faqs",
    tags=["FAQs"]
)

api_router.include_router(
    routes_estadisticas.router,
    prefix="/estadisticas",
    tags=["Estadísticas"]
)
