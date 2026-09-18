from datetime import datetime
from fastapi import APIRouter,HTTPException,Depends
from ..database import get_db
from ..security import get_current_user
router=APIRouter(prefix="/api/offers",tags=["Offers"])
@router.post("/place")
def place(produce_id:int=0,quantity:float=0,offered_price:float=0,current=Depends(get_current_user)):
    uid,role=current
    if role!="BUYER": raise HTTPException(403,"Only buyers can place offers")
    if quantity<=0 or offered_price<=0: raise HTTPException(400,"Quantity and offered price must be greater than zero")
    conn=get_db();p=conn.execute("SELECT * FROM produce WHERE id=? AND active=1",(produce_id,)).fetchone();u=conn.execute("SELECT name FROM users WHERE id=?",(uid,)).fetchone()
    if not p: conn.close();raise HTTPException(404,"Produce not found")
    if quantity>p["quantity"]: conn.close();raise HTTPException(400,"Requested quantity exceeds available quantity")
    now=datetime.utcnow().isoformat()
    cur=conn.execute("INSERT INTO offers(produce_id,buyer_id,buyer_name,quantity,offered_price,status,created_at) VALUES(?,?,?,?,?,?,?)",(produce_id,uid,u["name"],quantity,offered_price,"PENDING",now))
    conn.execute("INSERT INTO demand_history(crop_name,location,demand,month,recorded_at) VALUES(?,?,?,?,?)",(p["crop_name"],p["location"],quantity,datetime.utcnow().month,now))
    conn.commit();oid=cur.lastrowid;conn.close();return {"message":"Offer placed successfully","offer_id":oid,"status":"PENDING"}
@router.get("/produce/{produce_id}")
def get_produce_offers(produce_id:int):
    conn=get_db();rows=conn.execute("SELECT o.id offer_id,o.buyer_id,o.produce_id,p.crop_name,o.quantity,p.unit,o.offered_price,o.status,o.created_at FROM offers o JOIN produce p ON p.id=o.produce_id WHERE o.produce_id=? ORDER BY o.created_at DESC",(produce_id,)).fetchall();conn.close();return {"produce_id":produce_id,"offers":[dict(r) for r in rows]}
@router.get("/buyer/{buyer_id}")
def get_buyer_offers(buyer_id:int):
    conn=get_db();rows=conn.execute("SELECT o.id offer_id,o.buyer_id,o.produce_id,p.crop_name,o.quantity,p.unit,o.offered_price,o.status,o.created_at FROM offers o JOIN produce p ON p.id=o.produce_id WHERE o.buyer_id=? ORDER BY o.created_at DESC",(buyer_id,)).fetchall();conn.close();return {"buyer_id":buyer_id,"offers":[dict(r) for r in rows]}
@router.put("/{offer_id}/status")
def status(offer_id:int,status:str,current=Depends(get_current_user)):
    uid,role=current
    if role!="FARMER": raise HTTPException(403,"Only farmers can update offers")
    status=status.upper()
    if status not in ("ACCEPTED","REJECTED"): raise HTTPException(400,"Status must be ACCEPTED or REJECTED")
    conn=get_db();o=conn.execute("SELECT o.*,p.farmer_id,p.quantity available_qty,p.crop_name FROM offers o JOIN produce p ON p.id=o.produce_id WHERE o.id=?",(offer_id,)).fetchone()
    if not o: conn.close();raise HTTPException(404,"Offer not found")
    if o["farmer_id"] not in (None,uid): conn.close();raise HTTPException(403,"You can update offers only for your produce")
    if o["status"]!="PENDING": conn.close();raise HTTPException(400,"Offer has already been processed")
    order_id=None
    if status=="ACCEPTED":
        if o["quantity"]>o["available_qty"]: conn.close();raise HTTPException(400,"Not enough produce available")
        total=o["quantity"]*o["offered_price"]
        conn.execute("UPDATE produce SET quantity=quantity-? WHERE id=?",(o["quantity"],o["produce_id"]))
        cur=conn.execute("INSERT INTO orders(produce_id,buyer_id,farmer_id,quantity,unit_price,total_price,status,tracking_status,source_type,offer_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(o["produce_id"],o["buyer_id"],uid,o["quantity"],o["offered_price"],total,"ACCEPTED","ACCEPTED","OFFER",offer_id,datetime.utcnow().isoformat()))
        order_id=cur.lastrowid
    conn.execute("UPDATE offers SET status=? WHERE id=?",(status,offer_id));conn.commit();conn.close();return {"offer_id":offer_id,"status":status,"order_id":order_id}
