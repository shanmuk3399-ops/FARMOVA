from fastapi import FastAPI
from pydantic import BaseModel,Field
app=FastAPI(title="FarmDirect AI Service",version="2.0.0")
class PriceIn(BaseModel):
    crop:str
    baseline:float=Field(gt=0)
    demand:float=Field(ge=0,le=100)
    quantity:float=Field(gt=0)
@app.get("/")
def root():return {"status":"online","service":"ai-price"}
@app.get("/health")
def health():return {"status":"healthy"}
@app.post("/predict-price")
def predict_price(x:PriceIn):
    demand_factor=(x.demand-50)/1000;quantity_factor=max(-0.05,min(0.05,(50-x.quantity)/1000));crop_factor=0.02 if x.crop.strip().lower() in {"tomato","tomatoes","rice","wheat"} else 0
    recommended=round(x.baseline*(1+demand_factor+quantity_factor+crop_factor),2);retail=round(recommended*1.15,2);change=round((recommended-x.baseline)/x.baseline*100,2);level="HIGH" if x.demand>=75 else "MEDIUM" if x.demand>=55 else "LOW"
    return {"crop":x.crop,"recommended_price":recommended,"mandi_baseline":x.baseline,"demand_index":round(x.demand,2),"demand_level":level,"retail_rate":retail,"price_change_percentage":change,"source":"ai-service"}
