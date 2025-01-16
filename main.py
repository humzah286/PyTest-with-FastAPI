from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.params import Depends
from sqlalchemy import create_engine, String
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column
from pydantic import BaseModel
from contextlib import asynccontextmanager
import hashlib
import time


class Item(BaseModel):
    id: str
    name: str
    description: Optional[str]

class ItemCreate(BaseModel):
    name: str
    description: Optional[str]

class ItemUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]


DATABASE_URL = "sqlite:///test.db"


def generate_id(name: str, description: str) -> str:
    raw_data = f"{name}-{description}-{time.time()}"
    return hashlib.sha256(raw_data.encode()).hexdigest()


class Base(DeclarativeBase):
    pass

class DBItem(Base):
    __tablename__ = "items"

    id = mapped_column(String(64), primary_key=True)  # Store the hash as a string
    name = mapped_column(String(30))
    description = mapped_column(String(100))


    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.id = generate_id(name, description)



engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create all database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: (Optional) Drop all tables or perform other cleanup
    # Base.metadata.drop_all(bind=engine)


app = FastAPI(lifespan=lifespan)


# Dependency to get the database session
def get_db():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


@app.post("/items")
def create_item(item: ItemCreate, db: Session = Depends(get_db)) -> Item:
    db_item = DBItem(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return Item(**db_item.__dict__)


@app.get("/items/{item_id}")
def read_item(item_id: str, db: Session = Depends(get_db)) -> Item:
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return Item(**db_item.__dict__)

@app.get("/items")
def read_all_items(db: Session = Depends(get_db)) -> List[Item]:
    db_items = db.query(DBItem).all()
    if db_items is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return [Item(**db_item.__dict__) for db_item in db_items]


@app.put("/items/{item_id}")
def update_item(item_id: str, item: ItemUpdate, db: Session = Depends(get_db)) -> Item:
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in item.dict().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return Item(**db_item.__dict__)


@app.delete("/items/{item_id}")
def delete_item(item_id: str, db: Session = Depends(get_db)) -> Item:
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return Item(**db_item.__dict__)


