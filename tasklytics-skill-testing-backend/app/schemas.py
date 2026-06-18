from pydantic import BaseModel, EmailStr, Field
from pydantic import model_validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)
    confirm_password: str

    @model_validator(mode="after")
    def check_passwords(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    title: str
    description: str
    priority: str


class TaskUpdate(BaseModel):
    title: str
    description: str
    completed: bool














