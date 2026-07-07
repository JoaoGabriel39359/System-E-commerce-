from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Importamos o cliente do supabase e a lista fixa de bairros do seu database.py
from database import supabase, bairros_db

router = APIRouter(tags=["Cliente"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def get_cardapio(request: Request):
    # 1. Busca os ingredientes do banco dentro do esquema 'delivery' (Ordem corrigida)
    res_ing = supabase.table("ingredientes").select("*").order("nome").execute()
    ingredientes_formatados = {item["nome"]: {"disponivel": item["disponivel"]} for item in res_ing.data}

    # 2. Busca as configurações gerais da doceria (WhatsApp, Nutella, Loja Aberta)
    res_conf = supabase.table("configuracoes").select("*").execute()
    config_formatada = {}
    for item in res_conf.data:
        chave = item["chave"]
        valor = item["valor"]
        # Converte as strings "true"/"false" do banco em Booleanos reais
        if valor == "true":
            config_formatada[chave] = True
        elif valor == "false":
            config_formatada[chave] = False
        else:
            config_formatada[chave] = valor

    # 3. Renderiza o cardápio passando os dados atualizados em tempo real do banco
    return templates.TemplateResponse(
        name="cardapio.html",
        context={
            "ingredientes": ingredientes_formatados,
            "bairros": bairros_db,
            "config": config_formatada
        },
        request=request
    )