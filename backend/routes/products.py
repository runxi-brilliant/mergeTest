from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from bson import ObjectId
from datetime import datetime

from utils.database import get_database
from utils.security import get_current_user
from models.product import ProductCreate, ProductResponse, ProductInDB

from typing import Optional
from fastapi import Query
router = APIRouter(prefix="/products", tags=["Products"])


def _to_response(doc: dict) -> ProductResponse:
    # ProductResponse 的 config 里允许 alias，并且 id/seller_id 是 str
    return ProductResponse(
        id=str(doc["_id"]),
        seller_id=str(doc["seller_id"]),
        title=doc["title"],
        description=doc["description"],
        price=doc["price"],
        category=doc["category"],
        condition=doc["condition"],
        sustainable=doc.get("sustainable", False),
        images=doc.get("images", []),
        status=doc.get("status", "available"),
        views=doc.get("views", 0),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )


@router.get("", response_model=List[ProductResponse])
async def list_products(sustainable: Optional[bool] = Query(default=None)):
    db = get_database()

    query = {}
    if sustainable is not None:
        query["sustainable"] = sustainable

    docs = await db.products.find(query).sort("created_at", -1).to_list(length=200)
    return [_to_response(d) for d in docs]


@router.get("/{id}", response_model=ProductResponse)
async def get_product(id: str):
    db = get_database()

    try:
        pid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")

    doc = await db.products.find_one({"_id": pid})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")

    # 👇 每次看详情，浏览数 +1
    await db.products.update_one({"_id": pid}, {"$inc": {"views": 1}})
    doc = await db.products.find_one({"_id": pid})


    return _to_response(doc)

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()

    # 先查一下 user 存不存在（顺便后面你加 verified 就在这里）
    try:
        uid = ObjectId(current_user["user_id"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user id")

    user = await db.users.find_one({"_id": uid})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="User not verified")

    now = datetime.utcnow()
    doc = ProductInDB(
        seller_id=uid,
        **payload.model_dump(),
        created_at=now,
        updated_at=now,
    ).model_dump(by_alias=True)

    res = await db.products.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _to_response(doc)


@router.put("/{id}", response_model=ProductResponse)
async def update_product(id: str, payload: ProductCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()

    try:
        pid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")

    existing = await db.products.find_one({"_id": pid})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    # ✅ 1) 当前用户 id
    try:
        uid = ObjectId(current_user["user_id"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user id")

    # ✅ 2) 只有 owner 才能改
    if str(existing["seller_id"]) != str(uid):
        raise HTTPException(status_code=403, detail="Forbidden")


    # 先不做 owner/verified，下一步再加（避免你一下子炸太多）
    now = datetime.utcnow()
    await db.products.update_one(
        {"_id": pid},
        {"$set": {**payload.model_dump(), "updated_at": now}}
    )

    updated = await db.products.find_one({"_id": pid})
    return _to_response(updated)


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_product(id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()

    try:
        pid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")

    existing = await db.products.find_one({"_id": pid})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    # ✅ 1) 当前用户 id
    try:
        uid = ObjectId(current_user["user_id"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user id")

    # ✅ 2) 只有 owner 才能删
    if str(existing["seller_id"]) != str(uid):
        raise HTTPException(status_code=403, detail="Forbidden")

    await db.products.delete_one({"_id": pid})
    return {"ok": True}