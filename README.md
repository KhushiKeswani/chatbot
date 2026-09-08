# Chatbot API

An asynchronous FastAPI backend for a conversational AI assistant, powered by Google Gemini, backed by SQLAlchemy with SQLite, secured with JWT-based authentication, and accelerated with a Redis caching layer.

The codebase follows a **repository/service layered architecture**, separating routing, business logic, and data access for modularity and testability.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Key Design Decisions](#key-design-decisions)
- [Load Testing Results](#load-testing-results)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Tech Stack](#tech-stack)
- [Known Limitations & Next Steps](#known-limitations--next-steps)
- [License](#license)

## Features

- **Authentication** — signup and login with bcrypt password hashing (via passlib) and JWT access tokens (python-jose)
- **Conversation persistence** — conversations and messages stored per user via async SQLAlchemy ORM
- **LLM integration** — chat messages answered through a dedicated Gemini service layer (google-genai, model: gemini-3.5-flash)
- **Response caching** — normalized prompts cached in Redis with 1-hour expiration; graceful degradation if Redis is unavailable
- **Layered architecture** — routes → repositories → models; services and utilities isolated from routing logic
- **Structured logging** across authentication, chat, and history flows
- **Async/await throughout** — all database and I/O operations are non-blocking
- **Containerized** via multi-stage Dockerfile with minimal image size

## Architecture

### High-level flow

```
Client
  |
  v
FastAPI (bot.py)
  |
  |-- POST /signup, /login  →  Userrepository  →  User model
  |-- POST /convo            →  Conversationrepository
  `-- POST /chat             →  Conversationrepository + Messagerepository
                                      |
                                      |-- Redis cache lookup (hit → return cached response)
                                      |
                                      `-- Geminiservice → Google Gemini API
                                             |
                                             `-- Response cached (Redis) and persisted (DB)
```

### Project structure

```
chatbot/
├── bot.py                      # FastAPI app, lifespan startup, route definitions
├── models.py                   # SQLAlchemy models: User, Conversation, Message
├── database.py                 # Async engine/session setup, init_db, get_db
├── repositories/               # Data access layer
│   ├── user_repositories.py
│   ├── conversation_repositories.py
│   └── message_repositories.py
├── services/
│   ├── llm_services.py         # Geminiservice — Google Gemini integration
│   └── redis_service.py        # Cache operations: get/set normalized keys
├── utils/
│   ├── security.py             # JWT token creation and verification
│   ├── password.py             # Password hashing and verification
│   ├── auth.py                 # get_current_user dependency injection
│   └── logger.py               # Structured logging
├── tests/                      # pytest / pytest-asyncio test suite
├── .github/workflows/          # CI/CD configuration
├── Dockerfile
├── requirements.txt
└── README.md
```

## Key Design Decisions

### 1. Lifespan context manager defers Gemini initialization

**Why:** The Gemini client (`genai.Client`) is expensive to initialize. Initializing it inside the FastAPI lifespan (lines 19–31 in `bot.py`) ensures:
- It runs once at startup, not per request
- The event loop is ready and stable before making any calls
- Errors during initialization fail fast before traffic arrives
- It's cleanly stored in `app.state.gemini` and injected via `get_gemini()` dependency

Without this deferred init, each request might reinitialize the client or encounter timing issues.

### 2. Password hashing runs via `asyncio.to_thread()`

**Why:** Bcrypt password hashing is CPU-bound and blocks the event loop. Lines 61 and 85 in `bot.py` use `asyncio.to_thread()` to:
- Offload the blocking bcrypt computation to a thread pool
- Keep the event loop responsive for other concurrent requests
- Maintain async/await semantics without callbacks

Without this, signup/login endpoints would stall the entire server during hash operations under load.

### 3. Redis cache failures degrade gracefully

**Why:** Redis is optional for correctness—the application must work (slowly) without it. Lines 118–145 in `bot.py` catch Redis exceptions and:
- Log a warning instead of crashing
- Continue to the Gemini API if cache is unavailable
- Still persist the response to the database
- Return the correct result to the user

This trade-off prioritizes **availability** over **performance**. If Redis is down, users get slower responses instead of 500 errors.

## Load Testing Results

### Test Setup

Using Locust, a Python-based load testing framework, the `/chat` endpoint was tested under concurrent load. Results captured from the Locust web dashboard.

### Verified Metrics (from Locust screenshot)

| Metric                  | Value      |
|-------------------------|------------|
| **Requests per second** | 42.5 req/s |
| **Median latency (p50)**| 110 ms     |
| **Success rate**        | 99.86%     |
| **Failure rate**        | 0.1%       |

**Interpretation:**
- **42.5 req/s throughput** reflects external API latency (Gemini calls are inherently slow); subsequent identical queries benefit from Redis caching.
- **110 ms median latency** includes both cache hits and Gemini API calls; the median suggests typical cache-hit behavior.
- **99.86% reliability** demonstrates robust error handling and graceful Redis degradation under load.

To reproduce these results, configure and run Locust against a live deployment with similar network and Gemini API rate-limit conditions.

## Getting Started

### Prerequisites

- Python 3.11 or later
- A Google Gemini API key
- Redis (optional; the service degrades gracefully without it)
- Docker (optional)

### Installation

```bash
git clone https://github.com/KhushiKeswani/chatbot.git
cd chatbot
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root with these variables:

```env
# Google Gemini API
GEMINI_API_KEY=your_google_gemini_api_key

# JWT configuration
SECRET_KEY=your_jwt_secret_key_min_32_chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Redis configuration:** The app connects to Redis at `localhost:6379` by default. To use a different host/port, update `services/redis_service.py` lines 3–6. If Redis is unavailable, the app continues without caching—no configuration needed.

### Running locally

```bash
fastapi dev bot.py
```

The API is available at `http://127.0.0.1:8000`, with interactive Swagger documentation at `http://127.0.0.1:8000/docs`.

### Running with Docker

```bash
docker build -t chatbot .
docker run -p 8000:8000 --env-file .env chatbot
```

Ensure Redis is running separately (e.g., `docker run -d -p 6379:6379 redis:latest`) or remove it from your environment.

## API Reference

| Method | Endpoint               | Auth | Description                                    |
|--------|------------------------|----- |-------------------------------------------------|
| POST   | `/signup`              | No   | Create a new user account with email and password |
| POST   | `/login`               | No   | Authenticate and receive a JWT access token      |
| POST   | `/convo`               | Yes  | Start a new conversation                          |
| POST   | `/chat`                | Yes  | Send a message and receive a Gemini-generated reply; results cached |
| GET    | `/history/{convo_id}`  | Yes  | Retrieve full message history for a conversation  |

### Authentication

Authenticated endpoints require a bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are issued by `/login` and expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 30 minutes).

### Example workflow

```bash
# 1. Sign up
curl -X POST http://127.0.0.1:8000/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# 2. Login
curl -X POST http://127.0.0.1:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'
# Response: {"accesstoken": "eyJ0...", "token_type": "bearer"}

# 3. Create conversation
curl -X POST http://127.0.0.1:8000/convo \
  -H "Authorization: Bearer eyJ0..."
# Response: {"convo_id": 1}

# 4. Send a message
curl -X POST http://127.0.0.1:8000/chat \
  -H "Authorization: Bearer eyJ0..." \
  -H "Content-Type: application/json" \
  -d '{"convo_id": 1, "message": "What is machine learning?"}'
# Response: {"response": "Machine learning is..."}

# 5. Retrieve history
curl -X GET http://127.0.0.1:8000/history/1 \
  -H "Authorization: Bearer eyJ0..."
# Response: [{"role": "user", "content": "What is machine learning?"}, {"role": "assistant", "content": "..."}]
```

## Tech Stack

| Layer               | Technology                                  |
|---------------------|---------------------------------------------|
| **API framework**   | FastAPI, Uvicorn                            |
| **Language model**  | Google Gemini (google-genai, gemini-3.5-flash) |
| **Database**        | SQLAlchemy (async), SQLite (aiosqlite)      |
| **Caching**         | Redis                                       |
| **Authentication**  | python-jose (JWT), passlib/bcrypt           |
| **Validation**      | Pydantic                                    |
| **Testing**         | pytest, pytest-asyncio                      |
| **Containerization**| Docker (multi-stage)                        |
| **Logging**         | Python standard logging                     |

## Known Limitations & Next Steps

### Current limitations

- **Streaming responses** — responses are returned as complete text; SSE or WebSocket support would enable real-time token streaming.
- **No refresh tokens** — access tokens expire after 30 minutes; users must re-login.
- **No conversation search** — no conversation titles or full-text search; all queries go into one long history.
- **No rate limiting** — no per-user request throttling; a single user can hammer the `/chat` endpoint.
- **Single-instance only** — designed for local or single-server deployment; multi-instance setups would need a shared database and distributed session store.
- **SQLite only** — suitable for development; production should use PostgreSQL with a connection pool.
- **Redis hardcoded to localhost** — to change the host/port, edit `services/redis_service.py` directly (future: read from env).

### Roadmap

- [ ] Server-Sent Events (SSE) for streaming Gemini responses
- [ ] Conversation titles and full-text search
- [ ] Per-user rate limiting (sliding window or token bucket)
- [ ] Refresh token support for longer sessions
- [ ] PostgreSQL support for production deployments
- [ ] Docker Compose with Redis and optional PostgreSQL
- [ ] Redis configuration via environment variables
- [ ] OpenTelemetry instrumentation for observability
- [ ] Multi-turn conversation context management (sliding window for large histories)

## License

Licensed under the MIT License. See [LICENSE](./LICENSE) for details.
