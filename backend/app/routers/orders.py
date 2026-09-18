from datetime import datetime
from fastapi import APIRouter,HTTPException,Depends
from ..database import get_db
from ..security import get_current_user
router=APIRouter(prefix="/api/orders",tags=["Orders"])
@router.post("/place")
def place(produce_id:int=0,quantity:float=0,current=Depends(get_current_user)):
    uid,role=current
    if role!="BUYER": raise HTTPException(403,"Only buyers can place orders")
    if quantity<=0: raise HTTPException(400,"Quantity must be greater than zero")
    conn=get_db();p=conn.execute("SELECT * FROM produce WHERE id=? AND active=1",(produce_id,)).fetchone()
    if not p: conn.close();raise HTTPException(404,"Produce not found")
    if quantity>p["quantity"]: conn.close();raise HTTPException(400,"Requested quantity exceeds available quantity")
    total=quantity*p["expected_price"]
    now=datetime.utcnow().isoformat()
    cur=conn.execute("INSERT INTO orders(produce_id,buyer_id,farmer_id,quantity,unit_price,total_price,status,tracking_status,source_type,offer_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(produce_id,uid,p["farmer_id"],quantity,p["expected_price"],total,"ACCEPTED","ACCEPTED","DIRECT",None,now))
    conn.execute("INSERT INTO demand_history(crop_name,location,demand,month,recorded_at) VALUES(?,?,?,?,?)",(p["crop_name"],p["location"],quantity,datetime.utcnow().month,now))
    conn.execute("UPDATE produce SET quantity=quantity-? WHERE id=?",(quantity,produce_id))
    conn.commit();oid=cur.lastrowid;conn.close();return {"message":"Order placed successfully","order_id":oid,"total_price":total,"status":"ACCEPTED","tracking_status":"ACCEPTED","source_type":"DIRECT"}
@router.get("/buyer/{buyer_id}")
def buyer_orders(buyer_id:int):
    conn=get_db();rows=conn.execute("SELECT o.*,p.crop_name,p.location,p.unit FROM orders o JOIN produce p ON p.id=o.produce_id WHERE o.buyer_id=? ORDER BY o.created_at DESC",(buyer_id,)).fetchall();conn.close();return [dict(r) for r in rows]
@router.get("/farmer/{farmer_id}")
def farmer_orders(farmer_id:int):
    conn=get_db();rows=conn.execute("SELECT o.*,p.crop_name,p.location,p.unit FROM orders o JOIN produce p ON p.id=o.produce_id WHERE o.farmer_id=? ORDER BY o.created_at DESC",(farmer_id,)).fetchall();conn.close();return [dict(r) for r in rows]
@router.put("/{order_id}/status")
def update(order_id:int,status:str,current=Depends(get_current_user)):
    uid,role=current;status=status.upper()
    allowed={"ACCEPTED","PROCESSING","SHIPPED","DELIVERED","REJECTED","CANCELLED"}
    if status not in allowed: raise HTTPException(400,"Invalid order status")
    conn=get_db();o=conn.execute("SELECT * FROM orders WHERE id=?",(order_id,)).fetchone()
    if not o: conn.close();raise HTTPException(404,"Order not found")
    if role=="FARMER" and o["farmer_id"]!=uid: conn.close();raise HTTPException(403,"Not your order")
    if role=="BUYER" and o["buyer_id"]!=uid: conn.close();raise HTTPException(403,"Not your order")
    old=o["status"]
    if status=="ACCEPTED" and old not in ("ACCEPTED",):
        p=conn.execute("SELECT quantity FROM produce WHERE id=?",(o["produce_id"],)).fetchone()
        if p and o["source_type"]=="DIRECT" and o["quantity"]>p["quantity"]: conn.close();raise HTTPException(400,"Not enough produce available")
    tracking=status if status in ("ACCEPTED","PROCESSING","SHIPPED","DELIVERED") else (o["tracking_status"] or "ACCEPTED")
    conn.execute("UPDATE orders SET status=?,tracking_status=? WHERE id=?",(status,tracking,order_id));conn.commit();conn.close();return {"order_id":order_id,"status":status,"tracking_status":tracking}
@router.get("/{order_id}/track")
def track(order_id:int):
    conn=get_db();o=conn.execute("SELECT id,status,tracking_status,source_type,offer_id,created_at FROM orders WHERE id=?",(order_id,)).fetchone();conn.close()
    if not o: raise HTTPException(404,"Order not found")
    return dict(o)
@router.get("/farmer/{farmer_id}/earnings")
def farmer_earnings(farmer_id:int):
    conn=get_db();row=conn.execute("SELECT COALESCE(SUM(total_price),0) gross_revenue, COUNT(*) order_count FROM orders WHERE farmer_id=? AND status IN ('ACCEPTED','PROCESSING','SHIPPED','DELIVERED')",(farmer_id,)).fetchone();conn.close();gross=float(row["gross_revenue"]);transport=round(gross*0.02,2);platform=round(gross*0.01,2);net=round(gross-transport-platform,2);return {"farmer_id":farmer_id,"order_count":row["order_count"],"gross_revenue":gross,"transport_cost":transport,"platform_fee":platform,"total_deductions":round(transport+platform,2),"net_payout":net}
