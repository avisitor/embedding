import os
import gc
import psutil
import torch
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
import spacy

# --- Schemas (Pydantic) ---
# This replaces all the manual 'if key in data' checks
class EmbedRequest(BaseModel):
    text: str
    prefix: str = "passage: "
    model: str = "intfloat/multilingual-e5-small"

class BatchEmbedRequest(BaseModel):
    sentences: List[str]
    prefix: str = "passage: "
    model: str = "intfloat/multilingual-e5-small"

class AnalyzeRequest(BaseModel):
    sentence: str

# --- App Initialization ---
app = FastAPI(
    title="Hawaiian Corpus Embedding Service",
    description="High-performance vector embedding and NLP analysis API",
    version="2.0.0"
)

# Global model container
class ModelContainer:
    def __init__(self):
        self.models = {}
        self.nlp = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load_models(self):
        print(f"🔄 Loading models on {self.device}...")
        self.models['intfloat/multilingual-e5-small'] = SentenceTransformer('intfloat/multilingual-e5-small', device=self.device)
        self.models['intfloat/multilingual-e5-large-instruct'] = SentenceTransformer('intfloat/multilingual-e5-large-instruct', device=self.device)
        self.nlp = spacy.load("en_core_web_sm", disable=["parser"])
        print("✅ Models ready.")

models = ModelContainer()

@app.on_event("startup")
async def startup_event():
    models.load_models()

# --- Helpers ---
def memory_cleanup():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "healthy", "device": models.device}

@app.post("/embed")
def embed_text(request: EmbedRequest):
    try:
        model = models.models.get(request.model)
        if not model:
            raise HTTPException(status_code=400, detail=f"Model {request.model} not loaded")
        combined_text = f"{request.prefix}{request.text}"
        embedding = model.encode(combined_text)
        return {"embedding": embedding.tolist(), "dimensions": len(embedding)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed_sentences")
def embed_batch(request: BatchEmbedRequest, background_tasks: BackgroundTasks):
    if not request.sentences:
        raise HTTPException(status_code=400, detail="Empty sentence list")

    try:
        model = models.models.get(request.model)
        if not model:
            raise HTTPException(status_code=400, detail=f"Model {request.model} not loaded")
        prefixed = [f"{request.prefix}{s}" for s in request.sentences]
        # .encode is a blocking call, but FastAPI handles this well in a thread pool
        embeddings = model.encode(prefixed, batch_size=32)
        
        # Schedule cleanup after returning the response
        if psutil.virtual_memory().percent > 80:
            background_tasks.add_task(memory_cleanup)

        return {
            "embeddings": embeddings.tolist(),
            "count": len(embeddings)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
def analyze_text(request: AnalyzeRequest):
    doc = models.nlp(request.sentence)
    return {
        "entity_count": len(doc.ents),
        "entities": [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
    }

@app.get("/memory")
async def memory_status():
    mem = psutil.virtual_memory()
    return {
        "used_gb": round(psutil.Process().memory_info().rss / (1024**3), 2),
        "percent": mem.percent
    }
