from pydantic import BaseModel

class IngredienteBase(BaseModel):
    nome: str
    disponivel: bool

class IngredienteUpdate(BaseModel):
    status_ingredientes: dict[str, bool]

class AtualizarEstoqueSchema(BaseModel):
    status_ingredientes: dict[str, bool]