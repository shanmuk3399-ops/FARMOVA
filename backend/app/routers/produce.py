from datetime import datetime,date
from fastapi import APIRouter,HTTPException,Depends
from pydantic import BaseModel,Field
from ..database import get_db
from ..security import optional_user,get_current_user
router=APIRouter(prefix="/api/produce",tags=["Produce"])
class ProduceIn(BaseModel):
    crop_name:str=Field(min_length=1)
    quantity:float=Field(gt=0)
    unit:str="Qtl"
    quality_grade:str="Grade A (Premium)"
    expected_price:float=Field(gt=0)
    location:str=Field(min_length=1)
    available_date:str|None=None
class ProduceUpdate(BaseModel):
    crop_name:str|None=None
    quantity:float|None=None
    unit:str|None=None
    quality_grade:str|None=None
    expected_price:float|None=None
    location:str|None=None
    available_date:str|None=None
def row_dict(r): return dict(r) if r else None
@router.post("/add")
def add(x:ProduceIn,user=Depends(optional_user)):
    farmer_id=None
    if user:
        farmer_id,role=user
        if role!="FARMER": raise HTTPException(403,"Only farmers can publish produce")
    conn=get_db();cur=conn.execute("INSERT INTO produce(farmer_id,crop_name,quantity,unit,quality_grade,expected_price,location,available_date,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(farmer_id,x.crop_name.strip(),x.quantity,x.unit,x.quality_grade,x.expected_price,x.location.strip(),x.available_date or date.today().isoformat(),datetime.utcnow().isoformat()));conn.commit();pid=cur.lastrowid;conn.close()
    return {"status":"success","message":f"{x.crop_name.strip()} saved to database!","data":{"id":pid,"farmer_id":farmer_id}}
@router.get("/list")
def list_all():
    conn=get_db();rows=conn.execute("SELECT id,farmer_id,crop_name,quantity,unit,quality_grade,expected_price,location,available_date,created_at FROM produce WHERE active=1 AND quantity>0 ORDER BY id DESC").fetchall();conn.close();return [dict(r) for r in rows]
@router.get("/search")
def search(crop:str="",location:str=""):
    conn=get_db();rows=conn.execute("SELECT id,farmer_id,crop_name,quantity,unit,quality_grade,expected_price,location,available_date,created_at FROM produce WHERE active=1 AND quantity>0 AND lower(crop_name) LIKE ? AND lower(location) LIKE ? ORDER BY id DESC",(f"%{crop.lower()}%",f"%{location.lower()}%")).fetchall();conn.close();return [dict(r) for r in rows]
@router.get("/farmer/{farmer_id}")
def farmer_list(farmer_id:int):
    conn=get_db();rows=conn.execute("SELECT id,farmer_id,crop_name,quantity,unit,quality_grade,expected_price,location,available_date,created_at,active FROM produce WHERE farmer_id=? ORDER BY id DESC",(farmer_id,)).fetchall();conn.close();return [dict(r) for r in rows]
@router.get("/{produce_id}")
def get_one(produce_id:int):
    conn=get_db();r=conn.execute("SELECT * FROM produce WHERE id=?",(produce_id,)).fetchone();conn.close()
    if not r: raise HTTPException(404,"Produce not found")
    return dict(r)
@router.put("/{produce_id}")
def update(produce_id:int,x:ProduceUpdate,current=Depends(get_current_user)):
    uid,role=current
    if role!="FARMER": raise HTTPException(403,"Only farmers can edit produce")
    conn=get_db();old=conn.execute("SELECT * FROM produce WHERE id=?",(produce_id,)).fetchone()
    if not old: conn.close();raise HTTPException(404,"Produce not found")
    if old["farmer_id"] not in (None,uid): conn.close();raise HTTPException(403,"You can edit only your own produce")
    data=x.model_dump(exclude_none=True)
    if not data: conn.close();return dict(old)
    sets=",".join(f"{k}=?" for k in data);vals=list(data.values())+[produce_id]
    conn.execute(f"UPDATE produce SET {sets} WHERE id=?",vals);conn.commit();r=conn.execute("SELECT * FROM produce WHERE id=?",(produce_id,)).fetchone();conn.close();return dict(r)
@router.delete("/{produce_id}")
def delete(produce_id:int,current=Depends(get_current_user)):
    uid,role=current
    if role!="FARMER": raise HTTPException(403,"Only farmers can delete produce")
    conn=get_db();r=conn.execute("SELECT farmer_id,crop_name FROM produce WHERE id=?",(produce_id,)).fetchone()
    if not r: conn.close();raise HTTPException(404,"Produce not found")
    if r["farmer_id"] not in (None,uid): conn.close();raise HTTPException(403,"You can delete only your own produce")
    conn.execute("UPDATE produce SET active=0,quantity=0 WHERE id=?",(produce_id,));conn.commit();conn.close();return {"message":f"{r['crop_name']} removed successfully."}
