# TechSprint 2025 - Multilingual Campus Assistant

**Hackathon:** TechSprint - GDGOC 2025
**Track:** EdTech
**Team:** Valo Prophets
**Last Updated:** 2026-01-02
**Status:** ✅ FULLY FUNCTIONAL - Backend, Frontend, Knowledge Base Working

---

## Project Overview

Building a **Language Agnostic AI Chatbot** for educational institutions with:
- Multilingual support (7+ Indian languages: Hindi, English, Gujarati, Marathi, Punjabi, Tamil, Bengali, Telugu, Kannada, Malayalam, Odia)
- FAQ and PDF document ingestion
- RAG-based Q&A with intent recognition
- Human fallback escalation for complex queries
- Web widget interface (embeddable)
- Future: Telegram/WhatsApp integration

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.13) |
| Frontend | Next.js 14 (App Router) |
| Database | SQLite |
| Vector Store | ChromaDB |
| Embeddings | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| LLM | Google Gemini (gemini-1.5-flash-latest) |
| Translation | deep-translator (FREE - no API key needed) |
| RAG Pipeline | LangChain |

---

## Current Status ✅

### Backend: RUNNING
- FastAPI server on http://localhost:8000
- All endpoints functional
- Database initialized with 8 tables

### Frontend: RUNNING
- Next.js app on http://localhost:3000
- Chat widget working
- Admin dashboard accessible

### Knowledge Base: POPULATED
- **29 FAQs** loaded and indexed
- **14 categories** covered (admission, fees, scholarship, hostel, examination, placement, documents, contact, grievance, general, library, transport, activities, facilities)
- **2 languages** (English: 21, Hindi: 8)
- Vector store indexed for semantic search

### Chatbot: WORKING
- Confidence scores: 38-82% (up from 30%)
- Hindi queries working ("Hostel facility ke baare mein batao")
- English queries working ("What is the hostel fee structure?")
- Intent detection working (admission, fees, hostel, contact, etc.)

---

## What Was Completed

### 1. Backend (FastAPI) - DONE ✅
- **Location:** `F:\Sahaj\Projects\SIH\backend`
- **Port:** 8000
- **Features:**
  - Chat API with session management
  - FAQ CRUD operations + bulk import + reindex
  - Document upload and processing (PDF, DOCX, TXT)
  - Vector store for semantic search (ChromaDB)
  - LLM integration with RAG (Gemini)
  - Translation service (free, no API keys)
  - Admin endpoints for analytics

### 2. Frontend (Next.js) - DONE ✅
- **Location:** `F:\Sahaj\Projects\SIH\frontend`
- **Port:** 3000
- **Features:**
  - Chat widget component
  - Admin dashboard (FAQs, Documents, Analytics)
  - Multilingual UI
  - Responsive design with Tailwind CSS

### 3. Database Schema - DONE ✅
Tables created automatically on startup:
- `users` - User tracking
- `sessions` - Chat sessions
- `messages` - Conversation messages
- `faqs` - FAQ entries (29 loaded)
- `documents` - Uploaded documents
- `escalations` - Human escalation requests
- `conversation_logs` - Analytics data
- `feedback` - User feedback

### 4. Knowledge Base - DONE ✅
- Created `create_seed_faqs.py` to generate FAQ data
- Created `load_faqs.py` to load FAQs via API
- Generated `seed_faqs.json` with 29 FAQs
- All FAQs indexed in ChromaDB vector store

### 5. Configuration Files - DONE ✅
- `.env` file created from `.env.example`
- Data directories created (`data/uploads`, `data/chroma_db`)

---

## Issues Encountered & Solutions

### Issue 1: LangChain Import Errors
**Error:** `ModuleNotFoundError: No module named 'langchain.text_splitter'`

**Solution:** Updated imports to use new LangChain package structure:
```python
# OLD (deprecated)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# NEW (working)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangchainDocument
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
```

**Files Fixed:**
- `backend/app/services/document_processor.py`
- `backend/app/services/vector_store.py`
- `backend/app/services/llm_service.py`

### Issue 2: Frontend Memory Crash
**Error:** `RangeError: Array buffer allocation failed`

**Cause:** Low system RAM (81% of 12GB used during dev mode)

**Solution:** Use production build instead of dev mode:
```bash
cd frontend
npm run build
npm start
```

### Issue 3: Port Conflicts
**Error:** `EADDRINUSE: address already in use :::3000`

**Solution:** Kill the process using the port:
```bash
# Find process
netstat -ano | findstr :3000

# Kill it
taskkill /F /PID <process_id>
```

### Issue 4: Gemini Model Not Found
**Error:** `404 NOT_FOUND: models/gemini-1.5-flash is not found`

**Solution:** Changed model to `gemini-1.5-flash-latest` in `llm_service.py:62`

### Issue 5: Gemini Rate Limits
**Error:** `429 RESOURCE_EXHAUSTED: Quota exceeded`

**Solution:** Using `gemini-1.5-flash-latest` which has better free tier availability. May need to wait or upgrade API quota.

### Issue 6: No Translation API Keys
**Problem:** User doesn't have Google Translate API or Bhashini API keys

**Solution:** Rewrote translation service to use `deep-translator` library:
- FREE - no API keys required
- Uses Google Translate under the hood
- Supports all required languages

### Issue 7: ChromaDB Singleton Conflict (NEW)
**Error:** `An instance of Chroma already exists for data\chroma with different settings`

**Solution:** Modified `vector_store.py` to use shared client instance:
```python
# OLD (conflicting)
self._vectorstore = Chroma(
    persist_directory=str(self.persist_directory),
)

# NEW (fixed)
self._vectorstore = Chroma(
    client=self._get_client(),  # Use shared client
)
```

### Issue 8: FAQs Not Indexed in Vector Store (NEW)
**Problem:** FAQs were in SQLite but not indexed in ChromaDB

**Solution:** Called the reindex endpoint:
```bash
curl -X POST "http://localhost:8000/api/v1/faqs/reindex"
# Response: {"indexed": 29}
```

---

## Configuration

### Environment Variables (backend/.env)
```env
# App Configuration
APP_NAME=Campus Assistant
DEBUG=true
SECRET_KEY=your-super-secret-key-change-in-production

# Database
DATABASE_URL=sqlite:///./campus_assistant.db

# LLM Configuration
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your-google-api-key-here  # REQUIRED

# Vector Store
CHROMA_PERSIST_DIRECTORY=./data/chroma_db
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Translation - NO API KEYS NEEDED (uses deep-translator)
```

### Admin Credentials
- **Username:** `admin`
- **Password:** `admin123`
- **Note:** Change these in production! (defined in `backend/app/core/config.py`)

---

## How to Run

### Prerequisites:
- Python 3.13+
- Node.js 18+
- Google API Key (for Gemini)

### Start Backend:
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Load FAQs (first time only):
```bash
cd backend
python create_seed_faqs.py  # Creates seed_faqs.json
python load_faqs.py         # Loads FAQs via API
```

### Reindex FAQs (if needed):
```bash
curl -X POST "http://localhost:8000/api/v1/faqs/reindex"
```

### Start Frontend:
```bash
cd frontend
npm install
npm run build  # Build for production (less memory)
npm start      # Run on port 3000
```

### Access Points:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Admin Panel:** http://localhost:3000/admin

---

## File Structure

```
F:\Sahaj\Projects\SIH\
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── chat.py         # Chat endpoints
│   │   │   ├── faqs.py         # FAQ CRUD + reindex
│   │   │   ├── documents.py    # Document upload
│   │   │   └── admin.py        # Admin endpoints
│   │   ├── core/
│   │   │   ├── config.py       # Settings (admin credentials)
│   │   │   └── database.py     # SQLite setup
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/
│   │       ├── chat_service.py       # Main chat logic
│   │       ├── chatbot_engine.py     # RAG orchestration
│   │       ├── llm_service.py        # Gemini integration
│   │       ├── vector_store.py       # ChromaDB (fixed)
│   │       ├── document_processor.py # PDF/DOCX processing
│   │       └── translation.py        # Free translation
│   ├── data/
│   │   ├── uploads/            # Uploaded documents
│   │   └── chroma_db/          # Vector store data
│   ├── create_seed_faqs.py     # FAQ generator script
│   ├── load_faqs.py            # FAQ loader script
│   ├── seed_faqs.json          # 29 sample FAQs
│   ├── .env                    # Environment variables
│   ├── requirements.txt        # Python dependencies
│   └── campus_assistant.db     # SQLite database
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Home page
│   │   │   └── admin/          # Admin dashboard
│   │   ├── components/
│   │   │   ├── ChatWidget.tsx  # Chat component
│   │   │   └── ...
│   │   └── lib/
│   │       └── api.ts          # API client
│   ├── package.json
│   └── next.config.js
├── PROGRESS.md                 # This file
└── README.md                   # Project documentation
```

---

## FAQ Categories Loaded

| Category | Count | Sample Question |
|----------|-------|-----------------|
| admission | 5 | What are the admission requirements for B.Tech? |
| fees | 4 | What is the fee structure for engineering courses? |
| scholarship | 2 | What scholarships are available for students? |
| hostel | 2 | How to apply for hostel accommodation? |
| examination | 2 | What is the examination pattern? |
| placement | 2 | What are the placement opportunities? |
| documents | 2 | How to get bonafide certificate? |
| contact | 1 | What are the contact details for departments? |
| grievance | 2 | What are the anti-ragging rules? |
| general | 2 | What are the college timings? |
| library | 1 | How to access library resources? |
| transport | 1 | Is there bus facility for students? |
| activities | 1 | What extracurricular activities are available? |
| facilities | 1 | Wi-Fi aur computer lab kaise access karein? |

---

## Known Warnings (Non-Critical)

1. **LangChain Deprecation Warnings:**
   - `HuggingFaceEmbeddings` deprecated - upgrade to `langchain-huggingface`
   - `Chroma` deprecated - upgrade to `langchain-chroma`
   - These work but should be updated for future compatibility

2. **Relevance Score Warnings:**
   - Some scores are negative - this is a ChromaDB normalization issue
   - Does not affect functionality

---

## Next Steps (TODO)

### Immediate (Priority 1):
1. ✅ ~~Add FAQs to Knowledge Base~~ - DONE (29 FAQs)
2. ✅ ~~Test the Chatbot~~ - DONE (Working)
3. ⬜ Upload PDF documents with college information
4. ⬜ Add more FAQs for better coverage

### Security Improvements (Priority 2):
5. ⬜ Change default admin credentials
6. ⬜ Add rate limiting to prevent abuse
7. ⬜ Implement proper authentication (JWT)
8. ⬜ Add CORS configuration for production

### Feature Enhancements (Priority 3):
9. ⬜ Telegram Integration
   - Add Telegram bot token to `.env`
   - Implement webhook handlers
10. ⬜ WhatsApp Integration
    - Set up Twilio/WhatsApp Business API
    - Add webhook handlers
11. ⬜ Voice Support
    - Add speech-to-text (Whisper API)
    - Add text-to-speech

### Performance (Priority 4):
12. ⬜ Upgrade deprecated LangChain packages
13. ⬜ Add database indexes for better query performance
14. ⬜ Implement caching for frequent queries

---

## Notes

1. **Translation is FREE** - No API keys needed, uses deep-translator
2. **Gemini may rate limit** - Free tier has quotas, wait or upgrade if needed
3. **Use production build for frontend** - Dev mode uses too much RAM
4. **Reindex after adding FAQs** - Call `/api/v1/faqs/reindex` if new FAQs don't appear in search

---

## Contact / Support

**Team Valo Prophets** - TechSprint 2025 - GDGOC Hackathon

GitHub: [@sizwinz](https://github.com/sizwinz)
Email: sahajitaliya33@gmail.com
