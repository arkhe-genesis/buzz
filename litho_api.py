from fastapi import FastAPI
from typing import Dict, Any

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Litho API Running"}
