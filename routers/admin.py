import os
import uuid
import urllib.parse
from datetime import datetime
from fastapi import APIRouter, Request, Form, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from schemas.pedido import PedidoCreate
from database import supabase, bairros_db, BAIRROS_ORIGINAIS

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")

ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASS")

@router.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request, erro: str = None):
    return templates.TemplateResponse(
        request=request,
        name="login.html", 
        context={"request": request, "erro": erro}
    )

# --- ROTA: PROCESSA O LOGIN (POST) ---
@router.post("/login")
async def post_login(username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USER and password == ADMIN_PASS:
        # Credenciais corretas! Redireciona para o admin e salva o Cookie de sessão
        resposta = RedirectResponse(url="/admin", status_code=303)
        resposta.set_cookie(
            key="admin_session", 
            value="autenticado_divino", 
            httponly=True, # Protege contra ataques XSS de scripts maliciosos
            samesite="lax"
        )
        return resposta
    else:
        # Credenciais erradas, volta informando o erro na tela
        return RedirectResponse(url="/admin/login?erro=Usu%C3%A1rio%20ou%20senha%20inv%C3%A1lidos.", status_code=303)

# --- ROTA: LOGOUT (OPCIONAL) ---
@router.get("/logout")
async def get_logout():
    resposta = RedirectResponse(url="/admin/login", status_code=303)
    resposta.delete_cookie(key="admin_session")
    return resposta

@router.get("", response_class=HTMLResponse)
async def get_admin(request: Request, admin_session: str = Cookie(default=None)):
    if admin_session != "autenticado_divino":
        return RedirectResponse(url="/admin/login", status_code=303)

    res_ing = supabase.table("ingredientes").select("*").order("nome").execute()
    ingredientes_formatados = {item["nome"]: {"disponivel": item["disponivel"]} for item in res_ing.data}

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
            "bairros": bairros_db,
            "config": config_formatada,
            "pedidos": pedidos_formatados
        },
        request=request
    )

@router.get("/api/status-loja")
async def get_status_loja():
    res_conf = supabase.table("configuracoes").select("*").execute()
    config = {item["chave"]: item["valor"] for item in res_conf.data}

    res_ing = supabase.table("ingredientes").select("nome").eq("disponivel", True).execute()
    lista_ingredientes = [item["nome"] for item in res_ing.data]

    return {
        "loja_aberta": config.get("loja_aberta") == "true",
        "nutella_gratis": config.get("nutella_gratis") == "true",
        "ingredientes_disponiveis": lista_ingredientes
    }

@router.post("/salvar")
async def post_salvar(request: Request, admin_session: str = Cookie(default=None)):
    if admin_session != "autenticado_divino":
        return RedirectResponse(url="/admin/login", status_code=303)

    form_data = await request.form()
    
    res_ing = supabase.table("ingredientes").select("nome").execute()
    for item in res_ing.data:
        nome = item["nome"]
        status_disponivel = f"ingrediente_{nome}" in form_data
        supabase.table("ingredientes").update({"disponivel": status_disponivel}).eq("nome", nome).execute()

    # 2. Controla a Promoção de Nutella Grátis e o Status de Loja Aberta
    loja_status = "true" if "loja_aberta" in form_data else "false"
    nutella_status = "true" if "nutella_gratis" in form_data else "false"
    
    supabase.table("configuracoes").update({"valor": loja_status}).eq("chave", "loja_aberta").execute()
    supabase.table("configuracoes").update({"valor": nutella_status}).eq("chave", "nutella_gratis").execute()

    # 3. Atualiza o WhatsApp do Vendedor se enviado
    if "whatsapp_vendedor" in form_data:
        raw_phone = form_data["whatsapp_vendedor"]
        digits = "".join([c for c in raw_phone if c.isdigit()])
        if len(digits) in [10, 11] and not digits.startswith("55"):
            digits = "55" + digits
        supabase.table("configuracoes").update({"valor": digits}).eq("chave", "whatsapp_vendedor").execute()

    for bairro in bairros_db.keys():
        campo_taxa = f"taxa_{bairro}"
        if campo_taxa in form_data:
            try:
                bairros_db[bairro] = float(form_data[campo_taxa])
            except ValueError:
                pass
        
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
        return HTMLResponse(content="<h1>Pedido não encontrado</h1>", status_code=404)
        
    pedido_encontrado = res_pedido.data[0]
    recheios_texto = ", ".join(pedido_encontrado['recheios']) if isinstance(pedido_encontrado['recheios'], list) else pedido_encontrado['recheios']

    html_cupom = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Imprimir Pedido #{pedido_encontrado['id']}</title>
        <style>
            @page {{ margin: 0; }}
            body {{
                font-family: 'Courier New', Courier, monospace;
                font-size: 12px;
                width: 100%;
                max-width: 280px;
                margin: 0;
                padding: 8px;
                color: #000;
                background: #fff;
            }}
            .text-center {{ text-align: center; }}
            .bold {{ font-weight: bold; }}
            .line {{ border-bottom: 1px dashed #000; margin: 8px 0; }}
            .flex {{ display: flex; justify-content: space-between; }}
        </style>
    </head>
    <body>
        <div class="text-center bold" style="font-size: 14px;">
            🍫 DOCERIA DIVINO RECHEIO 🍫
        </div>
        <div class="text-center">Feito com amor, recheada de sabor</div>
        <div class="line"></div>
        
        <div class="bold" style="font-size: 13px;">PEDIDO #{pedido_encontrado['id']}</div>
        <div>Data: {pedido_encontrado['criado_em']}</div>
        <div class="line"></div>
        
        <div class="bold">👤 CLIENTE:</div>
        <div>Nome: {pedido_encontrado['nome']}</div>
        <div>Tel: {pedido_encontrado['telefone']}</div>
        <div class="line"></div>
        
        <div class="bold">📍 ENTREGA:</div>
        <div>Bairro: {pedido_encontrado['bairro']}</div>
        <div>Endereço: {pedido_encontrado['endereco']}</div>
        <div class="line"></div>
        
        <div class="bold">🛒 ITENS:</div>
        <div>Copão personalizado: {pedido_encontrado['tamanho']}</div>
        <div style="padding-left: 8px;">• Recheios: {recheios_texto}</div>
    """
        
    if pedido_encontrado['adicional_nutella'] > 0:
        html_cupom += f"""<div style="padding-left: 8px;">• Adicional Nutella: R$ 3,00</div>"""
        
    html_cupom += f"""
        <div class="line"></div>
        <div class="bold">💵 PAGAMENTO:</div>
        <div>Forma: {pedido_encontrado['forma_pagamento'].upper()}</div>
        
        <div class="flex font-medium" style="margin-top: 6px;">
            <span>Taxa Entrega:</span>
            <span>R$ {f"{pedido_encontrado['taxa_entrega']:.2f}".replace('.', ',')}</span>
        </div>
        <div class="flex bold" style="font-size: 13px; margin-top: 3px;">
            <span>TOTAL GERAL:</span>
            <span>R$ {f"{pedido_encontrado['total']:.2f}".replace('.', ',')}</span>
        </div>
        
        <div class="line"></div>
        <div class="text-center bold" style="margin-top: 15px; font-size: 11px;">
            Obrigado pelo pedido! 💕
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
        for bairro, taxa_atual in list(bairros_db.items()):
            if taxa_atual > taxa_uniforme:
                bairros_db[bairro] = taxa_uniforme
            
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/taxas/resetar")
async def post_resetar_taxas():
    # Restaura o dicionário em memória para os valores salvos no backup estático
    for bairro, taxa_original in BAIRROS_ORIGINAIS.items():
        bairros_db[bairro] = taxa_original
        
    return RedirectResponse(url="/admin", status_code=303)