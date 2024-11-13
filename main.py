import os
import random
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Header
from pydantic import BaseModel, EmailStr, constr
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Float, Integer, String, ForeignKey, select, DateTime, insert
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import jwt
import pandas as pd

SECRET_KEY = "7093c2f408c24ced10236cd194bc0b08562c4e54ff5277b71e50d804a06b22e9"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES =  20

DATABASE_URL = "mysql+aiomysql://root:12345678@localhost/finance_manager"

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
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


class TrackingDB(Base):
    __tablename__ = "tracking"
    id = Column(Integer, primary_key=True, index=True)
    tracking_code = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_type = Column(String)
    ready_time = Column(DateTime)
    issues_count = Column(Integer)
    issues = Column(String)


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


async def get_db():
    async with SessionLocal() as session:
        yield session


async def get_current_user(token: str = Header(...), db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(UserDB).filter(UserDB.username == username))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@app.post("/upload-incomes/")
async def upload_incomes(file: UploadFile = File(...), current_user: UserDB = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    try:
        df = pd.read_excel(file.file)
        expected_columns = ["amount", "source"]
        issues = []
        valid_rows = []

        for index, row in df.iterrows():
            if row.isnull().all():
                issues.append(f"Row {index + 1} is empty")
            elif not all(col in row and pd.notna(row[col]) for col in expected_columns):
                issues.append(f"Row {index + 1} is missing income columns")
            else:
                valid_rows.append(IncomeDB(user_id=current_user.id, amount=row['amount'], source=row['source']))

        if len(df) < 300:
            if valid_rows:
                db.add_all(valid_rows)
                await db.commit()

            response = {"msg": "Incomes processed", "issues": issues}
            return response
        else:
            tracking_code = os.urandom(16).hex()
            ready_time = datetime.utcnow() + timedelta(minutes=1)

            await db.execute(insert(TrackingDB).values(
                tracking_code=tracking_code,
                user_id=current_user.id,
                file_type='income',
                ready_time=ready_time,
                issues_count=len(issues),
                issues=','.join(issues)
            ))
            await db.commit()

            return {"tracking code": tracking_code, "check back in minutes": 1}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")


@app.post("/upload-expenses/")
async def upload_expenses(file: UploadFile = File(...), current_user: UserDB = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    try:
        df = pd.read_excel(file.file)
        expected_columns = ["amount", "category", "description"]
        issues = []
        valid_rows = []

        for index, row in df.iterrows():
            if row.isnull().all():
                issues.append(f"Row {index + 1} is empty")
            elif not all(col in row and pd.notna(row[col]) for col in expected_columns):
                issues.append(f"Row {index + 1} is missing expense columns")
            else:
                valid_rows.append(ExpenseDB(user_id=current_user.id, amount=row['amount'], category=row['category'],
                                            description=row['description']))

        if len(df) < 300:
            if valid_rows:
                db.add_all(valid_rows)
                await db.commit()

            response = {"msg": "Expenses processed", "issues": issues}
            return response
        else:
            tracking_code = os.urandom(16).hex()
            ready_time = datetime.utcnow() + timedelta(minutes=1)

            await db.execute(insert(TrackingDB).values(
                tracking_code=tracking_code,
                user_id=current_user.id,
                file_type='expense',
                ready_time=ready_time,
                issues_count=len(issues),
                issues=','.join(issues)
            ))
            await db.commit()

            return {"tracking_code": tracking_code, "check_back_in_minutes": 1}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")


@app.get("/check-validation/{tracking_code}")
async def check_validation(tracking_code: str, token: str = Header(...), db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(TrackingDB).filter(TrackingDB.tracking_code == tracking_code))
    tracking_info = result.scalars().first()

    if tracking_info is None:
        raise HTTPException(status_code=404, detail="Tracking code not found")

    current_time = datetime.utcnow()
    if current_time < tracking_info.ready_time:
        wait_time = (tracking_info.ready_time - current_time).seconds // 60
        return {"msg": f"Check back in {wait_time} minutes"}
    else:
        response = {
            "msg": "Validation complete",
            "issues": tracking_info.issues.split(','),
            "issues_count": tracking_info.issues_count
        }



        return response


@app.post("/signup", status_code=status.HTTP_201_CREATED)
async def sign_up(user: User, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(UserDB).filter(UserDB.username == user.username))
        db_user = result.scalars().first()
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
        await db.commit()
        await db.refresh(new_user)

        return {"msg": "User created successfully"}

    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400,
                            detail="Database integrity error: Possible duplicate entry or constraint violation.")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")


@app.post("/signin")
async def sign_in(username: str, password: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserDB).filter(UserDB.username == username))
    user = result.scalars().first()
    if user is None or not pwd_context.verify(password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/Income")
async def add_income(income: Income, current_user: UserDB = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    new_income = IncomeDB(user_id=current_user.id, **income.dict())
    db.add(new_income)
    await db.commit()

    return {"msg": "Income added successfully"}


@app.post("/Expense")
async def add_expense(expense: Expense, current_user: UserDB = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    new_expense = ExpenseDB(user_id=current_user.id, **expense.dict())
    db.add(new_expense)
    await db.commit()

    return {"msg": "Expense added successfully"}


@app.put("/Update Income")
async def update_income(income_id: int, income: Income, current_user: UserDB = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IncomeDB).filter(IncomeDB.id == income_id, IncomeDB.user_id == current_user.id))
    db_income = result.scalars().first()
    if db_income is None:
        raise HTTPException(status_code=404, detail="Income not found")

    for key, value in income.dict().items():
        setattr(db_income, key, value)
    await db.commit()

    return {"msg": "Income updated successfully"}


@app.put("/expense/{expense_id}")
async def update_expense(expense_id: int, expense: Expense, current_user: UserDB = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ExpenseDB).filter(ExpenseDB.id == expense_id, ExpenseDB.user_id == current_user.id))
    db_expense = result.scalars().first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    for key, value in expense.dict().items():
        setattr(db_expense, key, value)
    await db.commit()

    return {"msg": "Expense updated successfully"}


@app.delete("/income/{income_id}")
async def delete_income(income_id: int, current_user: UserDB = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IncomeDB).filter(IncomeDB.id == income_id, IncomeDB.user_id == current_user.id))
    db_income = result.scalars().first()
    if db_income is None:
        raise HTTPException(status_code=404, detail="Income not found")

    await db.delete(db_income)
    await db.commit()

    return {"msg": "Income deleted successfully"}


@app.delete("/expense/{expense_id}")
async def delete_expense(expense_id: int, current_user: UserDB = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ExpenseDB).filter(ExpenseDB.id == expense_id, ExpenseDB.user_id == current_user.id))
    db_expense = result.scalars().first()
    if db_expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")

    await db.delete(db_expense)
    await db.commit()

    return {"msg": "Expense deleted successfully"}


@app.get("/financial-summary/")
async def financial_summary(current_user: UserDB = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return {"msg": "Financial summary fetched successfully"}
