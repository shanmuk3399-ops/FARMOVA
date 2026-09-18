from fastapi import APIRouter,HTTPException
from ..models import RouteRequest,CostRequest,AllocationRequest
from ..logic import optimize,cost,allocate
router=APIRouter(prefix="/api/logistics",tags=["Logistics"])
routes={}
@router.post("/optimize-route")
def optimize_route(x:RouteRequest):
    if sum(s.quantity_kg for s in x.stops)>x.vehicle_capacity_kg:raise HTTPException(400,"Vehicle capacity exceeded")
    result=optimize(x);routes[x.order_id]=result;return result
@router.post("/calculate-cost")
def calculate_cost(x:CostRequest):return cost(x)
@router.post("/allocate-cost")
def allocate_cost(x:AllocationRequest):return allocate(x)
@router.get("/routes/{order_id}")
def get_route(order_id:str):
    if order_id not in routes:raise HTTPException(404,"Route not found for the supplied order ID.")
    return routes[order_id]
