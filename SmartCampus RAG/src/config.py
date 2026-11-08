import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do .env na raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Configurações do MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "smartcampus_rag")

# Configurações do Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# Configurações do ChromaDB
CHROMA_PERSIST_DIRECTORY = str(BASE_DIR / os.getenv("CHROMA_PERSIST_DIRECTORY", "chromadb_data"))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "academic_docs")

# Diretório para documentos acadêmicos
DATA_DIR = str(BASE_DIR / "data")
