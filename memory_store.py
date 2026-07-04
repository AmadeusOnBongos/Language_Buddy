import uuid
from datetime import datetime, timezone
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from config import settings


class MemoryStore:
    def __init__(self):
        self.embedder = SentenceTransformer(settings.embedding_model)
        self.client = chromadb.PersistentClient(
            path="./chroma_data",
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.rag_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_exchange(
        self,
        user_message: str,
        bot_response: str,
        topic: Optional[str] = None,
    ) -> str:
        entry_id = str(uuid.uuid4())
        text = f"User: {user_message}\nBot: {bot_response}"
        metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "topic": topic or "general",
            "user_message": user_message,
            "bot_response": bot_response,
        }
        embedding = self.embedder.encode(text).tolist()
        self.collection.add(
            ids=[entry_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
        return entry_id

    def search_similar(
        self,
        query: str,
        k: Optional[int] = None,
    ) -> list[dict]:
        k = k or settings.rag_top_k
        query_embedding = self.embedder.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
        )
        entries = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                entries.append({
                    "id": doc_id,
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })
        return entries

    def get_recent_exchanges(self, limit: int = 10) -> list[dict]:
        all_data = self.collection.get(limit=limit)
        entries = []
        if all_data["ids"]:
            sorted_pairs = sorted(
                zip(all_data["ids"], all_data["documents"], all_data["metadatas"]),
                key=lambda x: x[2].get("timestamp", ""),
                reverse=True,
            )
            for doc_id, doc, meta in sorted_pairs[:limit]:
                entries.append({
                    "id": doc_id,
                    "document": doc,
                    "metadata": meta,
                })
        return entries

    def count(self) -> int:
        return self.collection.count()
