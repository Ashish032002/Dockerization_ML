from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

# Create an instance of FastAPI
app = FastAPI()

# Example data storage (In-memory database for testing)
fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]
fake_users_db = {"user1": {"name": "John Doe", "email": "john@example.com"}}

# Pydantic model for creating new items
class Item(BaseModel):
    name: str
    description: str = None
    price: float
    is_offer: bool = None

# Pydantic model for user
class User(BaseModel):
    name: str
    email: str
    age: int

# Root endpoint for checking if the API is running
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# Get a list of items
@app.get("/items/", response_model=List[dict])
def read_items(skip: int = 0, limit: int = 10):
    return fake_items_db[skip : skip + limit]

# Get a specific item by ID
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    if q:
        return {"item_id": item_id, "query": q}
    return {"item_id": item_id}

# Create a new item (testing POST request)
@app.post("/items/")
def create_item(item: Item):
    fake_items_db.append({"item_name": item.name})
    return {"message": "Item created", "item": item}

# Update an existing item (testing PUT request)
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_id": item_id, "item": item}

# Create a new user
@app.post("/users/")
def create_user(user: User):
    fake_users_db[user.name] = {"name": user.name, "email": user.email}
    return {"message": "User created", "user": user}

# Get user details
@app.get("/users/{username}")
def get_user(username: str):
    if username in fake_users_db:
        return fake_users_db[username]
    return {"message": "User not found"}

# Delete an item (testing DELETE request)
@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id < len(fake_items_db):
        deleted_item = fake_items_db.pop(item_id)
        return {"message": "Item deleted", "item": deleted_item}
    return {"message": "Item not found"}
