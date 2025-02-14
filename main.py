from trader import create_app
from trader.core.config import settings

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.UVICORN_HOST,
        reload=settings.is_dev(),
        port=settings.UVICORN_PORT,
    )
