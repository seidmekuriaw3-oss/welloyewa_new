## ፋይል #303: `docs/development_guide.md`

```markdown
# Wolloyewa Store Bot - Development Guide

## 📚 Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment](#development-environment)
3. [Project Structure](#project-structure)
4. [Coding Standards](#coding-standards)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Database Migrations](#database-migrations)
8. [API Development](#api-development)
9. [Bot Development](#bot-development)
10. [Contributing Guidelines](#contributing-guidelines)

---

## 🚀 Getting Started

### Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Python | 3.11+ | [python.org](https://python.org) |
| PostgreSQL | 15+ | [postgresql.org](https://postgresql.org) |
| Redis | 7+ | [redis.io](https://redis.io) |
| Docker | 24+ | [docker.com](https://docker.com) |
| Git | 2.40+ | [git-scm.com](https://git-scm.com) |

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/seidmekuriaw3-oss/welloyewa.git
cd welloyewa

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Copy environment variables
cp .env.example .env

# 5. Run database migrations
alembic upgrade head

# 6. Seed database (optional)
python scripts/seed_db.py

# 7. Run development server
uvicorn main:app --reload
```

---

## 💻 Development Environment

### VS Code Configuration

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm Configuration

```xml
<!-- .idea/inspectionProfiles/profiles_settings.xml -->
<component name="InspectionProjectProfileManager">
  <settings>
    <option name="PROJECT_PROFILE" value="Wolloyewa" />
    <option name="USE_PROJECT_PROFILE" value="true" />
  </settings>
</component>
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

---

## 📁 Project Structure

```
welloyewa/
├── alembic/              # Database migrations
│   ├── versions/         # Migration files
│   ├── env.py           # Alembic environment
│   └── script.py.mako   # Migration template
│
├── core/                 # Core functionality
│   ├── config.py        # Settings
│   ├── security.py      # Auth, encryption
│   ├── exceptions.py    # Custom exceptions
│   └── logger.py        # Logging setup
│
├── apps/                 # Business modules
│   ├── users/           # User management
│   ├── products/        # Product catalog
│   ├── orders/          # Order processing
│   ├── payments/        # Payment handling
│   └── ...
│
├── infrastructure/       # Technical modules
│   ├── database/        # DB connection
│   ├── redis/           # Cache client
│   └── payments/        # Gateway integrations
│
├── bot/                  # Telegram bot
│   ├── handlers/        # Command handlers
│   ├── keyboards/       # Custom keyboards
│   └── middlewares/     # Bot middleware
│
├── tests/                # Test suite
│   ├── test_api/        # API tests
│   ├── test_bot/        # Bot tests
│   └── test_unit/       # Unit tests
│
├── scripts/              # Utility scripts
├── docs/                 # Documentation
└── devops/               # Deployment configs
```

---

## 📝 Coding Standards

### Python Style Guide

```python
# ✅ Good
def calculate_total(items: List[Dict]) -> Decimal:
    """
    Calculate total price of items.
    
    Args:
        items: List of items with price and quantity
        
    Returns:
        Total amount as Decimal
    """
    total = Decimal('0')
    for item in items:
        total += item['price'] * item['quantity']
    return total

# ❌ Bad
def calc(items):
    t=0
    for i in items:
        t+=i['p']*i['q']
    return t
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables | snake_case | `user_name` |
| Functions | snake_case | `get_user()` |
| Classes | PascalCase | `UserService` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Private | _leading_underscore | `_internal_method()` |

### Import Order

```python
# 1. Standard library
import json
from datetime import datetime
from typing import List, Optional

# 2. Third-party
from fastapi import APIRouter, Depends
from sqlalchemy import select

# 3. Local
from core.config import settings
from apps.users.models import User
```

### Type Hints

```python
# Always use type hints
async def get_user(
    user_id: int,
    include_deleted: bool = False,
) -> Optional[User]:
    user = await db.get(User, user_id)
    return user if user else None
```

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_api/test_users.py

# Run specific test
pytest tests/test_api/test_users.py::TestUserEndpoints::test_register_user

# Run by marker
pytest -m unit
pytest -m api
pytest -m integration
```

### Writing Tests

```python
# tests/test_api/test_users.py
import pytest
from httpx import AsyncClient

@pytest.mark.api
class TestUserEndpoints:
    async def test_register_user(self, client: AsyncClient, sample_user_data):
        response = await client.post("/api/v1/users/register", json=sample_user_data)
        assert response.status_code == 201
        assert response.json()["telegram_id"] == sample_user_data["telegram_id"]
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def sample_user_data():
    return {
        "telegram_id": 123456789,
        "first_name": "Test",
        "last_name": "User",
        "phone_number": "0912345678"
    }
```

---

## 🐛 Debugging

### VS Code Debug Configuration

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["main:app", "--reload"],
      "jinja": true
    },
    {
      "name": "Python: Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v"]
    }
  ]
}
```

### Logging

```python
from core.logger import logger

# Different log levels
logger.debug("Detailed information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical failure")

# With context
logger.info(f"User {user_id} created order {order_id}")
```

### Using Print Debugging

```python
import pdb

def complex_function(data):
    pdb.set_trace()  # Execution pauses here
    result = process(data)
    return result
```

---

## 🗄️ Database Migrations

### Creating Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description"

# Create empty migration
alembic revision -m "description"
```

### Running Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Upgrade to specific version
alembic upgrade +2

# Show current version
alembic current

# Show history
alembic history
```

### Migration Template

```python
"""Add user preferences table

Revision ID: 002_add_user_preferences
Revises: 001_initial_migration
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, nullable=False),
        sa.Column('language', sa.String(10), default='am'),
    )

def downgrade() -> None:
    op.drop_table('user_preferences')
```

---

## 🔌 API Development

### Creating a New Endpoint

```python
# infrastructure/api/v1/endpoints/example.py
from fastapi import APIRouter, Depends
from core.dependencies import get_current_user

router = APIRouter()

@router.get("/example")
async def get_example(
    current_user: dict = Depends(get_current_user),
):
    return {"message": "Hello", "user": current_user}
```

### Registering Router

```python
# infrastructure/api/v1/router.py
from infrastructure.api.v1.endpoints import example

api_router.include_router(
    example.router,
    prefix="/example",
    tags=["example"]
)
```

### Request/Response Models

```python
# apps/example/schemas.py
from pydantic import BaseModel

class ExampleRequest(BaseModel):
    name: str
    age: int = 0

class ExampleResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
```

---

## 🤖 Bot Development

### Creating a Handler

```python
# bot/handlers/example.py
from telegram import Update
from telegram.ext import ContextTypes

async def example_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello from example command!")
```

### Registering Handler

```python
# bot/dispatcher.py
from bot.handlers.example import example_command

application.add_handler(CommandHandler("example", example_command))
```

### Creating Conversation

```python
from telegram.ext import ConversationHandler

# States
SELECTING_OPTION, TYPING = range(2)

async def start(update, context):
    await update.message.reply_text("Choose option:")
    return SELECTING_OPTION

async def handle_option(update, context):
    context.user_data['option'] = update.message.text
    await update.message.reply_text("Type your message:")
    return TYPING

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        SELECTING_OPTION: [MessageHandler(filters.TEXT, handle_option)],
        TYPING: [MessageHandler(filters.TEXT, handle_message)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
```

---

## 🤝 Contributing Guidelines

### Branch Naming

| Branch Type | Format | Example |
|-------------|--------|---------|
| Feature | `feature/description` | `feature/user-profile` |
| Bug Fix | `fix/description` | `fix/payment-error` |
| Hotfix | `hotfix/description` | `hotfix/security-patch` |
| Release | `release/version` | `release/v1.2.0` |

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** feat, fix, docs, style, refactor, test, chore

**Example:**
```
feat(orders): add order cancellation endpoint

- Add cancel_order endpoint
- Add order status validation
- Add tests for cancellation

Closes #123
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with tests
3. Run `make all-checks`
4. Create PR with template
5. Request review
6. Merge after approval

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing done

## Checklist
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] Tests added/updated
```

---

## 🔧 Useful Commands

### Development

```bash
# Run development server
make dev

# Run tests
make test

# Run linters
make lint

# Format code
make format

# Run all checks
make all-checks
```

### Database

```bash
# Create migration
make makemigrations msg="description"

# Run migrations
make migrate

# Rollback
make downgrade

# Seed database
make seed
```

### Docker

```bash
# Start containers
make docker-up

# Stop containers
make docker-down

# View logs
make docker-logs

# Rebuild
make docker-build
```

---

## 📚 Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org)
- [python-telegram-bot Docs](https://python-telegram-bot.org)

### Tools
- [Postman](https://postman.com) - API testing
- [DBeaver](https://dbeaver.io) - Database GUI
- [RedisInsight](https://redis.com/redis-enterprise/redis-insight/) - Redis GUI

---

## ❓ Troubleshooting

### Common Issues

#### Module not found
```bash
pip install -r requirements.txt
```

#### Database connection failed
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify credentials in .env
cat .env | grep DATABASE_URL
```

#### Tests failing
```bash
# Clear cache
pytest --cache-clear

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_api/test_health.py -v
```

#### Git issues
```bash
# Check status
git status

# Undo changes
git checkout -- <file>

# Stash changes
git stash
```

---

**Next:** [Ethiopia Compliance](ethiopia_compliance.md)
```

**ቀጣይ ፋይል #304 ልስጥህ?** "ቀጣይ" በል።