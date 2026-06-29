import asyncio

from devops_resolver.infrastructure.repositories import StaticKnowledgeRepository
from devops_resolver.infrastructure.vector_store import FaissKnowledgeIndex


def test_semantic_search_returns_relevant_runbook() -> None:
    asyncio.run(_assert_semantic_search_returns_relevant_runbook())


async def _assert_semantic_search_returns_relevant_runbook() -> None:
    index = FaissKnowledgeIndex(StaticKnowledgeRepository())

    results = await index.search("postgres no space left on device wal archive", limit=3)

    assert results
    combined = " ".join(result.document.title.lower() for result in results)
    assert "disk" in combined or "postgresql" in combined
