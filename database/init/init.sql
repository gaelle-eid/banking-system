-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable vector similarity search (for AI knowledge base / RAG)
CREATE EXTENSION IF NOT EXISTS vector;