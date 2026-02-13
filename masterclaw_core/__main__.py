"""Entry point for MasterClaw Core"""

import uvicorn
from .config import settings


def main():
    """Run the FastAPI application"""
    uvicorn.run(
        "masterclaw_core.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL,
        reload=settings.LOG_LEVEL == "debug",
    )


if __name__ == "__main__":
    main()
