from devops_resolver.infrastructure.demo_data import demo_incidents, knowledge_documents


def test_demo_incidents_have_realistic_logs() -> None:
    demos = demo_incidents()

    assert len(demos) == 10
    assert {demo.key for demo in demos} == {
        "high-cpu",
        "disk-full",
        "postgresql-down",
        "redis-memory-full",
        "out-of-memory",
        "service-crash",
        "ssl-expired",
        "high-disk-io",
        "nginx-502",
        "memory-leak",
    }
    assert all(len(demo.log_lines) >= 4 for demo in demos)
    assert all("2026-06-29" in line for demo in demos for line in demo.log_lines)


def test_knowledge_documents_cover_runbooks_and_previous_incidents() -> None:
    documents = knowledge_documents()
    categories = {document.category for document in documents}

    assert "runbook" in categories
    assert "previous_incident" in categories
    assert "infrastructure_documentation" in categories
    assert len([document for document in documents if document.category == "runbook"]) == 10
