import os
from dotenv import load_dotenv

# Carrega o arquivo .env
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 60))

# --- Logging ---
# LOG_LEVEL vale para o código da aplicação. As libs de terceiro (agno, httpx,
# yfinance) têm o nível próprio, senão o "Found 0 documents" do agno afoga o
# log de verdade.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()  # "text" | "json"
LOG_LEVEL_LIBS = os.getenv("LOG_LEVEL_LIBS", "WARNING").upper()
# Trecho inicial da mensagem do usuário gravado no log. 0 desliga.
LOG_MESSAGE_PREVIEW_CHARS = int(os.getenv("LOG_MESSAGE_PREVIEW_CHARS", 120))

# --- Agente de IA (Agno) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Postgres com pgvector, separado do easy_finace. O Agno cria e gerencia as
# próprias tabelas aqui (sessões, resumos, conteúdos e vetores).
AI_DATABASE_URL = os.getenv(
    "AI_DATABASE_URL", "postgresql+psycopg://agno:agno@localhost:5433/agno_ai"
)

GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-3.5-flash")
GROQ_MODEL_ID = os.getenv("GROQ_MODEL_ID", "openai/gpt-oss-120b")
GROQ_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "medium")
GEMINI_EMBEDDER_ID = os.getenv("GEMINI_EMBEDDER_ID", "gemini-embedding-001")
GEMINI_EMBEDDER_DIMENSIONS = int(os.getenv("GEMINI_EMBEDDER_DIMENSIONS", 1536))

AI_HISTORY_RUNS = int(os.getenv("AI_HISTORY_RUNS", 5))
AI_FALLBACK_COOLDOWN_SECONDS = int(os.getenv("AI_FALLBACK_COOLDOWN_SECONDS", 300))

# Nomes das tabelas/schema que o Agno cria no AI_DATABASE_URL.
AI_DB_SCHEMA = os.getenv("AI_DB_SCHEMA", "ai")
AI_SESSION_TABLE = "ai_sessions"
AI_KNOWLEDGE_TABLE = "ai_knowledge_contents"
AI_VECTOR_TABLE = "ai_vectors"