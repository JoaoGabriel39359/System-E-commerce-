# 🍫 Doceria Divino Recheio 🍫

O **Divino Recheio** é uma aplicação web para automatização de pedidos e gerenciamento de uma doceria especializada em copões de doces personalizados. O sistema conta com uma área voltada para o cliente (cardápio interativo com envio de pedidos para o WhatsApp) e um painel de administração completo para controle da cozinha, estoque de ingredientes, taxas de entrega e status da loja em tempo real.

---

## 🚀 Tecnologias Utilizadas

O projeto foi construído utilizando uma arquitetura moderna, leve e integrada:

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3) - Framework rápido e de alta performance para APIs.
- **Banco de Dados & Real-Time**: [Supabase](https://supabase.com/) - Plataforma open-source que provê banco de dados PostgreSQL e integração simplificada.
- **Frontend**: HTML5, CSS3 personalizado e JavaScript com [Vue.js](https://vuejs.org/) na área do cliente para reatividade em tempo real.
- **Templates**: [Jinja2](https://palletsprojects.com/p/jinja/) para renderização dinâmica das páginas do lado do servidor.
- **Testes**: [Pytest](https://docs.pytest.org/) e `fastapi.testclient` para garantir a estabilidade das rotas e regras de negócio.

---

## 📋 Funcionalidades Principais

### 🛒 Área do Cliente (`/`)
- **Montagem do Copo**: O cliente pode selecionar o tamanho do copo e escolher os recheios disponíveis em tempo real.
- **Promoções Dinâmicas**: Aplicação automática de brindes ou regras de frete (ex: Nutella Grátis) configuradas pelo painel admin.
- **Cálculo de Entrega**: Seleção do bairro com carregamento automático da taxa de entrega correta.
- **Integração com WhatsApp**: Finalização do pedido estruturada e envio direto para o WhatsApp do vendedor com todas as informações.

### 🔐 Autenticação (`/admin/login`)
- Acesso restrito ao painel de controle utilizando sessões baseadas em Cookies seguros (`httponly` e `samesite="lax"`).

### 👨‍🍳 Painel do Administrador / Cozinha (`/admin`)
- **Painel de Pedidos Ativos**: Visualização em tempo real dos pedidos recebidos com atualização de status (Pendente, Em preparo, Saiu para entrega).
- **Avisos Automáticos no WhatsApp**: Disparo automático de mensagens para o WhatsApp do cliente quando o pedido muda para "Em preparo" ou "Saiu para entrega".
- **Impressão de Cupom não Fiscal**: Emissão de cupom formatado em fonte monoespaçada (`Courier`) para impressoras térmicas de cupom (80mm).
- **Gerenciamento de Ingredientes**: Ativação/desativação instantânea de recheios (seletor de estoque disponível).
- **Configurações Gerais**:
  - Abertura e fechamento da loja em tempo real.
  - Ativação da promoção "Nutella Grátis".
  - Atualização do número de telefone de atendimento.
- **Gestão de Taxas de Entrega**:
  - Alteração individual dos valores por bairro.
  - Ferramenta de promoção rápida (definir teto máximo uniforme de taxa).
  - Restauração rápida das taxas originais aos valores padrões do banco.

---

## 📂 Estrutura do Projeto

```text
DivinoRecheio/
├── database.py         # Configuração do cliente Supabase e banco em memória de taxas por bairro
├── main.py             # Arquivo principal e ponto de entrada da aplicação FastAPI
├── routers/            # Controladores modulares de rotas
│   ├── admin.py        # Rotas administrativas, autenticação, gerenciamento de pedidos e taxas
│   └── cliente.py      # Rota do cardápio público do cliente
├── schemas/            # Schemas Pydantic para validação de dados
│   ├── ingrediente.py  # Estruturas para ingredientes
│   └── pedido.py       # Estruturas para criação e persistência de pedidos
├── static/             # Arquivos estáticos (JavaScript, CSS, Imagens)
│   ├── js/
│   │   └── app-cliente.js  # Lógica em Vue.js para interatividade do cardápio do cliente
│   └── logo.png        # Logo oficial da doceria
├── templates/          # Templates HTML integrados com Jinja2
│   ├── admin.html      # Painel da cozinha e configurações
│   ├── cardapio.html   # Cardápio interativo do cliente
│   └── login.html      # Tela de login do administrador
└── testes/             # Bateria de testes automatizados
    ├── conftest.py     # Fixtures do pytest
    └── test_admin.py   # Testes unitários das regras do painel com mock do Supabase
```

---

## 🗄️ Estrutura do Banco de Dados (Supabase)

Para o correto funcionamento da aplicação, crie as seguintes tabelas no seu banco de dados PostgreSQL do Supabase:

### 1. Tabela: `ingredientes`
Guarda a lista de recheios do cardápio.
*   `nome` (text, Primary Key)
*   `disponivel` (boolean, Default: `true`)

### 2. Tabela: `configuracoes`
Guarda as chaves e valores das preferências da loja.
*   `chave` (text, Primary Key)
*   `valor` (text)

> **Observação**: Insira os seguintes registros iniciais na tabela `configuracoes`:
> | chave | valor |
> | :--- | :--- |
> | `loja_aberta` | `true` ou `false` |
> | `nutella_gratis` | `true` ou `false` |
> | `whatsapp_vendedor` | `5524XXXXXXXXX` (código do país + DDD + número) |

### 3. Tabela: `pedidos`
Gerencia os pedidos ativos na cozinha.
*   `id` (text, Primary Key) - Código de 8 caracteres
*   `nome` (text)
*   `telefone` (text)
*   `endereco` (text)
*   `bairro` (text)
*   `tamanho` (text)
*   `recheios` (jsonb ou text[])
*   `adicional_nutella` (numeric)
*   `forma_pagamento` (text)
*   `taxa_entrega` (numeric)
*   `total` (numeric)
*   `status` (text, Default: `'Pendente'`)
*   `criado_em` (text ou timestamp)

---

## 🛠️ Instalação e Execução Local

### Pré-requisitos
- Python 3.8 ou superior instalado.
- Acesso a um projeto no Supabase.

### Passo 1: Clonar o Repositório
```bash
git clone https://github.com/seu-usuario/DivinoRecheio.git
cd DivinoRecheio
```

### Passo 2: Criar e Ativar o Ambiente Virtual
No Linux/macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

No Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Passo 3: Instalar as Dependências
Como o projeto não contém um `requirements.txt` explícito na pasta raiz, você pode instalar as bibliotecas necessárias rodando:
```bash
pip install fastapi uvicorn supabase jinja2 pydantic python-dotenv pytest httpx
```

### Passo 4: Configurar as Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto seguindo as chaves necessárias (conforme o arquivo `.env` de configuração):
```env
SUPABASE_URL=https://sua-url-do-supabase.supabase.co
SUPABASE_KEY=sua-chave-anon-ou-service-role
ADMIN_USER=usuario_desejado_para_o_painel
ADMIN_PASS=senha_desejada_para_o_painel
```

### Passo 5: Executar o Servidor de Desenvolvimento
Inicie o servidor localmente com o Uvicorn:
```bash
uvicorn main:app --reload
```

A aplicação estará disponível em:
- **Cardápio do Cliente**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Painel Administrativo**: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
- **Documentação Swagger**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🧪 Executando os Testes Automatizados

O projeto conta com testes unitários focados nas rotas administrativas e nas integrações simuladas do Supabase. Para executar toda a bateria de testes, certifique-se de estar com o ambiente virtual ativo e execute:

```bash
pytest
```

Para ver os prints ou detalhes no terminal durante a execução dos testes:
```bash
pytest -v -s
```
