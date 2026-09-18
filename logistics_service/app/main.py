import math
from fastapi import FastAPI
from pydantic import BaseModel,Field
app=FastAPI(title="FarmDirect Logistics Service",version="2.0.0")
COORDS={"hyderabad":(17.3850,78.4867),"nashik":(19.9975,73.7898),"igatpuri":(19.6952,73.5627),"mumbai":(19.0760,72.8777),"vashi":(19.0771,72.9986),"pune":(18.5204,73.8567),"delhi":(28.6139,77.2090),"new delhi":(28.6139,77.2090),"bangalore":(12.9716,77.5946),"bengaluru":(12.9716,77.5946),"amritsar":(31.6340,74.8723),"ludhiana":(30.9010,75.8573),"vijayawada":(16.5062,80.6480),"warangal":(17.9689,79.5941),"nagpur":(21.1458,79.0882),"jaipur":(26.9124,75.7873),"kolkata":(22.5726,88.3639),"chennai":(13.0827,80.2707)}
class RouteIn(BaseModel):
    pickup_1:str
    pickup_2:str|None=None
    destination:str
    vehicle_type:str="10-Tonne Multi-Axle Heavy Truck"
class CostIn(BaseModel):
    distance_km:float=Field(gt=0)
    quantity_qtl:float=Field(gt=0)
    vehicle_type:str="10-Tonne Multi-Axle Heavy Truck"
class AllocationIn(BaseModel):
    total_cost:float=Field(gt=0)
    contributors:list

def find(name,idx):
    key=name.strip().lower()
    if key in COORDS:return COORDS[key]
    for k,v in COORDS.items():
        if key in k or k in key:return v
    seeds=[(17.3850,78.4867),(19.0760,72.8777),(28.6139,77.2090),(12.9716,77.5946),(22.5726,88.3639)]
    return seeds[idx%len(seeds)]
def hav(a,b):
    R=6371;p=math.pi/180;dlat=(b[0]-a[0])*p;dlon=(b[1]-a[1])*p;x=math.sin(dlat/2)**2+math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin(dlon/2)**2
    return R*2*math.atan2(math.sqrt(x),math.sqrt(1-x))
@app.get("/")
def root():return {"status":"online","service":"logistics","version":"2.0.0"}
@app.get("/health")
def health():return {"status":"healthy"}
@app.post("/optimize-route")
def optimize(x:RouteIn):
    names=[x.pickup_1]+([x.pickup_2] if x.pickup_2 and x.pickup_2.strip() else [])+[x.destination];pts=[find(v,i) for i,v in enumerate(names)];raw=sum(hav(pts[i],pts[i+1]) for i in range(len(pts)-1));distance=round(raw*1.12,1);speed=42 if "heavy" in x.vehicle_type.lower() else 50;mins=round(distance/speed*60);h=mins//60;m=mins%60;cost=round(max(25,distance*.25),2);return {"distance_km":distance,"duration":f"{h} Hours {m:02d} Mins","freight_cost_per_qtl":cost,"savings_percentage":20,"assigned_truck":x.vehicle_type,"stops":names,"source":"logistics-service"}
@app.post("/calculate-cost")
def calculate_cost(x:CostIn):
    fuel=round(max(300,x.distance_km*(.45 if "heavy" in x.vehicle_type.lower() else .3)),2);driver=round(max(250,x.distance_km*3),2);toll=round(max(100,x.distance_km*1.5),2);additional=100.0;total=round(fuel+driver+toll+additional,2);return {"distance_km":round(x.distance_km,1),"quantity_qtl":x.quantity_qtl,"fuel_cost":fuel,"driver_cost":driver,"toll_cost":toll,"additional_cost":additional,"total_cost":total,"cost_per_qtl":round(total/x.quantity_qtl,2),"source":"logistics-service"}
@app.post("/allocate-cost")
def allocate_cost(x:AllocationIn):
    total_qty=sum(float(i.get("quantity",0) or 0) for i in x.contributors)
    if total_qty<=0:return {"total_cost":x.total_cost,"allocations":[],"source":"logistics-service"}
    result=[]
    for i in x.contributors:
        qty=float(i.get("quantity",0) or 0);pct=qty/total_qty*100;result.append({"farmer_id":i.get("farmer_id"),"farmer_name":i.get("farmer_name","Farmer"),"quantity_qtl":qty,"share_percentage":round(pct,2),"allocated_cost":round(x.total_cost*pct/100,2)})
    return {"total_cost":x.total_cost,"total_quantity_qtl":total_qty,"allocations":result,"source":"logistics-service"}
