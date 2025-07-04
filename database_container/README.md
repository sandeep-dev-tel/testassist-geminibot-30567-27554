# Database Container for Chatbot Application

Provides PostgreSQL database storage for chatbot backend (FastAPI).

## Tables
- **users**: Stores user authentication data (if enabled)
- **conversations**: Chat sessions per user
- **messages**: Messages within each conversation

## Usage

- Exposed port: **5432**
- Default credentials (change for production):
  - **DB:** chatbotdb
  - **USER:** chatbotuser
  - **PASS:** chatbotpass

## For backend_fastapi integration:

The backend should connect using environment variables, e.g.

```
DB_HOST=database_container
DB_PORT=5432
DB_NAME=chatbotdb
DB_USER=chatbotuser
DB_PASSWORD=chatbotpass
```

## Initialization

On first start, schema is auto-created from `init.sql`.

# 04-07-2025 comment 1