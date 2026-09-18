from datetime import datetime
from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from ..database import get_db
from ..security import hash_password,create_token,get_current_user
from fastapi import HTTPException
router=APIRouter(prefix="/api/auth",tags=["Authentication"])
class RegisterIn(BaseModel):
    name:str=Field(min_length=2)
    phone:str=Field(min_length=5)
    password:str=Field(min_length=4)
    role:str
    location:str=""
    language:str="English"
class LoginIn(BaseModel):
    phone:str
    password:str
@router.post("/register")
def register(x:RegisterIn):
    role=x.role.upper().strip()
    if role not in ("FARMER","BUYER","FPO"): raise HTTPException(400,"Role must be FARMER, BUYER or FPO")
    conn=get_db()
    try:
        cur=conn.execute("INSERT INTO users(name,phone,password,role,location,language,created_at) VALUES(?,?,?,?,?,?,?)",(x.name.strip(),x.phone.strip(),hash_password(x.password),role,x.location.strip(),x.language.strip(),datetime.utcnow().isoformat()))
        uid=cur.lastrowid
        if role=="FPO":
            conn.execute("INSERT INTO fpos(name,location,created_by,created_at) VALUES(?,?,?,?)",(x.name.strip(),x.location.strip(),uid,datetime.utcnow().isoformat()))
            fpo_id=conn.execute("SELECT id FROM fpos WHERE created_by=? ORDER BY id DESC LIMIT 1",(uid,)).fetchone()[0]
            conn.execute("UPDATE users SET fpo_id=? WHERE id=?",(fpo_id,uid))
        conn.commit()
    except Exception as e:
        conn.rollback();conn.close();raise HTTPException(409,"Phone number already registered") from e
    conn.close()
    return {"message":"Registration successful","user_id":uid,"role":role}
@router.post("/login")
def login(x:LoginIn):
    conn=get_db();u=conn.execute("SELECT id,name,phone,role,location,language,password,fpo_id FROM users WHERE phone=?",(x.phone.strip(),)).fetchone();conn.close()
    if not u or hash_password(x.password)!=u["password"]: raise HTTPException(401,"Invalid phone number or password")
    token=create_token(u["id"],u["role"])
    return {"message":"Login successful","access_token":token,"token_type":"bearer","user":{k:u[k] for k in ["id","name","phone","role","location","language"]}|{"fpo_id":u["fpo_id"]}}
@router.post("/logout")
def logout(): return {"message":"Logout successful"}
@router.get("/me")
def me(current=Depends(get_current_user)):
    uid,role=current;conn=get_db();u=conn.execute("SELECT id,name,phone,role,location,language,fpo_id FROM users WHERE id=?",(uid,)).fetchone();conn.close()
    if not u: raise HTTPException(404,"User not found")
    return dict(u)
