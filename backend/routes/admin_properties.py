import base64

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.database.database import get_connection
from backend.routes.study_leads import _check_admin_key

router = APIRouter(prefix="/admin/properties")

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB por imagen


class PropertyRequest(BaseModel):
    title: str
    operation: str
    property_type: str
    city: str
    price: float
    bedrooms: int | None = None
    bathrooms: int | None = None
    available: bool = True


def _property_with_images(connection, property_id: int) -> dict:
    row = connection.execute(
        "SELECT * FROM properties WHERE id = ?", (property_id,)
    ).fetchone()

    if row is None:
        return None

    data = dict(row)

    images = connection.execute(
        "SELECT id, image_url FROM property_images WHERE property_id = ?",
        (property_id,),
    ).fetchall()

    data["images"] = [dict(image) for image in images]

    return data


@router.get("")
def list_all_properties(key: str | None = None):
    _check_admin_key(key)

    connection = get_connection()

    ids = connection.execute("SELECT id FROM properties ORDER BY id DESC").fetchall()
    properties = [_property_with_images(connection, row["id"]) for row in ids]

    connection.close()

    return properties


@router.post("")
def create_property(request: PropertyRequest, key: str | None = None):
    _check_admin_key(key)

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO properties (title, operation, property_type, city, price, bedrooms, bathrooms, available)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request.title,
            request.operation,
            request.property_type,
            request.city,
            request.price,
            request.bedrooms,
            request.bathrooms,
            1 if request.available else 0,
        ),
    )

    property_id = cursor.lastrowid
    connection.commit()

    result = _property_with_images(connection, property_id)
    connection.close()

    return result


@router.put("/{property_id}")
def update_property(property_id: int, request: PropertyRequest, key: str | None = None):
    _check_admin_key(key)

    connection = get_connection()

    cursor = connection.execute(
        """
        UPDATE properties
        SET title = ?, operation = ?, property_type = ?, city = ?, price = ?,
            bedrooms = ?, bathrooms = ?, available = ?
        WHERE id = ?
        """,
        (
            request.title,
            request.operation,
            request.property_type,
            request.city,
            request.price,
            request.bedrooms,
            request.bathrooms,
            1 if request.available else 0,
            property_id,
        ),
    )

    connection.commit()

    if cursor.rowcount == 0:
        connection.close()
        raise HTTPException(status_code=404, detail="Propiedad no encontrada.")

    result = _property_with_images(connection, property_id)
    connection.close()

    return result


@router.delete("/{property_id}")
def delete_property(property_id: int, key: str | None = None):
    _check_admin_key(key)

    connection = get_connection()

    connection.execute("DELETE FROM property_images WHERE property_id = ?", (property_id,))
    cursor = connection.execute("DELETE FROM properties WHERE id = ?", (property_id,))

    connection.commit()
    connection.close()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada.")

    return {"status": "ok"}


@router.post("/{property_id}/images")
async def upload_property_image(property_id: int, key: str | None = None, file: UploadFile = File(...)):
    _check_admin_key(key)

    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Solo se aceptan imágenes JPG, PNG o WEBP.")

    contents = await file.read()

    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="La imagen no puede superar los 5 MB.")

    connection = get_connection()

    property_row = connection.execute(
        "SELECT id FROM properties WHERE id = ?", (property_id,)
    ).fetchone()

    if property_row is None:
        connection.close()
        raise HTTPException(status_code=404, detail="Propiedad no encontrada.")

    encoded = base64.b64encode(contents).decode("ascii")
    data_url = f"data:{file.content_type};base64,{encoded}"

    cursor = connection.execute(
        "INSERT INTO property_images (property_id, image_url) VALUES (?, ?)",
        (property_id, data_url),
    )

    connection.commit()

    image_id = cursor.lastrowid
    connection.close()

    return {"id": image_id, "image_url": data_url}


@router.delete("/images/{image_id}")
def delete_property_image(image_id: int, key: str | None = None):
    _check_admin_key(key)

    connection = get_connection()

    cursor = connection.execute("DELETE FROM property_images WHERE id = ?", (image_id,))
    connection.commit()
    connection.close()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")

    return {"status": "ok"}
