from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.ws import router as ws_router

app = FastAPI(title="MOSAIC Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)

from app.recovery.receipt import DecisionReceipt

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "backend healthy"}

@app.get("/recovery/{shipment_id}", response_model=DecisionReceipt)
def get_recovery_plan(shipment_id: str):
    # Stub endpoint demonstrating the API response shape for the frontend
    pass
