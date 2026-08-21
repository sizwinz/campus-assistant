# Campus Assistant

> Multilingual AI Helpdesk and Knowledge Base for Educational Institutions  
> **TechSprint 2025 - GDGOC Hackathon** | Track: EdTech | Team: Valo Prophets

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-FF6F00?style=flat)](https://www.trychroma.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Campus Assistant is a language-agnostic AI chatbot designed for universities and colleges. It resolves student inquiries in 7+ Indian regional languages, including Hindi, English, Gujarati, Marathi, Punjabi, Tamil, and Rajasthani, using Retrieval-Augmented Generation (RAG) powered by Google Gemini and ChromaDB.

---

## Overview

Educational administration offices routinely process high volumes of repetitive inquiries regarding admission dates, fee structures, scholarship criteria, and exam schedules. Many students communicate more naturally in regional languages. Campus Assistant automates these interactions, providing real-time, verified answers while routing complex grievances to staff.

### Core Highlights

- **Retrieval Augmented Generation (RAG)**: Combines structured FAQ data and ingested institutional documents with vector search for factual responses.
- **Multilingual Pipeline**: Supports automatic language detection and translation across 7+ regional languages with zero API costs via deep-translator.
- **Google Gemini Integration**: Uses Google Gemini (gemini-2.0-flash / gemini-2.5-flash) for contextual dialogue, intent detection, and follow-up suggestion generation.
- **Full Administrative Control**: Web dashboard for analytics, conversation monitoring, document uploads, and real-time FAQ vector reindexing.
- **Lightweight & Containerized**: Ready for production deployment with Docker Compose, SQLite (dev), and PostgreSQL (prod).

---

## Screenshots

### Chat Interface
![Chat Interface](images/chat-panel.png)

### Admin Dashboard
![Admin Dashboard](images/admin-panel.png)

---

## System Architecture

```
+-------------------------------------------------------------------------+
|                              CLIENT LAYER                               |
+-------------------+-------------------+----------------+----------------+
|     Web App       |   Telegram Bot    | Admin Console  | Campus Portal  |
|    (Next.js 14)   |  (Python Bot API) |  (TailwindCSS) |   (Embeddable) |
+-------------------+-------------------+----------------+----------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                          API GATEWAY (FastAPI)                          |
+-------------------------------------------------------------------------+
                                    |
            +-----------------------+-----------------------+
            v                       v                       v
+-----------------------+ +-------------------+ +-----------------------+
|  Language Processing  | | Intent & Retrieval| |  Session Management   |
| (Detection/Translate) | |  (LangChain + RAG)| |    (Async SQLite/PG)  |
+-----------------------+ +-------------------+ +-----------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                             KNOWLEDGE BASE                              |
+-----------------------+-----------------------+-------------------------+
|     Document Store    |       Vector DB       |      FAQ Database       |
|    (PDF, DOCX Text)   |   (ChromaDB + ST-v2)  |   (Relational Tables)   |
+-----------------------+-----------------------+-------------------------+
```

### Request Lifecycle

1. **Input & Detection**: The user submits a query in any supported language.
2. **Translation & Normalization**: Non-English queries are translated to English for vector search.
3. **Contextual Retrieval**: Semantic embeddings (`paraphrase-multilingual-MiniLM-L12-v2`) match relevant documents and FAQs in ChromaDB.
4. **LLM Generation**: Google Gemini generates a factual response utilizing the retrieved context and session history.
5. **Localization**: The response and suggested follow-up questions are translated back to the user preference.
6. **Persistence & Telemetry**: Conversation turns, confidence scores, and intents are logged for administrative analytics.

---

## Tech Stack

| Layer | Technology | Details |
|---|---|---|
| **Backend Framework** | FastAPI | Async REST API, Pydantic v2 validation, SlowAPI rate limiting |
| **Frontend Framework** | Next.js 14 | React 18, Tailwind CSS, Lucide icons, Responsive UI |
| **LLM Provider** | Google Gemini / OpenAI | Configurable via `LLM_PROVIDER` and `LLM_MODEL` |
| **Vector Database** | ChromaDB | Local persistent vector storage with cosine similarity |
| **Embeddings** | Sentence Transformers | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| **RAG Framework** | LangChain | Document loaders, recursive character splitters, prompt templates |
| **Translation** | deep-translator | Direct Google Translate integration (no API key required) |
| **Primary Database** | SQLite / PostgreSQL | Async SQLAlchemy 2.0 with Alembic schema migrations |

---

## Supported Languages

| Code | Language | Native Script | Translation Provider |
|---|---|---|---|
| `en` | English | English | Native |
| `hi` | Hindi | हिन्दी | Google Translate / Bhashini |
| `gu` | Gujarati | ગુજરાતી | Google Translate / Bhashini |
| `mr` | Marathi | मराठी | Google Translate / Bhashini |
| `pa` | Punjabi | ਪੰਜਾਬੀ | Google Translate / Bhashini |
| `ta` | Tamil | தமிழ் | Google Translate / Bhashini |
| `raj` | Rajasthani | राजस्थानी | Hindi fallback |

---

## Getting Started

### Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18.x or higher
- **Package Managers**: `pip` (or `uv`), `npm`
- **Google AI API Key**: (Optional, for full Gemini LLM generation) [Get a free key](https://aistudio.google.com/app/apikey)

---

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to configure `GOOGLE_API_KEY`, `SECRET_KEY`, and admin credentials.*

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the API server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install packages**:
   ```bash
   npm install
   ```

3. **Configure environment variables**:
   ```bash
   echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
   ```

4. **Start the development server**:
   ```bash
   npm run dev
   ```
   *For production builds, run `npm run build && npm start`.*

---

### Seed Knowledge Base

With the backend running, populate the database and vector store with sample campus FAQs:

```bash
cd backend
python load_faqs.py --username admin --password dev-password-change-me
```

---

## Application URLs

| Service | URL | Default Credentials |
|---|---|---|
| **Web Chatbot** | [http://localhost:3000](http://localhost:3000) | Public |
| **Admin Dashboard** | [http://localhost:3000/admin](http://localhost:3000/admin) | `admin` / `dev-password-change-me` |
| **API Documentation** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger UI |
| **Health Check** | [http://localhost:8000/health](http://localhost:8000/health) | Public |

---

## Configuration Reference

Key variables available in `backend/.env`:

| Key | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Environment mode (`development`, `staging`, `production`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/chatbot.db` | Async database connection string |
| `SECRET_KEY` | `CHANGE-THIS-IN-PRODUCTION` | Cryptographic secret for signing tokens |
| `ADMIN_USERNAME` | `admin` | Admin dashboard username |
| `ADMIN_PASSWORD_HASH` | Dev fallback | Bcrypt hash for admin password authentication |
| `LLM_PROVIDER` | `gemini` | LLM backend (`gemini` or `openai`) |
| `GOOGLE_API_KEY` | `None` | Google Gemini Studio API key |
| `LLM_MODEL` | `gemini-2.0-flash` | Model identifier |
| `CHROMA_PERSIST_DIRECTORY` | `./data/chroma` | Persistence directory for vector embeddings |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Allowed client origins |
| `RATE_LIMIT_REQUESTS` | `60` | Requests allowed per rate limit window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Duration of rate limiting window in seconds |
| `TELEGRAM_BOT_TOKEN` | `None` | Optional Telegram bot token from @BotFather |
| `PUBLIC_BASE_URL` | `None` | Public HTTPS URL for Telegram webhook callbacks |

---

## API Summary

### Chat Endpoints
- `POST /api/v1/chat/`: Submit a user question and receive a context-aware answer.
- `GET /api/v1/chat/welcome`: Retrieve localized introductory greetings.
- `GET /api/v1/chat/languages`: List available languages and codes.
- `POST /api/v1/chat/detect-language`: Detect the language of a submitted string.

### Knowledge Management (Admin Auth Required)
- `GET /api/v1/faqs/`: Query all FAQs with category and language filters.
- `POST /api/v1/faqs/`: Add a single FAQ record and index in vector store.
- `POST /api/v1/faqs/bulk-import`: Ingest a JSON array of FAQ records.
- `POST /api/v1/faqs/reindex`: Rebuild all vector embeddings from current FAQs.
- `PUT /api/v1/faqs/{id}`: Modify an existing FAQ.
- `DELETE /api/v1/faqs/{id}`: Remove an FAQ and delete its vector embedding.

### Document Management (Admin Auth Required)
- `GET /api/v1/documents/`: List all ingested circulars and documents.
- `POST /api/v1/documents/upload`: Upload PDF or DOCX institutional files.
- `POST /api/v1/documents/{id}/index`: Parse, split, and vectorize an uploaded document.
- `DELETE /api/v1/documents/{id}`: Delete a document and clear its vector entries.

### Admin & Telemetry (Admin Auth Required)
- `GET /api/v1/admin/dashboard`: Metrics on sessions, messages, escalations, and average confidence.
- `GET /api/v1/admin/analytics`: Historical daily message volume and language distribution.
- `GET /api/v1/admin/conversations`: Filterable conversation logs and user feedback.
- `GET /api/v1/admin/health`: System health status and dependency checks.

---

## Deployment

### Docker Compose (Recommended)

Run both the frontend and backend services in isolated containers:

```bash
# Build images and start services in detached mode
docker-compose up -d --build

# Inspect logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Checklist

1. Deploy with PostgreSQL using `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname`.
2. Generate a secure secret key:
   ```bash
   python -m app.cli generate-secret
   ```
3. Generate a secure admin password hash:
   ```bash
   python -m app.cli hash-password
   ```
4. Set `ENVIRONMENT=production` and specify explicit domains in `CORS_ORIGINS`.
5. Schema migrations run automatically on container startup via `alembic upgrade head`.

---

## Testing

### Backend Test Suite
```bash
cd backend
python -m pytest tests -v
```

### Frontend Test Suite
```bash
cd frontend
npm test
```

---

## Telegram Integration (Optional)

1. Obtain a bot token from [@BotFather](https://t.me/botfather).
2. Set `TELEGRAM_BOT_TOKEN=your_token` in `backend/.env`.
3. Set `PUBLIC_BASE_URL=https://your-domain.example` to your public HTTPS endpoint.
4. Register the webhook with admin credentials:
   ```bash
   curl -u admin:<password> "https://your-domain.example/api/v1/telegram/setup"
   ```

---

## License

This project is open source and distributed under the [MIT License](LICENSE).

---

## Team

Developed for **TechSprint 2025 - GDGOC Hackathon** by **Team Valo Prophets**:

- Sahaj Italiya ([@sizwinz](https://github.com/sizwinz))
- Divy Viradiya ([@divyviradiya2](https://github.com/divyviradiya2))\n