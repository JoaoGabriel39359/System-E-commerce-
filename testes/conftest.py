import pytest
from fastapi.testclient import TestClient
from main import app  

@pytest.fixture
def client():
    """Fixture que fornece um cliente de teste para simular as requisições HTTP"""
    with TestClient(app) as c:
        yield c