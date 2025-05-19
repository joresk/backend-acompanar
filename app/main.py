from fastapi import FastAPI
from app.db.session import engine
from app.db.base import Base
from app.api import routes_auth, routes_users

# Importá aquí los modelos directamente (fuera del ciclo)
from app.models import user

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Acompañar API")

app.include_router(routes_auth.router, prefix="/auth", tags=["Auth"])
app.include_router(routes_users.router, prefix="/users", tags=["Users"])
