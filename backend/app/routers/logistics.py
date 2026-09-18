import json, math
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from ..database import get_db
router=APIRouter(prefix="/api/logistics",tags=["Logistics"])
class RouteIn(BaseModel):
    pickup_1:str=Field(min_length=1)
    pickup_2:str|None=None
    destination:str=Field(min_length=1)
    vehicle_type:str="10-Tonne Multi-Axle Heavy Truck"
class CostIn(BaseModel):
    distance_km:float=Field(gt=0)
    quantity_qtl:float=Field(gt=0)
    vehicle_type:str="10-Tonne Multi-Axle Heavy Truck"
class AllocationIn(BaseModel):
    total_cost:float=Field(gt=0)
    contributors:list
COORDS={"hyderabad":(17.385,78.4867),"warangal":(17.9689,79.5941),"vijayawada":(16.5062,80.648),"pune":(18.5204,73.8567),"mumbai":(19.076,72.8777),"nashik":(19.9975,73.7898),"delhi":(28.6139,77.209),"bangalore":(12.9716,77.5946),"chennai":(13.0827,80.2707)}
def point(s,i):
    t=str(s or "").lower().strip()
    for k,v in COORDS.items():
        if k in t or t in k:return v
    return [(20.0,74.0),(20.8,75.5),(19.0,73.0)][i] if i<3 else (19.5,76.5)
def hav(a,b):
    r=6371.0;lat1,lon1=map(math.radians,a);lat2,lon2=map(math.radians,b);dlat=lat2-lat1;dlon=lon2-lon1
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return r*2*math.atan2(math.sqrt(h),math.sqrt(1-h))
def route_estimate(x):
    pts=[x.pickup_1]+([x.pickup_2] if x.pickup_2 else [])+[x.destination]
    coords=[point(p,i) for i,p in enumerate(pts)]
    km=sum(hav(coords[i],coords[i+1]) for i in range(len(coords)-1))*1.15
    h=km/45;hrs=int(h);mins=round((h-hrs)*60)
    rate=2.45 if "reefer" in x.vehicle_type.lower() else 1.65 if "10-tonne" in x.vehicle_type.lower() else 2.9
    cost=max(20,km*rate/10)
    savings=18 if len(pts)>=3 else 10
    return {"distance_km":round(km,1),"duration":f"{hrs} Hours {mins} Mins","freight_cost_per_qtl":round(cost,2),"savings_percentage":savings,"assigned_truck":x.vehicle_type,"stops":pts,"source":"farmova-main-backend"}
@router.post("/optimize")
def optimize(x:RouteIn):
    return route_estimate(x)
@router.post("/optimize-route")
def optimize_route(x:RouteIn):
    return optimize(x)
@router.post("/calculate-cost")
def calculate_cost(x:CostIn):
    total=max(500,x.distance_km*(18 if "10-tonne" in x.vehicle_type.lower() else 24))
    fuel=max(300,x.distance_km*.45);driver=max(250,x.distance_km*3);toll=max(100,x.distance_km*1.5);additional=100.0
    return {"distance_km":round(x.distance_km,1),"quantity_qtl":x.quantity_qtl,"total_cost":round(total,2),"fuel_cost":round(fuel,2),"driver_cost":round(driver,2),"toll_cost":round(toll,2),"additional_cost":additional,"cost_per_qtl":round(total/x.quantity_qtl,2),"source":"farmova-main-backend"}
@router.post("/allocate-cost")
def allocate_cost(x:AllocationIn):
    total_qty=sum(float(i.get("quantity",0) or 0) for i in x.contributors)
    if total_qty<=0: raise HTTPException(400,"Contributor quantities must be greater than zero")
    result=[]
    for i in x.contributors:
        qty=float(i.get("quantity",0) or 0);pct=qty/total_qty*100
        result.append({"farmer_id":i.get("farmer_id"),"farmer_name":i.get("farmer_name","Farmer"),"quantity_qtl":qty,"share_percentage":round(pct,2),"allocated_cost":round(x.total_cost*pct/100,2)})
    return {"total_cost":x.total_cost,"total_quantity_qtl":total_qty,"allocations":result,"source":"farmova-main-backend"}
@router.get("/routes/{order_id}")
def route_by_order(order_id:int):
    conn=get_db();r=conn.execute("SELECT * FROM routes WHERE order_id=?",(str(order_id),)).fetchone();conn.close()
    if not r: raise HTTPException(404,"Route not found for this order")
    item=dict(r)
    try:item["route"]=json.loads(item.pop("route_json"))
    except Exception:item["route"]={}
    return item
