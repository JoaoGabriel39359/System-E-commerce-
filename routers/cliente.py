import json
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from database import supabase, BAIRROS_ORIGINAIS

router = APIRouter(tags=["Cliente"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def get_cardapio(request: Request):
    # 1. Busca os ingredientes do banco
    res_ing = supabase.table("ingredientes").select("*").order("nome").execute()
    ingredientes_formatados = {item["nome"]: {"disponivel": item["disponivel"]} for item in res_ing.data}

    # 2. Busca as taxas dos bairros com tratamento de erro (Fallback seguro)
    try:
        res_bairros = supabase.table("bairros").select("*").order("nome").execute()
        bairros_formatados = {item["nome"]: float(item["taxa"]) for item in res_bairros.data}
        if not bairros_formatados:
            bairros_formatados = BAIRROS_ORIGINAIS
    except Exception as e:
        print(f"Aviso: Não foi possível carregar bairros do Supabase ({e}). Usando backup estático.")
        bairros_formatados = BAIRROS_ORIGINAIS

    # 3. Busca as configurações gerais da doceria
    res_conf = supabase.table("configuracoes").select("*").execute()
    config_formatada = {}
    for item in res_conf.data:
        chave = item["chave"]
        valor = item["valor"]
        if valor == "true":
            config_formatada[chave] = True
        elif valor == "false":
            config_formatada[chave] = False
        else:
            config_formatada[chave] = valor

    return templates.TemplateResponse(
        name="cardapio.html",
        context={
            "ingredientes": ingredientes_formatados,
            "bairros": bairros_formatados,
            "config": config_formatada,
            "ingredientes_json": json.dumps(ingredientes_formatados),
            "bairros_json": json.dumps(bairros_formatados)
        },
        request=request
    )