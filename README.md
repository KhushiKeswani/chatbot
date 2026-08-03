# Chatbot API

An asynchronous FastAPI backend for a conversational AI assistant, powered by Google Gemini, backed by SQLAlchemy with SQLite, secured with JWT-based authentication, and accelerated with a Redis response cache.

The codebase follows a repository/service layered architecture, separating routing, business logic, and data access rather than collapsing everything into a single file.

## Overview

Chatbot API provides authenticated, persistent, and cached conversations with a Gemini-backed language model. Each user can create multiple conversations, exchange messages, and retrieve full conversation history. Repeated prompts are served from Redis instead of re-querying the LLM, with a fallback path if the cache is unavailable.

## Features

- **Authentication** — signup and login with bcrypt password hashing (via passlib) and JWT access tokens (python-jose)
- **Conversation persistence** — conversations and messages are stored per user via an async SQLAlchemy ORM
- **LLM integration** — chat messages are answered through a dedicated Gemini service layer
- **Response caching** — normalized prompts are cached in Redis, reducing redundant LLM calls, with graceful degradation if Redis is down
- **Layered architecture** — routes call repositories, repositories operate on models; services and utilities are isolated from route logic
- **Structured logging** across authentication, chat, and history flows
- **Automated tests** using pytest and pytest-asyncio
- **Containerized** via a provided Dockerfile

## Architecture

```
Client
  |
  v
FastAPI (bot.py)
  |
  |-- POST /signup, /login  -->  Userrepository        --> User model
  |-- POST /convo            -->  Conversationrepository
  `-- POST /chat             -->  Conversationrepository + Messagerepository
                                        |
                                        |-- Redis cache lookup (hit -> return cached response)
                                        |
                                        `-- Geminiservice --> Google Gemini API
                                               |
                                               `-- response cached and persisted
```

### Project structure

```
chatbot/
├── bot.py                 FastAPI app, lifespan startup, route definitions
├── models.py               SQLAlchemy models: User, Conversation, Message
├── database.py              Async engine/session setup, init_db, get_db
├── repositories/            Data access layer (user, conversation, message)
├── services/
│   ├── llm_services.py       Geminiservice — Google Gemini integration
│   └── redis_service.py      cache_response / get_cached_response / normalize_key
├── utils/
│   ├── security.py            JWT token creation
│   ├── password.py             Password hashing and verification
│   ├── auth.py                 get_current_user dependency
│   └── logger.py
├── tests/                    pytest / pytest-asyncio test suite
├── .github/workflows/         CI configuration
├── Dockerfile
└── requirements.txt
```

## API Reference

| Method | Endpoint               | Auth | Description                                    |
|--------|-------------------------|:----:|-------------------------------------------------|
| POST   | `/signup`               | No   | Create a new user account                        |
| POST   | `/login`                | No   | Authenticate and receive a JWT access token      |
| POST   | `/convo`                | Yes  | Start a new conversation                          |
| POST   | `/chat`                 | Yes  | Send a message and receive a Gemini-generated reply |
| GET    | `/history/{convo_id}`   | Yes  | Retrieve full message history for a conversation  |

Authenticated requests must include a bearer token:

```
Authorization: Bearer <access_token>
```

## Getting Started

### Prerequisites

- Python 3.11 or later
- A Google Gemini API key
- Redis (recommended; the service degrades gracefully without it)

### Installation

```bash
git clone https://github.com/KhushiKeswani/chatbot.git
cd chatbot
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_google_gemini_api_key
SECRET_KEY=your_jwt_secret_key
REDIS_URL=redis://localhost:6379
```

### Running locally

```bash
fastapi dev bot.py
```

The API is available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

### Running with Docker

```bash
docker build -t chatbot .
docker run -p 8000:8000 --env-file .env chatbot
```

## Testing

```bash
pytest
```

## Tech Stack

| Layer            | Technology                                  |
|-------------------|-----------------------------------------------|
| API framework     | FastAPI, Uvicorn                              |
| Language model    | Google Gemini (google-genai)                  |
| Database          | SQLAlchemy (async), SQLite (aiosqlite)        |
| Caching           | Redis                                          |
| Authentication    | python-jose (JWT), passlib/bcrypt             |
| Validation        | Pydantic                                       |
| Testing           | pytest, pytest-asyncio                        |
| Containerization  | Docker                                         |

## Roadmap

- Streaming responses (SSE or WebSockets)
- Conversation titles and search
- Per-user rate limiting
- Refresh token support
- PostgreSQL support for production deployments

## License

Licensed under the MIT License. See [LICENSE](./LICENSE) for details.
