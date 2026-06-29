import asyncio

from devops_resolver.domain.models import ToolName
from devops_resolver.infrastructure.repositories import StaticKnowledgeRepository
from devops_resolver.infrastructure.tool_layer import ToolLayer
from devops_resolver.infrastructure.vector_store import FaissKnowledgeIndex
from devops_resolver.shared.config import get_settings


def test_tool_layer_refuses_destructive_commands() -> None:
    asyncio.run(_assert_tool_layer_refuses_destructive_commands())


async def _assert_tool_layer_refuses_destructive_commands() -> None:
    knowledge = StaticKnowledgeRepository()
    tool_layer = ToolLayer(get_settings(), knowledge, FaissKnowledgeIndex(knowledge))

    result = await tool_layer.execute(ToolName.linux_command, "rm -rf /", demo_key="disk-full")

    assert not result.success
    assert "Refusing destructive command" in result.output


def test_tool_layer_reads_demo_logs() -> None:
    asyncio.run(_assert_tool_layer_reads_demo_logs())


async def _assert_tool_layer_reads_demo_logs() -> None:
    knowledge = StaticKnowledgeRepository()
    tool_layer = ToolLayer(get_settings(), knowledge, FaissKnowledgeIndex(knowledge))

    result = await tool_layer.execute(ToolName.log_reader, "disk full", demo_key="disk-full")

    assert result.success
    assert "No space left on device" in result.output
