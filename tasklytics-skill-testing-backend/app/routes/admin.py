from fastapi import Depends, APIRouter
from app.auth.auth_dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/test")
def admin_test(admin = Depends(require_admin)):
    return {"message": "Admin access granted"}