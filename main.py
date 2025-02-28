from trader import create_app
from trader.config import init_config

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        reload=init_config().is_dev(),
        port=8000,
    )
