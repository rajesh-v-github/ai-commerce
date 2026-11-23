from app.database.db import SessionLocal
from app.models.product import Product

products = [
    {
        "name": "Wireless Earbuds",
        "description": "Bluetooth earbuds with noise cancellation",
        "category": "Audio",
        "price": 2499,
        "stock": 40,
    },
    {
        "name": "Bluetooth Speaker",
        "description": "Portable bluetooth speaker",
        "category": "Audio",
        "price": 2999,
        "stock": 20,
    },
    {
        "name": "Gaming Mouse",
        "description": "RGB gaming mouse",
        "category": "Gaming Accessories",
        "price": 1499,
        "stock": 50,
    },
    {
        "name": "Mechanical Keyboard",
        "description": "Gaming mechanical keyboard",
        "category": "Gaming Accessories",
        "price": 3499,
        "stock": 30,
    },
    {
        "name": "Laptop Backpack",
        "description": "Business laptop backpack",
        "category": "Laptop Bags & Cases",
        "price": 1999,
        "stock": 25,
    },
    {
        "name": "USB-C Hub",
        "description": "7-in-1 USB-C Hub",
        "category": "Computer Accessories",
        "price": 2499,
        "stock": 15,
    },
    {
        "name": "Webcam HD",
        "description": "1080P conference webcam",
        "category": "Webcams & Video Conferencing",
        "price": 3299,
        "stock": 18,
    },
    {
        "name": "Wireless Keyboard",
        "description": "Wireless office keyboard",
        "category": "Keyboards & Mice",
        "price": 1799,
        "stock": 35,
    },
    {
        "name": "Wireless Mouse",
        "description": "Office wireless mouse",
        "category": "Keyboards & Mice",
        "price": 999,
        "stock": 45,
    },
    {
        "name": "Laptop Pro 14",
        "description": "Business productivity laptop",
        "category": "Laptops",
        "price": 49999,
        "stock": 12,
    },
    {
        "name": "Gaming Laptop X",
        "description": "High performance gaming laptop",
        "category": "Laptops",
        "price": 89999,
        "stock": 8,
    },
    {
        "name": "Smart Watch",
        "description": "Fitness tracking smartwatch",
        "category": "Wearables",
        "price": 5999,
        "stock": 22,
    },
    {
        "name": "Power Bank",
        "description": "20000mAh power bank",
        "category": "Power & Charging",
        "price": 1599,
        "stock": 60,
    },
    {
        "name": "Bluetooth Headset",
        "description": "Call center bluetooth headset",
        "category": "Audio",
        "price": 3499,
        "stock": 27,
    },
    {
        "name": "Monitor 24",
        "description": "24 inch IPS monitor",
        "category": "Monitors & Displays",
        "price": 9999,
        "stock": 10,
    },
]

db = SessionLocal()

for item in products:
    db.add(Product(**item))

db.commit()
db.close()

print("Products seeded successfully")
