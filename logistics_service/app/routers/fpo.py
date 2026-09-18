from fastapi import APIRouter
router=APIRouter(prefix="/api/fpo",tags=["FPO Logistics"])
SAMPLE=[{"listing_id":"L001","farmer_id":"F001","farmer_name":"Farmer A","fpo_id":"FPO-001","crop":"Tomato","quality":"Grade A","available_quantity_kg":500,"price_per_kg":40,"lat":17.385,"lon":78.486},{"listing_id":"L002","farmer_id":"F002","farmer_name":"Farmer B","fpo_id":"FPO-001","crop":"Tomato","quality":"Grade A","available_quantity_kg":800,"price_per_kg":39,"lat":17.968,"lon":79.594},{"listing_id":"L003","farmer_id":"F003","farmer_name":"Farmer C","fpo_id":"FPO-001","crop":"Rice","quality":"Grade A","available_quantity_kg":1000,"price_per_kg":35,"lat":16.506,"lon":80.648}]
@router.get("/{fpo_id}/available-produce")
def available(fpo_id:str):return {"fpo_id":fpo_id,"produce":[x for x in SAMPLE if x["fpo_id"]==fpo_id]}
@router.get("/{fpo_id}/suitability-scores")
def suitability(fpo_id:str,crop:str,required_quantity_kg:float,reference_latitude:float,reference_longitude:float):
    from ..logic import hav
    vals=[]
    for x in SAMPLE:
        if x["fpo_id"]!=fpo_id:continue
        crop_score=1 if x["crop"].lower()==crop.lower() else 0
        qty_score=min(1,x["available_quantity_kg"]/required_quantity_kg) if required_quantity_kg else 0
        loc=hav((x["lat"],x["lon"]),(reference_latitude,reference_longitude))
        loc_score=max(0,1-loc/500)
        score=round((crop_score*.5+qty_score*.3+loc_score*.2)*100,2)
        vals.append({**x,"distance_km":round(loc,2),"suitability_score":score})
    return {"fpo_id":fpo_id,"crop":crop,"required_quantity_kg":required_quantity_kg,"candidates":sorted(vals,key=lambda x:x["suitability_score"],reverse=True)}
@router.post("/{fpo_id}/aggregate")
def create_batch(fpo_id:str,request:dict):return {"message":"Aggregation batch created successfully","batch":{"batch_id":"BATCH-001","fpo_id":fpo_id,**request}}
@router.get("/{fpo_id}/batches")
def get_batches(fpo_id:str):return {"fpo_id":fpo_id,"batches":[]}
@router.post("/{fpo_id}/match-bulk-order")
def match_bulk_order(fpo_id:str,request:dict):return {"message":"Bulk order matching completed","fpo_id":fpo_id,"buyer_order_id":request.get("buyer_order_id"),"matched_quantity_kg":request.get("required_quantity_kg",0)}
