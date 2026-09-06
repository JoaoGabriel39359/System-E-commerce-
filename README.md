# Divino Recheio — Custom E-Commerce Ordering System

A full-stack ordering platform built for a dessert business, combining an interactive customer menu with a real-time kitchen and administration dashboard.

[![Live menu](https://img.shields.io/badge/Live_Menu-Open-ec4899?style=for-the-badge)](https://divino-recheio.up.railway.app)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3FCF8E?style=flat-square&logo=supabase&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-Pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)

## Product overview

The platform digitizes the complete ordering workflow: customers configure a product, receive real-time pricing, select delivery or pickup, and send a structured order through WhatsApp. The business manages availability, orders, delivery fees, promotions, and kitchen operations from a protected dashboard.

### Customer experience

- Interactive product builder with size and filling selection
- Real-time ingredient availability
- Automatic pricing and delivery-fee calculation
- Delivery or store-pickup flow
- Dynamic promotions and optional extras
- Structured WhatsApp checkout
- Responsive, mobile-first interface

### Administration and kitchen operations

- Protected administrator login
- Live order queue and status management
- WhatsApp notifications when order status changes
- Ingredient availability controls
- Store open/closed status
- Promotion and contact-number settings
- Delivery fees by neighborhood
- Thermal receipt printing for 80 mm printers
- Automated tests for business and administrative rules

## Business impact

This project replaces manual order transcription and scattered operational controls with a single workflow. It reduces ordering errors, keeps the menu synchronized with current stock, standardizes WhatsApp messages, and gives the kitchen a clear view of active orders.

## Architecture

```text
Customer menu / Admin dashboard
       Vue.js + JavaScript
                |
                v
          FastAPI + Jinja2
                |
                v
       Supabase / PostgreSQL
                |
                v
        WhatsApp workflow
```

## Tech stack

| Area | Technologies |
|---|---|
| Backend | Python, FastAPI, Pydantic |
| Frontend | Vue.js, JavaScript, HTML, CSS |
| Templates | Jinja2 |
| Database | Supabase, PostgreSQL |
| Integrations | WhatsApp |
| Quality | Pytest, FastAPI TestClient |
| Deployment | Railway, Uvicorn |

## Repository structure

```text
.
├── main.py                 # FastAPI entry point
├── database.py             # Supabase integration and data access
├── routers/
│   ├── admin.py            # Authentication, orders and settings
│   └── cliente.py          # Public menu routes
├── schemas/                # Pydantic models
├── static/                 # CSS, JavaScript and images
├── templates/              # Customer, login and admin views
├── testes/                 # Automated tests
├── .env.example            # Safe environment template
├── Procfile
└── requirements.txt
```

## Local setup

### Prerequisites

- Python 3.10+
- A Supabase project

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/JoaoGabriel39359/System-E-commerce-.git
cd System-E-commerce-
python -m venv .venv
source .venv/bin/activate
```

On Windows, activate it with `.venv\\Scripts\\activate`.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Use your own credentials in `.env`. Never commit this file.

### 4. Run the application

```bash
uvicorn main:app --reload
```

Open:

- Customer menu: `http://127.0.0.1:8000`
- Admin login: `http://127.0.0.1:8000/admin/login`
- API documentation: `http://127.0.0.1:8000/docs`

## Tests

```bash
pytest -q
```

Tests use mocked integrations where appropriate, allowing business rules to be checked without accessing production services.

## Privacy and security

- Administrative access is protected by session-based authentication.
- Credentials and production configuration belong only in environment variables.
- The public live link points only to the customer-facing menu.
- Administrator credentials are never provided publicly.
- Please report security concerns privately instead of opening a public issue.

## Author

**João Gabriel Vieira Barbosa**  
Full-Stack Developer focused on Python, FastAPI, React, APIs, and business automation.

[GitHub profile](https://github.com/JoaoGabriel39359)
