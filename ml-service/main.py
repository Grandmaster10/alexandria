from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

app = FastAPI(title = "Vector Embedding")

print("loading model.....")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("model loaded succesfully")

class embedRequest(BaseModel):
    text: str

@app.post("/embed")
async def generate_embedding(request: embedRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Empty text.")
    
    try:
        vector = model.encode(request.text)
        return vector.tolist()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML Error: {str(e)}")