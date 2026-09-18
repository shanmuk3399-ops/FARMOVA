import base64,hashlib,hmac
from datetime import datetime,timedelta
from fastapi import Header,HTTPException
SECRET_KEY="farmdirect-local-secret"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id,role):
    expiry=int((datetime.utcnow()+timedelta(days=7)).timestamp())
    data=f"{user_id}:{role}:{expiry}"
    sig=hmac.new(SECRET_KEY.encode(),data.encode(),hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{data}:{sig}".encode()).decode()

def get_current_user(authorization: str|None=Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401,"Authentication required")
    try:
        raw=base64.urlsafe_b64decode(authorization.split(" ",1)[1].encode()).decode()
        user_id,role,expiry,sig=raw.split(":")
        data=f"{user_id}:{role}:{expiry}"
        expected=hmac.new(SECRET_KEY.encode(),data.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,expected) or int(expiry)<int(datetime.utcnow().timestamp()):
            raise ValueError
        return int(user_id),role
    except Exception:
        raise HTTPException(401,"Invalid or expired token")

def optional_user(authorization: str|None=Header(default=None)):
    if not authorization: return None
    return get_current_user(authorization)
