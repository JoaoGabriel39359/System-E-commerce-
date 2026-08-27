import os
import uuid
import json
import time
import hmac
import hashlib
import asyncio
import urllib.parse
from datetime import datetime
from collections import defaultdict
from fastapi import APIRouter, Request, Form, Cookie, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from schemas.pedido import PedidoCreate
from database import supabase, BAIRROS_ORIGINAIS

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")

ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASS")
SECRET_KEY = os.getenv("SECRET_KEY", "divino_recheio_secret_key_2026")

# --- DICA 1: GERADOR E VALIDADOR DE SESSÃO SEGURA (HMAC) ---
def gerar_token_admin() -> str:
    user = ADMIN_USER or "admin"
    return hmac.new(SECRET_KEY.encode(), user.encode(), hashlib.sha256).hexdigest()

def validar_sessao_admin(session_cookie: str) -> bool:
    if not session_cookie:
        return False
    expected_token = gerar_token_admin()
    # Aceita token HMAC assinado ou o legado 'autenticado_divino' para retrocompatibilidade
    return hmac.compare_digest(session_cookie, expected_token) or session_cookie == "autenticado_divino"

# --- DICA 3: RATE LIMITER LEVE POR IP (PROTEÇÃO CONTRA DDoS / SPAM) ---
class SimpleRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def check(self, request: Request):
        x_forwarded = request.headers.get("x-forwarded-for")
        if x_forwarded:
            client_ip = x_forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        now = time.time()
        # Filtra registros dentro da janela de tempo
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window_seconds]
        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Muitas requisições. Por favor, aguarde um instante.")
        self.requests[client_ip].append(now)

rate_limiter_geral = SimpleRateLimiter(max_requests=600, window_seconds=60)
rate_limiter_login = SimpleRateLimiter(max_requests=20, window_seconds=60)

@router.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request, erro: str = None):
    return templates.TemplateResponse(
        request=request,
        name="login.html", 
        context={"request": request, "erro": erro}
    )

# --- ROTA: PROCESSA O LOGIN (POST) ---
@router.post("/login")
async def post_login(request: Request, username: str = Form(...), password: str = Form(...)):
    rate_limiter_login.check(request)
    if username == ADMIN_USER and password == ADMIN_PASS:
        resposta = RedirectResponse(url="/admin", status_code=303)
        resposta.set_cookie(
            key="admin_session", 
            value=gerar_token_admin(), 
            httponly=True,
            samesite="lax"
        )
        return resposta
    else:
        return RedirectResponse(url="/admin/login?erro=Usu%C3%A1rio%20ou%20senha%20inv%C3%A1lidos.", status_code=303)

# --- ROTA: LOGOUT ---
@router.get("/logout")
async def get_logout():
    resposta = RedirectResponse(url="/admin/login", status_code=303)
    resposta.delete_cookie(key="admin_session")
    return resposta

@router.get("", response_class=HTMLResponse)
async def get_admin(request: Request, admin_session: str = Cookie(default=None)):
    if not validar_sessao_admin(admin_session):
        return RedirectResponse(url="/admin/login", status_code=303)

    # 1. Ingredientes
    res_ing = supabase.table("ingredientes").select("*").order("nome").execute()
    ingredientes_formatados = {item["nome"]: {"disponivel": item["disponivel"]} for item in res_ing.data}

    # 2. Configurações
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

    # 3. Bairros (Buscando direto do Supabase)
    res_bairros = supabase.table("bairros").select("*").order("nome").execute()
    bairros_formatados = {item["nome"]: float(item["taxa"]) for item in res_bairros.data}
    if not bairros_formatados:
        bairros_formatados = BAIRROS_ORIGINAIS

    # 4. Pedidos
    res_pedidos = supabase.table("pedidos").select("*").execute()
    pedidos_formatados = []
    for pedido in res_pedidos.data:
        novo_pedido = dict(pedido)
        try:
            dt = datetime.fromisoformat(pedido["criado_em"].replace("Z", "+00:00"))
            novo_pedido["criado_em"] = dt.strftime("%d/%m %H:%M")
        except Exception:
            pass 
        pedidos_formatados.append(novo_pedido)

    return templates.TemplateResponse(
        name="admin.html",
        context={
            "ingredientes": ingredientes_formatados,
            "bairros": bairros_formatados,
            "config": config_formatada,
            "pedidos": pedidos_formatados
        },
        request=request
    )

@router.get("/api/status-loja")
async def get_status_loja(request: Request = None):
    if request:
        rate_limiter_geral.check(request)

    res_conf = supabase.table("configuracoes").select("*").execute()
    config = {item["chave"]: item["valor"] for item in res_conf.data}

    res_ing = supabase.table("ingredientes").select("*").order("nome").execute()
    ingredientes_formatados = {item["nome"]: {"disponivel": item["disponivel"]} for item in res_ing.data}
    lista_ingredientes = [item["nome"] for item in res_ing.data if item["disponivel"]]

    try:
        res_bairros = supabase.table("bairros").select("*").order("nome").execute()
        bairros_formatados = {item["nome"]: float(item["taxa"]) for item in res_bairros.data}
        if not bairros_formatados:
            bairros_formatados = BAIRROS_ORIGINAIS
    except Exception:
        bairros_formatados = BAIRROS_ORIGINAIS

    return {
        "loja_aberta": config.get("loja_aberta") == "true",
        "nutella_gratis": config.get("nutella_gratis") == "true",
        "ingredientes_disponiveis": lista_ingredientes,
        "ingredientes": ingredientes_formatados,
        "bairros": bairros_formatados
    }

# --- DICA 5: ENDPOINT STREAMING SSE PARA TEMPO REAL INSTANTÂNEO ---
@router.get("/api/status-stream")
async def get_status_stream(request: Request):
    rate_limiter_geral.check(request)

    async def event_generator():
        ultimo_estado = None
        while True:
            if await request.is_disconnected():
                break
            try:
                dados = await get_status_loja()
                estado_json = json.dumps(dados)
                if estado_json != ultimo_estado:
                    ultimo_estado = estado_json
                    yield f"data: {estado_json}\n\n"
            except Exception as e:
                print(f"Aviso SSE status-stream: {e}")
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- NOVO ENDPOINT LEVE PARA POLLING ---
@router.get("/api/pedidos/contagem")
async def get_contagem_pedidos():
    """Endpoint otimizado para o polling de 10s do JS sem carregar a página toda."""
    res = supabase.table("pedidos").select("id").not_.in_("status", ["Concluído", "Cancelado"]).execute()
    return {"total_ativos": len(res.data)}

@router.post("/salvar")
async def post_salvar(request: Request, admin_session: str = Cookie(default=None)):
    if not validar_sessao_admin(admin_session):
        return RedirectResponse(url="/admin/login", status_code=303)

    form_data = await request.form()

    # 1. Ingredientes — busca IDs e salva tudo em 1 upsert em lote
    res_ing = supabase.table("ingredientes").select("id, nome").execute()
    if res_ing.data:
        payload_ing = [
            {"id": item["id"], "nome": item["nome"], "disponivel": f"ingrediente_{item['nome']}" in form_data}
            for item in res_ing.data
        ]
        supabase.table("ingredientes").upsert(payload_ing).execute()

    # 2. Configurações (loja, nutella, whatsapp) — 1 upsert único
    loja_status    = "true" if "loja_aberta"    in form_data else "false"
    nutella_status = "true" if "nutella_gratis" in form_data else "false"

    configs_payload = [
        {"chave": "loja_aberta",    "valor": loja_status},
        {"chave": "nutella_gratis", "valor": nutella_status},
    ]

    if "whatsapp_vendedor" in form_data:
        raw_phone = form_data["whatsapp_vendedor"]
        digits = "".join([c for c in raw_phone if c.isdigit()])
        if len(digits) in [10, 11] and not digits.startswith("55"):
            digits = "55" + digits
        configs_payload.append({"chave": "whatsapp_vendedor", "valor": digits})

    supabase.table("configuracoes").upsert(configs_payload, on_conflict="chave").execute()

    # 3. Bairros — busca nome/taxa e salva alterados em 1 upsert em lote (PK = nome)
    res_bairros = supabase.table("bairros").select("nome, taxa").execute()
    if res_bairros.data:
        payload_bairros = []
        for item in res_bairros.data:
            campo = f"taxa_{item['nome']}"
            if campo in form_data:
                try:
                    payload_bairros.append({"nome": item["nome"], "taxa": float(form_data[campo])})
                except ValueError:
                    pass
        if payload_bairros:
            supabase.table("bairros").upsert(payload_bairros, on_conflict="nome").execute()

    resposta = RedirectResponse(url="/admin", status_code=303)
    resposta.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resposta.headers["Pragma"] = "no-cache"
    resposta.headers["Expires"] = "0"
    return resposta

@router.post("/novo-ingrediente")
async def post_novo_ingrediente(novo_nome: str = Form(...)):
    nome_limpo = novo_nome.strip()
    if nome_limpo:
        try:
            supabase.table("ingredientes").insert({"nome": nome_limpo, "disponivel": True}).execute()
        except Exception:
            pass 
            
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/pedidos/novo")
async def post_novo_pedido(pedido_in: PedidoCreate):
    pedido_id = str(uuid.uuid4())[:8].upper()
    criado_em = datetime.now().isoformat()
    
    raw_phone = pedido_in.telefone
    digits = "".join([c for c in raw_phone if c.isdigit()])
    if len(digits) in [10, 11] and not digits.startswith("55"):
        digits = "55" + digits
    
    pedido = {
        "id": pedido_id,
        "nome": pedido_in.nome,
        "telefone": digits,
        "endereco": pedido_in.endereco,
        "bairro": pedido_in.bairro,
        "tamanho": pedido_in.tamanho,
        "recheios": pedido_in.recheios, 
        "adicional_nutella": float(pedido_in.adicional_nutella),
        "forma_pagamento": pedido_in.forma_pagamento,
        "taxa_entrega": float(pedido_in.taxa_entrega),
        "total": float(pedido_in.total),
        "status": "Pendente",
        "criado_em": criado_em
    }
    
    supabase.table("pedidos").insert(pedido).execute()
    return {"status": "sucesso", "pedido_id": pedido_id}

@router.post("/pedidos/atualizar")
async def post_atualizar_pedido(pedido_id: str = Form(...), novo_status: str = Form(...)):
    res_pedido = supabase.table("pedidos").select("*").eq("id", pedido_id).execute()
    if not res_pedido.data:
        return RedirectResponse(url="/admin", status_code=303)
        
    pedido_encontrado = res_pedido.data[0]

    if novo_status in ["Concluído", "Cancelado"]:
        supabase.table("pedidos").delete().eq("id", pedido_id).execute()
        return RedirectResponse(url="/admin", status_code=303)

    supabase.table("pedidos").update({"status": novo_status}).eq("id", pedido_id).execute()
            
    if novo_status in ["Em preparo", "Saiu para entrega"]:
        if novo_status == "Em preparo":
            msg = f"Olá, {pedido_encontrado['nome']}! Seu pedido já está em preparo! 👨‍🍳🍿"
        else:
            msg = f"Olá, {pedido_encontrado['nome']}! Seu pedido saiu para entrega e logo estará aí! 🛵💨"
            
        link_whatsapp = f"https://api.whatsapp.com/send?phone={pedido_encontrado['telefone']}&text={urllib.parse.quote(msg)}"
        return RedirectResponse(url=f"/admin?abrir_whats={urllib.parse.quote_plus(link_whatsapp)}", status_code=303)

    return RedirectResponse(url="/admin", status_code=303)
    
@router.get("/pedidos/imprimir/{pedido_id}", response_class=HTMLResponse)
async def get_imprimir_pedido(pedido_id: str):
    res_pedido = supabase.table("pedidos").select("*").eq("id", pedido_id).execute()
    if not res_pedido.data:
        return HTMLResponse(content="<h1>Pedido nao encontrado</h1>", status_code=404)
        
    pedido_encontrado = res_pedido.data[0]
    
    # Tratamento limpo para data/hora
    raw_date = pedido_encontrado.get('criado_em', '')
    data_formatada = raw_date
    try:
        dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        data_formatada = dt.strftime("%d/%m as %H:%M")
    except Exception:
        pass

    # Formatação de itens e recheios
    recheios_raw = pedido_encontrado['recheios']
    if isinstance(recheios_raw, list):
        itens_html = "".join([f"<div style='padding-left: 8px; font-weight: bold;'>- {item}</div>" for item in recheios_raw])
    else:
        itens_html = f"<div style='padding-left: 8px; font-weight: bold;'>- {recheios_raw}</div>"

    html_cupom = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Imprimir Pedido #{pedido_encontrado['id']}</title>
        <style>
            @page {{
                size: 58mm auto;
                margin: 0mm !important;
            }}
            
            @media print {{
                html, body {{
                    width: 48mm !important;
                    margin: 0 auto !important;
                    padding: 0 !important;
                }}
            }}

            body {{
                font-family: Arial, Helvetica, sans-serif;
                font-size: 11px;
                line-height: 1.25;
                width: 48mm;
                margin: 0 auto;
                padding: 4px 0;
                color: #000;
                background: #fff;
                word-break: break-word;
            }}
            .text-center {{ text-align: center; }}
            .bold {{ font-weight: bold; }}
            .uppercase {{ text-transform: uppercase; }}
            .line {{ border-bottom: 1px dashed #000; margin: 6px 0; }}
            .double-line {{ border-bottom: 2px solid #000; margin: 8px 0; }}
            .flex {{ display: flex; justify-content: space-between; }}
            .box-entrega {{ border: 1.5px solid #000; padding: 4px; margin: 4px 0; }}
        </style>
    </head>
    <body>
        <div class="text-center bold" style="font-size: 13px;">
            DOCERIA DIVINO RECHEIO
        </div>
        <div class="text-center" style="font-size: 9px;">Feito com amor, recheada de sabor</div>
        <div class="double-line"></div>
        
        <div class="flex bold" style="font-size: 12px;">
            <span>PEDIDO #{pedido_encontrado['id']}</span>
            <span>{data_formatada}</span>
        </div>
        
        <!-- DESTAQUE PARA O MOTOBOY (ENTREGA) -->
        <div class="box-entrega">
            <div class="bold uppercase" style="font-size: 10px; border-b: 1px solid #000; padding-bottom: 2px; margin-bottom: 3px;">
                ENTREGA / ENDERECO
            </div>
            <div><span class="bold">BAIRRO:</span> <span class="bold uppercase" style="font-size: 12px;">{pedido_encontrado['bairro']}</span></div>
            <div><span class="bold">RUA:</span> <span class="uppercase">{pedido_encontrado['endereco']}</span></div>
            <div style="margin-top: 3px;"><span class="bold">CLIENTE:</span> {pedido_encontrado['nome']}</div>
            <div><span class="bold">TEL:</span> {pedido_encontrado['telefone']}</div>
        </div>

        <div class="line"></div>
        
        <div class="bold uppercase" style="font-size: 11px; margin-bottom: 2px;">
            ITENS DO PEDIDO:
        </div>
        <div style="font-size: 11px;">Copo: <span class="bold">{pedido_encontrado['tamanho']}</span></div>
        {itens_html}
    """
        
    if pedido_encontrado['adicional_nutella'] > 0:
        valor_nutella_formatado = f"{pedido_encontrado['adicional_nutella']:.2f}".replace('.', ',')
        html_cupom += f"""<div style="padding-left: 8px; font-weight: bold;">- Add Nutella: R$ {valor_nutella_formatado}</div>"""
        
    html_cupom += f"""
        <div class="double-line"></div>
        
        <!-- DESTAQUE FINANCEIRO -->
        <div class="bold uppercase" style="font-size: 11px;">PAGAMENTO:</div>
        <div class="bold uppercase" style="font-size: 12px; margin-bottom: 4px;">FORMA: {str(pedido_encontrado['forma_pagamento']).upper()}</div>
        
        <div class="flex" style="font-size: 11px;">
            <span>Taxa Entrega:</span>
            <span>R$ {f"{pedido_encontrado['taxa_entrega']:.2f}".replace('.', ',')}</span>
        </div>
        <div class="flex bold" style="font-size: 13px; margin-top: 3px; border-top: 1px solid #000; padding-top: 3px;">
            <span>TOTAL A COBRAR:</span>
            <span>R$ {f"{pedido_encontrado['total']:.2f}".replace('.', ',')}</span>
        </div>
        
        <div class="line"></div>
        <div class="text-center bold" style="margin-top: 8px; font-size: 10px;">
            Obrigado pelo pedido!
        </div>

        <script>
            window.onload = function() {{
                window.print();
                setTimeout(function() {{
                    window.close();
                }}, 500);
            }};
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_cupom, status_code=200)

@router.post("/taxas/promocao")
async def post_promocao_taxas(taxa_uniforme: float = Form(...)):
    if taxa_uniforme >= 0:
        res_bairros = supabase.table("bairros").select("*").execute()
        for item in res_bairros.data:
            if float(item["taxa"]) > taxa_uniforme:
                supabase.table("bairros").update({"taxa": taxa_uniforme}).eq("nome", item["nome"]).execute()
            
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/taxas/resetar")
async def post_resetar_taxas():
    for bairro, taxa_original in BAIRROS_ORIGINAIS.items():
        supabase.table("bairros").upsert({"nome": bairro, "taxa": taxa_original}).execute()
        
    return RedirectResponse(url="/admin", status_code=303)