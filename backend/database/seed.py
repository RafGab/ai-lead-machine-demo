from backend.database.database import get_connection

properties = [
    {
        "title": "Habitación luminosa cerca de la Universidad",
        "operation": "alquiler",
        "property_type": "habitacion",
        "city": "León",
        "price": 390,
        "bedrooms": 1,
        "image": "/properties/hab1_universidad.jpeg",
    },
    {
        "title": "Habitación individual en zona centro",
        "operation": "alquiler",
        "property_type": "habitacion",
        "city": "León",
        "price": 420,
        "bedrooms": 1,
        "image": "/properties/hab1_centro.jpeg",
    },
    {
        "title": "Piso de 3 habitaciones cerca del centro",
        "operation": "venta",
        "property_type": "vivienda",
        "city": "León",
        "price": 165000,
        "bedrooms": 3,
        "image": "/properties/vivienda-leon-1.svg",
    },
    {
        "title": "Piso de 2 habitaciones en León",
        "operation": "alquiler",
        "property_type": "vivienda",
        "city": "León",
        "price": 850,
        "bedrooms": 2,
        "image": "/properties/vivienda-leon-2.svg",
    },
    {
        "title": "Piso de 2 habitaciones en Valladolid",
        "operation": "alquiler",
        "property_type": "vivienda",
        "city": "Valladolid",
        "price": 650,
        "bedrooms": 2,
        "image": "/properties/vivienda-valladolid-1.svg",
    },
    {
        "title": "Habitación cerca del campus en Valladolid",
        "operation": "alquiler",
        "property_type": "habitacion",
        "city": "Valladolid",
        "price": 300,
        "bedrooms": 1,
        "image": "/properties/habitacion-valladolid-1.svg",
    },
    {
        "title": "Piso de 2 habitaciones en Gijón",
        "operation": "alquiler",
        "property_type": "vivienda",
        "city": "Gijón",
        "price": 700,
        "bedrooms": 2,
        "image": "/properties/vivienda-gijon-1.svg",
    },
    {
        "title": "Piso de 3 habitaciones cerca de la playa en Gijón",
        "operation": "venta",
        "property_type": "vivienda",
        "city": "Gijón",
        "price": 175000,
        "bedrooms": 3,
        "image": "/properties/vivienda-gijon-2.svg",
    },
    {
        "title": "Piso de 3 habitaciones en Oviedo",
        "operation": "venta",
        "property_type": "vivienda",
        "city": "Oviedo",
        "price": 140000,
        "bedrooms": 3,
        "image": "/properties/vivienda-oviedo-1.svg",
    },
    {
        "title": "Piso de 2 habitaciones en Oviedo",
        "operation": "alquiler",
        "property_type": "vivienda",
        "city": "Oviedo",
        "price": 680,
        "bedrooms": 2,
        "image": "/properties/vivienda-oviedo-2.svg",
    },
    {
        "title": "Piso de 2 habitaciones en Burgos",
        "operation": "alquiler",
        "property_type": "vivienda",
        "city": "Burgos",
        "price": 600,
        "bedrooms": 2,
        "image": "/properties/vivienda-burgos-1.svg",
    },
    {
        "title": "Habitación individual en Burgos",
        "operation": "alquiler",
        "property_type": "habitacion",
        "city": "Burgos",
        "price": 280,
        "bedrooms": 1,
        "image": "/properties/habitacion-burgos-1.svg",
    },
    {
        "title": "Piso de 3 habitaciones en Santander",
        "operation": "alquiler",
        "property_type": "vivienda",
        "city": "Santander",
        "price": 900,
        "bedrooms": 3,
        "image": "/properties/vivienda-santander-1.svg",
    },
    {
        "title": "Piso de 2 habitaciones en Santander",
        "operation": "venta",
        "property_type": "vivienda",
        "city": "Santander",
        "price": 190000,
        "bedrooms": 2,
        "image": "/properties/vivienda-santander-2.svg",
    },
    {
        "title": "Piso de 2 habitaciones en Bilbao",
        "operation": "alquiler",
        "property_type": "vivienda",
        "city": "Bilbao",
        "price": 950,
        "bedrooms": 2,
        "image": "/properties/vivienda-bilbao-1.svg",
    },
    {
        "title": "Piso de 3 habitaciones en Bilbao",
        "operation": "venta",
        "property_type": "vivienda",
        "city": "Bilbao",
        "price": 220000,
        "bedrooms": 3,
        "image": "/properties/vivienda-bilbao-2.svg",
    },
    {
        "title": "Piso de 2 habitaciones en Madrid",
        "operation": "alquiler",
        "property_type": "vivienda",
        "city": "Madrid",
        "price": 1400,
        "bedrooms": 2,
        "image": "/properties/vivienda-madrid-1.svg",
    },
    {
        "title": "Habitación en piso compartido en Madrid",
        "operation": "alquiler",
        "property_type": "habitacion",
        "city": "Madrid",
        "price": 550,
        "bedrooms": 1,
        "image": "/properties/habitacion-madrid-1.svg",
    },
]


connection = get_connection()

connection.execute("DELETE FROM property_images")
connection.execute("DELETE FROM properties")

for property_data in properties:
    cursor = connection.execute(
        """
        INSERT INTO properties
        (title, operation, property_type, city, price, bedrooms)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            property_data["title"],
            property_data["operation"],
            property_data["property_type"],
            property_data["city"],
            property_data["price"],
            property_data["bedrooms"],
        ),
    )

    image_url = property_data.get("image")

    if image_url:
        connection.execute(
            """
            INSERT INTO property_images (property_id, image_url)
            VALUES (?, ?)
            """,
            (cursor.lastrowid, image_url),
        )

connection.commit()
connection.close()

print("Propiedades de prueba creadas correctamente.")