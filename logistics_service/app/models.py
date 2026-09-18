from pydantic import BaseModel,Field
class Pickup(BaseModel):
    farmer_id:str
    farmer_name:str
    quantity_kg:float=Field(gt=0)
    lat:float
    lon:float
class Depot(BaseModel):
    lat:float
    lon:float
class RouteRequest(BaseModel):
    order_id:str
    vehicle_capacity_kg:float=Field(gt=0)
    depot:Depot
    stops:list[Pickup]=[]
class CostRequest(BaseModel):
    order_id:str
    distance_km:float=Field(gt=0)
    fuel_efficiency_km_l:float=Field(gt=0)
    fuel_price_per_l:float=Field(gt=0)
    driver_cost:float=0
    toll_cost:float=0
    additional_cost:float=0
class AllocationRequest(BaseModel):
    order_id:str
    total_transportation_cost:float=Field(ge=0)
    farmer_contributions:list[dict]
