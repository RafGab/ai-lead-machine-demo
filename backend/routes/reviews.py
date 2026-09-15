from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database.database import get_connection
from backend.routes.study_leads import _check_admin_key

router = APIRouter()


class ReviewRequest(BaseModel):
    name: str
    rating: int | None = None
    text: str


@router.post("/reviews")
def create_review(request: ReviewRequest):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO reviews (name, rating, text, published)
        VALUES (?, ?, ?, 0)
        """,
        (request.name, request.rating, request.text),
    )

    connection.commit()
    connection.close()

    return {
        "status": "ok",
        "message": "Gracias, tu reseña se publicará en cuanto la revisemos.",
    }


@router.get("/reviews")
def list_published_reviews():
    connection = get_connection()

    rows = connection.execute(
        "SELECT id, name, rating, text, created_at FROM reviews "
        "WHERE published = 1 ORDER BY created_at DESC"
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


@router.get("/reviews/pending")
def list_pending_reviews(key: str | None = None):
    _check_admin_key(key)

    connection = get_connection()

    rows = connection.execute(
        "SELECT * FROM reviews WHERE published = 0 ORDER BY created_at DESC"
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


@router.post("/reviews/{review_id}/publish")
def publish_review(review_id: int, key: str | None = None):
    _check_admin_key(key)

    connection = get_connection()

    cursor = connection.execute(
        "UPDATE reviews SET published = 1 WHERE id = ?", (review_id,)
    )

    connection.commit()
    connection.close()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Reseña no encontrada.")

    return {"status": "ok"}
