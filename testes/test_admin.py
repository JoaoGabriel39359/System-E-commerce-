import pytest
import urllib.parse
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def mock_supabase():
    """Mocka o objeto supabase filtrando e persistindo retornos de forma flexível"""
    with patch("routers.admin.supabase") as mock_supabase_obj:
        dados_ingredientes = [
            {"nome": "Leite Ninho", "disponivel": True},
            {"nome": "Nutella", "disponivel": False}
        ]
        dados_configuracoes = [
            {"chave": "loja_aberta", "valor": "true"},
            {"chave": "nutella_gratis", "valor": "false"},
            {"chave": "whatsapp_vendedor", "valor": "5524998217201"}
        ]
        # Deixamos os dados de pedidos acessíveis para modificação nos testes
        dados_pedidos = []

        def resolver_tabela(nome_tabela):
            mock_chain = MagicMock()
            # Faz qualquer método encadeado retornar o próprio mock estruturado
            mock_chain.select.return_value = mock_chain
            mock_chain.order.return_value = mock_chain
            mock_chain.eq.return_value = mock_chain
            mock_chain.update.return_value = mock_chain
            mock_chain.insert.return_value = mock_chain
            mock_chain.delete.return_value = mock_chain

            if nome_tabela == "ingredientes":
                mock_chain.execute.return_value.data = dados_ingredientes
            elif nome_tabela == "configuracoes":
                mock_chain.execute.return_value.data = dados_configuracoes
            elif nome_tabela == "pedidos":
                # Retorna os dados dinâmicos da lista de pedidos local externa
                mock_chain.execute.return_value.data = dados_pedidos
            else:
                mock_chain.execute.return_value.data = []
            
            return mock_chain

        mock_supabase_obj.table.side_effect = resolver_tabela
        
        # Guardamos uma referência na própria fixture para permitir que os testes 
        # alterem os dados de pedidos sob demanda antes de chamar o client
        mock_supabase_obj._dados_pedidos = dados_pedidos
        yield mock_supabase_obj


# --- BATERIA DE TESTES ---

def test_get_admin_page_success(mock_supabase):
    """Garante que a rota principal do admin renderiza com sucesso as dependências"""
    response = client.get("/admin", cookies={"admin_session": "autenticado_divino"})
    assert response.status_code == 200
    assert "Painel da Cozinha" in response.text
    assert "Leite Ninho" in response.text


def test_api_status_loja(mock_supabase):
    """Testa o endpoint JSON que o Vue.js consome para saber o status da loja"""
    response = client.get("/admin/api/status-loja")
    assert response.status_code == 200
    dados = response.json()
    assert dados["loja_aberta"] is True
    assert "Leite Ninho" in dados["ingredientes_disponiveis"]


def test_post_salvar_configuracoes(mock_supabase):
    """Testa o envio do formulário de salvamento do painel administrativo"""
    payload = {
        "loja_aberta": "true",
        "whatsapp_vendedor": "(24) 99821-7201",
        "ingrediente_Nutella": "true"
    }
    response = client.post("/admin/salvar", data=payload, follow_redirects=False, cookies={"admin_session": "autenticado_divino"})
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"


def test_post_novo_ingrediente(mock_supabase):
    """Valida a criação de um novo recheio no cardápio"""
    payload = {"novo_nome": "  Morango Fresco  "}
    response = client.post("/admin/novo-ingrediente", data=payload, follow_redirects=False)
    assert response.status_code == 303


def test_post_novo_pedido_visto_pelo_cliente(mock_supabase):
    """Valida o endpoint que recebe o JSON enviado pelo script Vue.js do cliente"""
    json_pedido = {
        "nome": "Carlos Silva",
        "telefone": "24987654321",
        "endereco": "Rua das Flores, 123",
        "bairro": "Centro",
        "tamanho": "500ML",
        "recheios": ["Nutella", "Ninho"],
        "adicional_nutella": 3.0,
        "forma_pagamento": "Pix ⚡",
        "taxa_entrega": 5.0,
        "total": 35.0
    }
    response = client.post("/admin/pedidos/novo", json=json_pedido)
    assert response.status_code == 200
    dados = response.json()
    assert dados["status"] == "sucesso"
    assert "pedido_id" in dados


@pytest.mark.parametrize("status_novo, texto_esperado", [
    ("Em preparo", "Seu pedido já está em preparo!"),
    ("Saiu para entrega", "Seu pedido saiu para entrega"),
])
def test_atualizar_status_pedido_com_whatsapp(mock_supabase, status_novo, texto_esperado):
    """Testa a mudança de status e a geração automática do link de aviso do WhatsApp"""
    # Injeta o pedido simulado diretamente na lista monitorada pelo mock global
    mock_supabase._dados_pedidos.clear()
    mock_supabase._dados_pedidos.append({
        "id": "A1B2C3D4",
        "nome": "Mariana",
        "telefone": "5524999999999"
    })
    
    payload = {"pedido_id": "A1B2C3D4", "novo_status": status_novo}
    response = client.post("/admin/pedidos/atualizar", data=payload, follow_redirects=False)
    
    assert response.status_code == 303
    url_redirecionamento = urllib.parse.unquote(urllib.parse.unquote(response.headers["location"]))
    assert texto_esperado in url_redirecionamento


def test_concluir_ou_cancelar_pedido_deleta_da_tela_ativa(mock_supabase):
    """Pedidos Concluídos ou Cancelados devem sumir do painel (deletados do banco ativo)"""
    mock_supabase._dados_pedidos.clear()
    mock_supabase._dados_pedidos.append({"id": "ABC"})
    
    payload = {"pedido_id": "ABC", "novo_status": "Concluído"}
    response = client.post("/admin/pedidos/atualizar", data=payload, follow_redirects=False)
    
    assert response.status_code == 303


def test_get_imprimir_pedido_html(mock_supabase):
    """Verifica se a rota de impressão gera o cupom não-fiscal em formato texto (Courier)"""
    mock_supabase._dados_pedidos.clear()
    mock_supabase._dados_pedidos.append({
        "id": "XF92",
        "criado_em": "2026-05-20T19:00:00",
        "nome": "João Gabriel Dev",
        "telefone": "5524999998888",
        "bairro": "Aterrado",
        "endereco": "Av Lucas, 90",
        "tamanho": "1L",
        "recheios": ["Ouro Branco", "Prestigio"],
        "adicional_nutella": 0.0,
        "forma_pagamento": "pix",
        "taxa_entrega": 7.00,
        "total": 44.00
    })
    
    response = client.get("/admin/pedidos/imprimir/XF92")
    assert response.status_code == 200
    assert "DOCERIA DIVINO RECHEIO" in response.text
    assert "PEDIDO #XF92" in response.text