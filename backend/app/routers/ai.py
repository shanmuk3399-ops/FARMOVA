from datetime import datetime
from statistics import mean
from fastapi import APIRouter, HTTPException
from ..database import get_db

router=APIRouter(prefix="/api/ai",tags=["AI"])

CROP_BONUS={"tomato":0.05,"tomatoes":0.05,"onion":0.03,"potato":0.02,"rice":0.04,"wheat":0.03,"maize":0.02,"cotton":0.04}

def clean(v):
    return str(v or "").strip().lower()

def demand_score(quantity:float,baseline:float,crop:str):
    crop=clean(crop)
    seasonal={"tomato":8,"tomatoes":8,"onion":5,"potato":4,"rice":7,"wheat":6,"maize":3,"cotton":5}.get(crop,2)
    scarcity=max(-12,min(12,40-quantity))
    price_signal=max(-8,min(8,(baseline-1500)/250))
    score=round(max(35,min(95,68+seasonal+scarcity+price_signal)))
    level="HIGH" if score>=75 else "MEDIUM" if score>=55 else "LOW"
    return score,level

def price_predict(crop:str,baseline:float,demand:int,quantity:float):
    if baseline<=0 or quantity<=0: raise HTTPException(400,"Baseline and quantity must be positive")
    demand=max(0,min(100,int(demand)))
    crop_key=clean(crop)
    demand_factor=(demand-50)/1000
    quantity_factor=max(-0.04,min(0.04,(25-quantity)/1000))
    crop_factor=CROP_BONUS.get(crop_key,0.01)
    recommended=round(baseline*(1+demand_factor+quantity_factor+crop_factor),2)
    retail=round(recommended*1.15,2)
    change=round((recommended-baseline)/baseline*100,2)
    level="HIGH" if demand>=75 else "MEDIUM" if demand>=55 else "LOW"
    confidence=round(min(96,max(62,72+abs(demand-70)*0.18+min(12,quantity/10))),1)
    factors=[]
    if demand>=75:factors.append("strong current demand")
    elif demand>=55:factors.append("moderate current demand")
    else:factors.append("soft current demand")
    factors.append("available quantity")
    factors.append("crop-specific market signal")
    return {"crop":crop,"recommended_price":recommended,"mandi_baseline":baseline,"demand_index":demand,"demand_level":level,"retail_rate":retail,"price_change_percentage":change,"confidence":confidence,"factors":factors,"source":"farmova-ai-demo"}

def _month_key(value):
    text=str(value or "")
    return text[:7] if len(text)>=7 else ""

def _actual_demand_by_month(conn,crop_name,location=""):
    crop=clean(crop_name)
    loc=clean(location)
    where_loc=" AND lower(location)=?" if loc else ""
    params=[crop]+([loc] if loc else [])
    rows=conn.execute(f"SELECT substr(recorded_at,1,7) period,SUM(demand) demand FROM demand_history WHERE lower(crop_name)=?{where_loc} GROUP BY substr(recorded_at,1,7) ORDER BY period ASC",params).fetchall()
    result={str(r["period"]):float(r["demand"] or 0) for r in rows if r["period"]}
    if result:
        return result,"demand_history"
    # Backfill from actual marketplace behaviour for older local databases.
    rows=conn.execute("SELECT substr(o.created_at,1,7) period,SUM(o.quantity) demand FROM offers o JOIN produce p ON p.id=o.produce_id WHERE lower(p.crop_name)=? AND o.status!='REJECTED' GROUP BY substr(o.created_at,1,7)",(crop,)).fetchall()
    for r in rows:
        if r["period"]: result[str(r["period"])]=result.get(str(r["period"]),0)+float(r["demand"] or 0)
    rows=conn.execute("SELECT substr(o.created_at,1,7) period,SUM(o.quantity) demand FROM orders o JOIN produce p ON p.id=o.produce_id WHERE lower(p.crop_name)=? AND o.status IN ('ACCEPTED','PROCESSING','SHIPPED','DELIVERED') GROUP BY substr(o.created_at,1,7)",(crop,)).fetchall()
    for r in rows:
        if r["period"]: result[str(r["period"])]=result.get(str(r["period"]),0)+float(r["demand"] or 0)
    return dict(sorted(result.items())),"offers_and_orders"

def _forecast(periods,values,future_periods):
    if len(values)>=2:
        try:
            from sklearn.linear_model import LinearRegression
            import numpy as np
            x=np.arange(1,len(values)+1,dtype=float).reshape(-1,1)
            y=np.array(values,dtype=float)
            model=LinearRegression().fit(x,y)
            fx=np.arange(len(values)+1,len(values)+future_periods+1,dtype=float).reshape(-1,1)
            preds=[max(0,round(float(v),2)) for v in model.predict(fx)]
            slope=float(model.coef_[0])
            if slope>0.5:trend="RISING"
            elif slope<-0.5:trend="FALLING"
            else:trend="STABLE"
            score=model.score(x,y) if len(values)>2 else 0.6
            confidence=round(min(95,max(60,60+score*30+min(10,len(values))),1),1)
            return preds,trend,confidence,"scikit-learn LinearRegression"
        except Exception:
            pass
    last=float(values[-1]) if values else 0.0
    trend="STABLE"
    return [round(last,2) for _ in range(future_periods)],trend,58.0,"Rolling baseline fallback (limited history)"

@router.get("/demand-forecast")
def demand_forecast(crop_name:str,location:str="",future_periods:int=4):
    if future_periods<1 or future_periods>6: raise HTTPException(400,"future_periods must be between 1 and 6")
    conn=get_db()
    series,source=_actual_demand_by_month(conn,crop_name,location)
    if not series:
        # No demand events yet: use current month as an explicit zero-observation baseline.
        current_month=datetime.utcnow().strftime("%Y-%m")
        series={current_month:0.0}
        source="no_recorded_market_demand"
    periods=list(series.keys())
    values=[float(series[p]) for p in periods]
    if source=="no_recorded_market_demand":
        preds=[0.0 for _ in range(future_periods)];trend="STABLE";confidence=55.0;algorithm="Limited-history baseline"
    else:
        preds,trend,confidence,algorithm=_forecast(periods,values,future_periods)
    return {
        "crop_name":crop_name,
        "location":location,
        "historical_periods":periods,
        "historical_demand":[round(v,2) for v in values],
        "predicted_demand":preds,
        "trend":trend,
        "confidence":confidence,
        "algorithm":algorithm,
        "data_sources":["recorded demand history" if source=="demand_history" else "buyer offers","completed/active orders" if source!="demand_history" else "buyer offers and completed/active orders"],
        "history_source":source,
        "unit":"Qtl"
    }

@router.get("/price-predict")
def price_predict_endpoint(crop:str="Wheat",baseline:float=2400.0,demand:int=70,quantity:float=10):
    return price_predict(crop,baseline,demand,quantity)

@router.post("/demand")
def demand(crop_name:str,historical_demand:str="",current_month:int=0,future_periods:int=1):
    if historical_demand.strip():
        try: values=[float(x.strip()) for x in historical_demand.split(",") if x.strip()]
        except ValueError: raise HTTPException(400,"historical_demand must contain numbers separated by commas")
        if len(values)<2: raise HTTPException(400,"At least two historical demand values are required")
        period_count=len(values)
        periods=[f"P{i+1}" for i in range(period_count)]
        preds,trend,confidence,algorithm=_forecast(periods,values,future_periods)
        return {"crop_name":crop_name,"current_month":current_month,"historical_demand":values,"predicted_demand":preds,"trend":trend,"confidence":confidence,"algorithm":algorithm,"history_source":"explicit_input"}
    return demand_forecast(crop_name=crop_name,future_periods=future_periods)

@router.post("/selling-recommendation")
def selling_recommendation(crop_name:str,current_price:float,predicted_demand:float,average_market_price:float):
    if current_price<=0 or average_market_price<=0: raise HTTPException(400,"Prices must be positive")
    score=0
    if current_price<average_market_price: score+=35
    if predicted_demand>=75: score+=40
    elif predicted_demand>=55: score+=25
    else: score+=10
    if current_price<=average_market_price*0.95: score+=15
    elif current_price>=average_market_price*1.05: score+=10
    score=min(100,score)
    action="SELL NOW" if score>=75 else "SELL WITHIN 7-14 DAYS" if score>=55 else "WAIT AND MONITOR"
    reasons=["demand is strong" if predicted_demand>=75 else "demand is moderate" if predicted_demand>=55 else "demand is soft", "listing price is below the market reference" if current_price<average_market_price else "listing price is at or above the market reference"]
    return {"crop_name":crop_name,"recommendation":action,"confidence":score,"current_price":current_price,"predicted_demand":predicted_demand,"average_market_price":average_market_price,"reasons":reasons}

@router.post("/match")
def match(crop_match:float,quantity_match:float,price_match:float,quality_match:float,location_match:float):
    vals=[max(0,min(1,float(v))) for v in (crop_match,quantity_match,price_match,quality_match,location_match)]
    score=round(sum(vals)/5*100,2);rating="Excellent" if score>=85 else "Good" if score>=70 else "Fair" if score>=50 else "Low"
    return {"match_score":score,"rating":rating}

@router.post("/real-match")
def real_match(farmer_crop:str,buyer_crop:str,available_quantity:float,required_quantity:float,farmer_price:float,buyer_price:float,farmer_quality:str="",buyer_quality:str="",farmer_location:str="",buyer_location:str=""):
    crop=1.0 if clean(farmer_crop)==clean(buyer_crop) else 0.0
    qty=min(1.0,available_quantity/required_quantity) if required_quantity>0 else 0
    price=1-min(1,abs(farmer_price-buyer_price)/max(farmer_price,buyer_price,1))
    quality=1.0 if not buyer_quality or clean(farmer_quality)==clean(buyer_quality) else 0.5
    loc=1.0 if not buyer_location or clean(farmer_location)==clean(buyer_location) else 0.7
    score=round((crop*.3+qty*.2+price*.25+quality*.1+loc*.15)*100,2)
    rating="Excellent" if score>=85 else "Good" if score>=70 else "Fair" if score>=50 else "Low"
    return {"match_score":score,"rating":rating}

@router.get("/buyer-match")
def buyer_match(produce_id:int):
    conn=get_db();p=conn.execute("SELECT * FROM produce WHERE id=? AND active=1",(produce_id,)).fetchone()
    if not p: conn.close();raise HTTPException(404,"Produce not found")
    buyers=conn.execute("SELECT id,name,location FROM users WHERE role='BUYER' ORDER BY id DESC").fetchall()
    offers=conn.execute("SELECT buyer_id,buyer_name,offered_price,quantity,status FROM offers WHERE produce_id=? ORDER BY id DESC",(produce_id,)).fetchall();conn.close()
    by_id={int(x["buyer_id"]):x for x in offers};results=[]
    for b in buyers:
        score=55;reasons=[];offer=by_id.get(int(b["id"]))
        if offer:
            score+=30;reasons.append("already showed interest on this listing")
            if str(offer["status"]).upper()=="ACCEPTED": score+=10;reasons.append("accepted offer history")
            if float(offer["offered_price"] or 0)>=float(p["expected_price"])*0.98: score+=5;reasons.append("offer price is close to your asking price")
        if clean(b["location"]) and clean(p["location"]) and clean(b["location"])==clean(p["location"]): score+=5;reasons.append("same location")
        results.append({"buyer_id":b["id"],"buyer_name":b["name"],"location":b["location"] or "Marketplace","match_score":min(99,round(score)),"reasons":reasons or ["marketplace fit based on current listing"]})
    results.sort(key=lambda x:x["match_score"],reverse=True)
    return {"produce_id":produce_id,"crop":p["crop_name"],"matches":results[:5]}

@router.get("/insights/{produce_id}")
def insights(produce_id:int):
    conn=get_db();p=conn.execute("SELECT * FROM produce WHERE id=? AND active=1",(produce_id,)).fetchone()
    if not p: conn.close();raise HTTPException(404,"Produce not found")
    history=conn.execute("SELECT price FROM price_history WHERE lower(crop_name)=lower(?) ORDER BY id DESC LIMIT 12",(p["crop_name"],)).fetchall();conn.close()
    baseline=float(p["expected_price"]);quantity=float(p["quantity"])
    forecast=demand_forecast(p["crop_name"],p["location"],4)
    idx=round(min(100,max(0,forecast["predicted_demand"][0] if forecast["predicted_demand"] else 0))) if forecast["historical_demand"] else demand_score(quantity,baseline,p["crop_name"])[0]
    level="HIGH" if idx>=75 else "MEDIUM" if idx>=55 else "LOW"
    prices=[float(x[0]) for x in history];market_avg=round(mean(prices),2) if prices else baseline
    recommended=price_predict(p["crop_name"],baseline,idx,quantity)
    predicted=float(forecast["predicted_demand"][0] if forecast["predicted_demand"] else idx)
    sell=selling_recommendation(p["crop_name"],baseline,predicted,market_avg)
    return {"produce":dict(p),"price":recommended,"demand":{"index":idx,"level":level,"forecast":forecast},"selling":sell}
