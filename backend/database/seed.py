from backend.database.database import get_connection

properties = [
    {
        "title": "Habitación luminosa cerca de la Universidad",
        "operation": "alquiler",
        "property_type": "habitacion",
        "city": "León",
        "price": 390,
        "bedrooms": 1,
    },
    {
        "title": "Habitación individual en zona centro",
        "operation": "alquiler",
        "property_type": "habitacion",
        "city": "León",
        "price": 420,
        "bedrooms": 1,
    },
    {
        "title": "Piso de 3 habitaciones cerca del centro",
        "operation": "venta",
        "property_type": "vivienda",
        "city": "León",
        "price": 165000,
        "bedrooms": 3,
    },
    {
        "title": "Piso de 2 habitaciones en León",
        "operation": "alquiler",
        "property_type": "vivienda",
        "city": "León",
        "price": 850,
        "bedrooms": 2,
    },
]


connection = get_connection()

for property_data in properties:
    connection.execute(
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

connection.commit()
connection.close()

print("Propiedades de prueba creadas correctamente.")