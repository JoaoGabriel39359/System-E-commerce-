import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import cliente, admin

app = FastAPI(title="Doceria Divino Recheio")

# Monta a pasta de arquivos estáticos (essencial para carregar o JS e a Logo)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inclui os controladores de rotas modulares
app.include_router(cliente.router)
app.include_router(admin.router)