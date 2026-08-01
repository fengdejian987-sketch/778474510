# Architecture diagram (textual)

The system is composed of these main layers:

- API (FastAPI)
  - Exposes endpoints for formula generation, retrieval, derivation

- Services
  - FormulaService: business logic to manage formulas
  - DimensionValidator: validates dimensional consistency

- Core
  - quantity.py, formula.py, dimension.py, library.py
  - encapsulates domain objects and symbolic manipulation

- Models (ML)
  - seq2seq model for formula generation

- Database
  - SQLAlchemy ORM models (formulas, quantities, derivations)
  - session factory and migrations

- DevOps
  - Dockerfile, docker-compose for local development
  - CI: pre-commit detect-secrets, secret-scan workflow

ASCII diagram:

```
+-------------------+          +----------------------+         +----------------+
|   Client / UI     | <------> |      API (FastAPI)   | <-----> |  ML Model (seq2seq) |
+-------------------+          +----------------------+         +----------------+
                                      |      ^
                                      |      |
                                      v      |
                               +--------------------+
                               | Services (business)|
                               +--------------------+
                                      |      |
                    +-----------------+      +----------------+
                    |                                     |
         +--------------------+               +-----------------------+
         |  Core (domain)     |               |   Database (Postgres) |
         | formula/dimension  |               |  SQLAlchemy ORM       |
         +--------------------+               +-----------------------+


```

Notes:
- Use environment variables for all sensitive config (DATABASE_URL, secrets).
- Add CI scanning to detect accidental secrets.
