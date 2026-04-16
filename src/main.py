import uvicorn 
from src.api import api


if __name__ == "__main__":
    uvicorn.run(app=api.app, reload=True)