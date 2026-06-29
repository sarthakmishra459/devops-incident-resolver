import uvicorn

from devops_resolver.shared.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "devops_resolver.presentation.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "local",
    )
