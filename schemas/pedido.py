from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PedidoCreate(BaseModel):
    nome: str
    telefone: str
    endereco: str
    bairro: str
    tamanho: str
    recheios: List[str]
    adicional_nutella: float
    forma_pagamento: str
    taxa_entrega: float
    total: float

class Pedido(PedidoCreate):
    id: str
    status: str
    criado_em: str
