from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .routers import auth, produce, offers, orders, fpo, ai, logistics

app=FastAPI(title="Farmova Backend",version="4.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return {
        "status":"online",
        "database":"connected",
        "main_api":"http://127.0.0.1:8000",
        "services":{
            "ai":"/api/ai",
            "logistics":"/api/logistics",
            "frontend":"/"
        }
    }

@app.get("/health")
def health():
    return {"status":"healthy","port":8000}

app.include_router(auth.router)
app.include_router(produce.router)
app.include_router(offers.router)
app.include_router(orders.router)
app.include_router(fpo.router)
app.include_router(ai.router)
app.include_router(logistics.router)
