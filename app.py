"""
API REST - Florería "Flor y Encanto"
Práctica: Creación y administración de un catálogo mediante una API REST (CRUD)
Tecnologías: Flask + SQLite + Render + Postman

Operaciones:
  POST   /products          -> Crear producto
  GET    /products          -> Consultar catálogo completo
  GET    /products/<id>     -> Consultar un producto por id
  PUT    /products/<id>     -> Actualizar un producto
  DELETE /products/<id>     -> Eliminar un producto

Seguridad: todas las rutas de /products requieren el encabezado X-API-KEY.
"""

from flask import Flask, request, jsonify
from functools import wraps
import sqlite3
import os

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DATABASE = os.environ.get("DATABASE_PATH", "floreria.db")
# La llave puede definirse como variable de entorno en Render (API_KEY).
# Si no se define, se usa este valor por defecto.
API_KEY = os.environ.get("API_KEY", "FLORERIA2026")


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # permite acceder a las columnas por nombre
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT    NOT NULL,
            price REAL    NOT NULL,
            stock INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Seguridad: decorador que valida el encabezado X-API-KEY
# ---------------------------------------------------------------------------
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-KEY")
        if key != API_KEY:
            return (
                jsonify(
                    {
                        "error": "Acceso no autorizado. "
                        "Debe proporcionar un encabezado X-API-KEY válido."
                    }
                ),
                401,
            )
        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    return jsonify(
        {
            "mensaje": "API REST - Florería 'Flor y Encanto'",
            "estado": "en línea",
            "endpoints": [
                "GET /products",
                "GET /products/<id>",
                "POST /products",
                "PUT /products/<id>",
                "DELETE /products/<id>",
            ],
        }
    )


@app.route("/products", methods=["GET"])
@require_api_key
def get_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows]), 200


@app.route("/products/<int:product_id>", methods=["GET"])
@require_api_key
def get_product(product_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Producto no encontrado"}), 404
    return jsonify(dict(row)), 200


@app.route("/products", methods=["POST"])
@require_api_key
def create_product():
    data = request.get_json(silent=True)
    if not data or "name" not in data or "price" not in data or "stock" not in data:
        return (
            jsonify(
                {"error": "Datos incompletos. Se requiere: name, price y stock."}
            ),
            400,
        )

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
        (data["name"], data["price"], data["stock"]),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return (
        jsonify(
            {
                "id": new_id,
                "name": data["name"],
                "price": data["price"],
                "stock": data["stock"],
            }
        ),
        201,
    )


@app.route("/products/<int:product_id>", methods=["PUT"])
@require_api_key
def update_product(product_id):
    data = request.get_json(silent=True) or {}

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Producto no encontrado"}), 404

    # Solo se actualizan los campos enviados; el resto conserva su valor.
    name = data.get("name", row["name"])
    price = data.get("price", row["price"])
    stock = data.get("stock", row["stock"])

    conn.execute(
        "UPDATE products SET name = ?, price = ?, stock = ? WHERE id = ?",
        (name, price, stock, product_id),
    )
    conn.commit()
    conn.close()

    return (
        jsonify({"id": product_id, "name": name, "price": price, "stock": stock}),
        200,
    )


@app.route("/products/<int:product_id>", methods=["DELETE"])
@require_api_key
def delete_product(product_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Producto no encontrado"}), 404

    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

    return (
        jsonify({"mensaje": f"Producto con id {product_id} eliminado correctamente"}),
        200,
    )


# Se crea la tabla al importar el módulo (necesario para gunicorn en Render).
init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
