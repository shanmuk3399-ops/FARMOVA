from math import radians,sin,cos,sqrt,atan2
def hav(a,b):
    R=6371.0;dlat=radians(b[0]-a[0]);dlon=radians(b[1]-a[1]);x=sin(dlat/2)**2+cos(radians(a[0]))*cos(radians(b[0]))*sin(dlon/2)**2;return R*2*atan2(sqrt(x),sqrt(1-x))
def optimize(req):
    remaining=list(req.stops);cur=(req.depot.lat,req.depot.lon);ordered=[];total=0
    while remaining:
        nxt=min(remaining,key=lambda s:hav(cur,(s.lat,s.lon)));d=hav(cur,(nxt.lat,nxt.lon));total+=d;ordered.append(nxt);cur=(nxt.lat,nxt.lon);remaining.remove(nxt)
    total+=hav(cur,(req.depot.lat,req.depot.lon))
    q=sum(s.quantity_kg for s in ordered)
    return {"order_id":req.order_id,"optimized_stop_sequence":[{"sequence":i+1,"farmer_id":s.farmer_id,"farmer_name":s.farmer_name,"quantity_kg":s.quantity_kg,"lat":s.lat,"lon":s.lon} for i,s in enumerate(ordered)],"farmer_ids":[s.farmer_id for s in ordered],"farmer_names":[s.farmer_name for s in ordered],"pickup_quantities":[s.quantity_kg for s in ordered],"total_quantity_kg":q,"total_road_distance_km":round(total,2),"estimated_travel_time_minutes":round(total/45*60,1),"vehicle_capacity_kg":req.vehicle_capacity_kg,"route_status":"optimized"}
def cost(req):
    fuel=req.distance_km/req.fuel_efficiency_km_l;fc=fuel*req.fuel_price_per_l;total=fc+req.driver_cost+req.toll_cost+req.additional_cost;return {"order_id":req.order_id,"fuel_used_l":round(fuel,3),"fuel_cost":round(fc,2),"driver_cost":req.driver_cost,"toll_cost":req.toll_cost,"additional_cost":req.additional_cost,"total_estimated_cost":round(total,2),"estimate_note":"Estimated transportation cost based on supplied route and cost inputs."}
def allocate(req):
    totalq=sum(float(x["quantity_kg"]) for x in req.farmer_contributions);out=[]
    if totalq<=0:return {"order_id":req.order_id,"total_transportation_cost":req.total_transportation_cost,"farmer_allocations":[]}
    for x in req.farmer_contributions:
        q=float(x["quantity_kg"]);share=q/totalq*100;out.append({"farmer_id":str(x["farmer_id"]),"farmer_name":str(x["farmer_name"]),"quantity_kg":q,"share_percentage":round(share,2),"allocated_cost":round(req.total_transportation_cost*q/totalq,2)})
    diff=round(req.total_transportation_cost-sum(x["allocated_cost"] for x in out),2)
    if out:out[0]["allocated_cost"]=round(out[0]["allocated_cost"]+diff,2)
    return {"order_id":req.order_id,"total_transportation_cost":req.total_transportation_cost,"farmer_allocations":out}
