from fastapi import FastAPI, File, UploadFile
from agent import kedro_agent

app = FastAPI()

@app.post("/process")
async def process_notebook(file: UploadFile = File(...)):
    notebook_bytes = await file.read()
    result = kedro_agent.run(notebook_bytes)
    return result
