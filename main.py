import os
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, constr
from sqlalchemy import create_engine, Column, Float, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from fastapi import Header
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import jwt
import pandas as pd
from fastapi import File, UploadFile
from typing import List

SECRET_KEY = "7093c2f408c24ced10236cd194bc0b08562c4e54ff5277b71e50d804a06b22e9"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 40

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

DATABASE_URL = "mysql+mysqlconnector://root:12345678@localhost/finance_manager"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    date_of_birth = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

class IncomeDB(Base):
    __tablename__ = "incomes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    source = Column(String)

class ExpenseDB(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    category = Column(String)
    description = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()

class User(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    username: constr(min_length=6, max_length=15)
    email: EmailStr
    password: str

class Income(BaseModel):
    amount: float
    source: str

class Expense(BaseModel):
    amount: float
    category: str
    description: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Header(...), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def update_excel_file(user_id: int, db: Session):
    incomes = db.query(IncomeDB).filter(IncomeDB.user_id == user_id).all()
    expenses = db.query(ExpenseDB).filter(ExpenseDB.user_id == user_id).all()

    income_data = [{"amount": income.amount, "source": income.source} for income in incomes]
    expense_data = [{"amount": expense.amount, "category": expense.category, "description": expense.description} for expense in expenses]

    df_incomes = pd.DataFrame(income_data)
    df_expenses = pd.DataFrame(expense_data)

    directory = "/Users/mohammad/Desktop/Project"
    os.makedirs(directory, exist_ok=True)

    file_path = os.path.join(directory, f'financial_summary_user_{user_id}.xlsx')
    with pd.ExcelWriter(file_path) as writer:
        df_incomes.to_excel(writer, sheet_name='Incomes', index=False)
        df_expenses.to_excel(writer, sheet_name='Expenses', index=False)

@app.post("/signup/", status_code=status.HTTP_201_CREATED)
async def sign_up(user: User, db: Session = Depends(get_db)):
    try:
        db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        hashed_password = pwd_context.hash(user.password)
        new_user = UserDB(
            first_name=user.first_name,
            last_name=user.last_name,
            date_of_birth=user.date_of_birth,
            username=user.username,
            email=user.email,
            password=hashed_password
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {"msg": "User created successfully"}

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400,
                            detail="Database integrity error: Possible duplicate entry or constraint violation.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")

@app.post("/signin/")
async def sign_in(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None or not pwd_context.verify(password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/income/")
async def add_income(income: Income, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    new_income = IncomeDB(user_id=current_user.id, **income.dict())
    db.add(new_income)
    db.commit()

    update_excel_file(current_user.id, db)

    return {"msg": "Income added successfully"}


@app.post("/expense/")
async def add_expense(expense: Expense, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    new_expense = ExpenseDB(user_id=current_user.id, **expense.dict())
    db.add(new_expense)
    db.commit()

    update_excel_file(current_user.id, db)

    return {"msg": "Expense added successfully"}

@app.put("/income/{income_id}")
async def update_income(income_id: int, income: Income, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    db_income = db.query(IncomeDB).filter(IncomeDB.id == income_id, IncomeDB.user_id == current_user.id).first()
    if db_income is None:
        raise HTTPException(status_code=404, detail="Income not found")

    for key, value in income.dict().items():
        setattr(db_income, key, value)
    db.commit()

    update_excel_file(current_user.id, db)

    return {"msg": "Income updated successfully"}

@app.put("/expense/{expense_id}")
async def update_expense(expense_id: int, expense: Expense, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    db_expense = db.query(ExpenseDB).filter(ExpenseDB.id == expense_id, ExpenseDB.user_id == current_user.id).first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    for key, value in expense.dict().items():
        setattr(db_expense, key, value)
    db.commit()

    update_excel_file(current_user.id, db)

    return {"msg": "Expense updated successfully"}

@app.delete("/income/{income_id}")
async def delete_income(income_id: int, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    db_income = db.query(IncomeDB).filter(IncomeDB.id == income_id, IncomeDB.user_id == current_user.id).first()
    if db_income is None:
        raise HTTPException(status_code=404, detail="Income not found")

    db.delete(db_income)
    db.commit()

    update_excel_file(current_user.id, db)

    return {"msg": "Income deleted successfully"}

@app.delete("/expense/{expense_id}")
async def delete_expense(expense_id: int, current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    db_expense = db.query(ExpenseDB).filter(ExpenseDB.id == expense_id, ExpenseDB.user_id == current_user.id).first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(db_expense)
    db.commit()

    update_excel_file(current_user.id, db)

    return {"msg": "Expense deleted successfully"}

@app.get("/financial-summary/")
async def financial_summary(current_user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    update_excel_file(current_user.id, db)
    return {"msg": "Financial data exported to Excel successfully"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)