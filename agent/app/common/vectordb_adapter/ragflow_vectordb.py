from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import requests
from agno.knowledge.document import Document
from agno.vectordb.base import VectorDb
from agno.vectordb.search import SearchType


class RagFlowVectorDb(VectorDb):
    """VectorDb adapter backed by RAGFlow retrieval API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        dataset_ids: Optional[List[str]] = None,
        search_id: Optional[str] = None,
        kb_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        metadata_condition: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        similarity_threshold: Optional[float] = None,
    ):
        super().__init__(name="RagFlowVectorDb", similarity_threshold=similarity_threshold)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.dataset_ids = dataset_ids or []
        self.search_id = search_id
        self.kb_id = kb_id
        self.endpoint = endpoint
        self.document_ids = document_ids or []
        self.metadata_condition = metadata_condition
        self.timeout = timeout

    def _use_test_retrieval_api(self) -> bool:
        return bool(self.search_id and self.kb_id)

    def _request_url(self) -> str:
        if self.endpoint:
            return f"{self.base_url}/{self.endpoint.lstrip('/')}"
        if self._use_test_retrieval_api():
            return f"{self.base_url}"
        return f"{self.base_url}"

    def _request_payload(self, query: str, limit: int, filters: Optional[Any]) -> Dict[str, Any]:
        if self._use_test_retrieval_api():
            return {
                "question": query,
                "search_id": self.search_id,
                "kb_id": self.kb_id,
                "size": limit,
            }

        payload: Dict[str, Any] = {"question": query, "dataset_ids": self.dataset_ids, "page": 1, "page_size": limit}
        if self.document_ids:
            payload["document_ids"] = self.document_ids
        if self.metadata_condition:
            payload["metadata_condition"] = self.metadata_condition
        if filters:
            payload["metadata_condition"] = filters
        return payload

    def _request_retrieval(self, query: str, limit: int, filters: Optional[Any]) -> List[Dict[str, Any]]:
        response = requests.post(
            self._request_url(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=self._request_payload(query=query, limit=limit, filters=filters),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code") not in (0, None):
            raise RuntimeError(f"RAGFlow retrieval failed: {payload}")

        return self._extract_chunks_from_payload(payload)

    @staticmethod
    def _extract_chunks_from_payload(payload: Any) -> List[Dict[str, Any]]:
        """Normalize RAGFlow responses: list at top level, list under data, or retrieval_test shape data.chunks."""
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            chunks = data.get("chunks")
            if isinstance(chunks, list):
                return [item for item in chunks if isinstance(item, dict)]
        return []

    @staticmethod
    def _chunk_to_document(chunk: Dict[str, Any]) -> Optional[Document]:
        content = (
            chunk.get("content")
            or chunk.get("content_with_weight")
            or chunk.get("text")
            or chunk.get("chunk")
        )
        if not content:
            return None

        score = chunk.get("similarity") or chunk.get("score") or chunk.get("vector_similarity")
        chunk_id = chunk.get("chunk_id") or chunk.get("id")
        meta_data = {
            "dataset_id": chunk.get("dataset_id"),
            "document_id": chunk.get("document_id") or chunk.get("doc_id"),
            "document_name": chunk.get("document_name") or chunk.get("docnm_kwd"),
            "position": chunk.get("position") or chunk.get("positions"),
            "source": chunk.get("source") or chunk.get("img_id") or chunk.get("image_id"),
        }
        meta_data["raw_chunk"] = chunk

        return Document(
            id=str(chunk_id) if chunk_id is not None else None,
            name=chunk.get("document_name") or chunk.get("docnm_kwd"),
            content=content,
            meta_data=meta_data,
            reranking_score=float(score) if isinstance(score, (int, float)) else None,
        )

    def search(self, query: str, limit: int = 5, filters: Optional[Any] = None) -> List[Document]:
        chunks = self._request_retrieval(query=query, limit=limit, filters=filters)
        documents: List[Document] = []
        for chunk in chunks[:limit]:
            doc = self._chunk_to_document(chunk)
            if doc is None:
                continue
            if self.similarity_threshold is not None and isinstance(doc.reranking_score, float):
                if doc.reranking_score < self.similarity_threshold:
                    continue
            documents.append(doc)
        return documents

    async def async_search(self, query: str, limit: int = 5, filters: Optional[Any] = None) -> List[Document]:
        return await asyncio.to_thread(self.search, query, limit, filters)

    def create(self) -> None:
        return None

    async def async_create(self) -> None:
        return None

    def name_exists(self, name: str) -> bool:
        return name == self.name

    def async_name_exists(self, name: str) -> bool:
        return self.name_exists(name)

    def id_exists(self, id: str) -> bool:
        return id == self.id

    def content_hash_exists(self, content_hash: str) -> bool:
        return False

    def insert(self, content_hash: str, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        return None

    async def async_insert(
        self, content_hash: str, documents: List[Document], filters: Optional[Dict[str, Any]] = None
    ) -> None:
        return None

    def upsert_available(self) -> bool:
        return False

    def upsert(self, content_hash: str, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        return None

    async def async_upsert(
        self, content_hash: str, documents: List[Document], filters: Optional[Dict[str, Any]] = None
    ) -> None:
        return None

    def drop(self) -> None:
        return None

    async def async_drop(self) -> None:
        return None

    def exists(self) -> bool:
        return True

    async def async_exists(self) -> bool:
        return True

    def delete(self) -> bool:
        return False

    def delete_by_id(self, id: str) -> bool:
        return False

    def delete_by_name(self, name: str) -> bool:
        return False

    def delete_by_metadata(self, metadata: Dict[str, Any]) -> bool:
        return False

    def delete_by_content_id(self, content_id: str) -> bool:
        return False

    def get_supported_search_types(self) -> List[str]:
        return [SearchType.vector.value]


