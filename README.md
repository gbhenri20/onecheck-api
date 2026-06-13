# OneCheck API

API REST para gestão de vistorias imobiliárias. Permite cadastrar imóveis, contratos de locação e checklists de vistoria — com controle de acesso por perfil, autenticação JWT + MFA via TOTP e upload de fotos por item vistoriado.

## Funcionalidades

- **Autenticação** — login com JWT, MFA obrigatório para roles críticas (admin, gestor, vistoriador), refresh token com rotação e revogação
- **Gestão de imóveis** — cadastro com endereço e cômodos padrão automáticos, filtros por status e visibilidade por role
- **Contratos de locação** — criação vincula imóvel e locatário, gera agendamentos de vistoria inicial e de encerramento automaticamente
- **Checklists de vistoria** — preenchimento por cômodo/item, upload de foto por item, fluxo de submissão → aceite/rejeição
- **Registro de problemas** — locatário e vistoriador registram ocorrências no contrato, com prioridade e status
- **Dashboard** — contadores em tempo real de imóveis locados, checklists pendentes, problemas abertos e vistorias agendadas
- **Logs de auditoria** — toda operação relevante é registrada com usuário, entidade e timestamp
- **Admin** — seed e refresh de dados via endpoint protegido por secret

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Framework | FastAPI 0.115 + Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Banco (produção) | PostgreSQL (Render) |
| Banco (local) | SQLite (padrão) ou PostgreSQL |
| Autenticação | python-jose (JWT) + pyotp (TOTP) + bcrypt |
| Testes | pytest + pytest-cov + httpx |
| CI | GitHub Actions |
| Deploy | Render |

## Perfis de acesso (RBAC)

| Role | Descrição |
|------|-----------|
| `admin` | Acesso total, MFA obrigatório |
| `gestor` | Gerencia imóveis, contratos e usuários, MFA obrigatório |
| `vistoriador` | Preenche e submete checklists, MFA obrigatório |
| `locatario` | Visualiza seus contratos e checklists, registra problemas |
| `visualizador` | Leitura geral, sem ações de escrita |

## Endpoints principais

```
POST   /api/v1/auth/login
POST   /api/v1/auth/mfa/verify
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout

GET    /api/v1/usuarios/me
PATCH  /api/v1/usuarios/me
POST   /api/v1/usuarios
GET    /api/v1/usuarios/{id}

GET    /api/v1/imoveis
POST   /api/v1/imoveis
GET    /api/v1/imoveis/{id}
PUT    /api/v1/imoveis/{id}
POST   /api/v1/imoveis/{id}/endereco
GET    /api/v1/imoveis/{id}/comodos

GET    /api/v1/contratos
POST   /api/v1/contratos
GET    /api/v1/contratos/{id}/checklists
POST   /api/v1/contratos/{id}/checklists
GET    /api/v1/contratos/{id}/problemas
POST   /api/v1/contratos/{id}/problemas

GET    /api/v1/checklists/{id}
POST   /api/v1/checklists/{id}/itens
PUT    /api/v1/checklists/{id}/itens/{item_id}
POST   /api/v1/checklists/{id}/itens/{item_id}/fotos
PATCH  /api/v1/checklists/{id}/submeter
PATCH  /api/v1/checklists/{id}/aceitar

GET    /api/v1/dashboard
GET    /api/v1/logs
GET    /api/v1/health
```

Documentação interativa disponível em `/docs` quando o servidor estiver rodando.

---

## Executando localmente

### Pré-requisitos

- Python 3.12+
- Git

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd onecheck-api
```

### 2. Criar e ativar o ambiente virtual

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Obrigatório em produção — em desenvolvimento um valor padrão é usado
JWT_SECRET=troque-por-um-secret-seguro

# URL do banco. Sem essa variável a API usa SQLite local (onecheck.db)
# DATABASE_URL=postgresql://usuario:senha@localhost:5432/onecheck

# Secret para endpoints de seed/admin (opcional em dev)
SEED_SECRET=troque-por-um-secret-seguro

# Diretório de uploads (padrão: ./uploads)
# UPLOAD_DIR=uploads
```

### 5. Iniciar o servidor

```bash
uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000`.
Documentação interativa: `http://localhost:8000/docs`

### 6. Popular o banco com dados iniciais (opcional)

```bash
python scripts/seed.py
```

---

## Executando os testes

### Instalar dependências de teste

```bash
pip install -r requirements-test.txt
```

### Rodar a suíte completa

```bash
# Usando o Python do venv diretamente (recomendado se o venv não estiver ativo no shell)
.venv/bin/pytest

# Ou com o venv ativo
pytest
```

Os testes usam **SQLite em memória** por padrão. Para rodar contra PostgreSQL, defina a variável antes de executar:

```bash
TEST_DATABASE_URL=postgresql://usuario:senha@localhost:5432/onecheck_test pytest
```

### Relatório de cobertura

```bash
pytest --cov=app --cov-report=html
# Abre htmlcov/index.html no navegador
```

Cobertura atual: **95%**

---

## Estrutura do projeto

```
app/
├── main.py          # Ponto de entrada FastAPI
├── config.py        # Variáveis de ambiente
├── database.py      # Engine e sessão SQLAlchemy
├── models.py        # Modelos ORM
├── schemas.py       # Schemas Pydantic + helpers ok()/fail()
├── auth.py          # JWT, bcrypt, TOTP, refresh token
├── deps.py          # Dependências FastAPI (get_current_user, require_roles)
├── serializers.py   # Funções de serialização e paginação
└── routers/
    ├── auth_router.py
    ├── usuarios.py
    ├── imoveis.py
    ├── contratos.py
    ├── checklists.py
    ├── dashboard.py
    ├── health.py
    └── admin.py

tests/
├── conftest.py          # Fixtures globais (banco, client, usuários, dados)
├── unit/                # Testes unitários (auth, schemas, serializers)
└── integration/         # Testes de integração por router
```

---

## CI / CD

O pipeline de CI roda automaticamente a cada push e pull request via **GitHub Actions** (`.github/workflows/tests.yml`):

1. Sobe um container PostgreSQL 16
2. Instala as dependências
3. Executa `pytest --cov-fail-under=70`

O deploy é feito no **Render** via `render.yaml`, com PostgreSQL gerenciado e seed automático no primeiro deploy.
