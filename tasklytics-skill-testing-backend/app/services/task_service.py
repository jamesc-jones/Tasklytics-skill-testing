from app.models import User, Task

def get_user_tasks(db, user_id: int):
    return db.query(Task).filter(Task.user_id == user_id).all()