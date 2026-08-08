from pydantic_ai import Embedder

embedder = Embedder("gateway/openai:text-embedding-3-small")


async def get_embedding(text: str) -> list[float]:
    """Get an embedding vector for a piece of text via the Pydantic AI Gateway."""
    result = await embedder.embed(text, input_type="document")
    return result.embeddings[0]


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]



async def search_similar_chunks(db, query: str, limit: int = 3):
    """Find the most relevant knowledge chunks for a query using vector similarity."""
    from sqlalchemy import select
    from app.models.models import KnowledgeChunk, KnowledgeDocument

    query_embedding = await get_embedding(query)

    result = await db.execute(
        select(KnowledgeChunk, KnowledgeDocument.title)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(KnowledgeChunk.embedding.isnot(None))
        .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    return result.all()