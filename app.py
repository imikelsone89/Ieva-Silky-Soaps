from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for flash messages

def get_db_connection():
    """
    Create and return a connection to the SQLite database
    """
    db = Path(__file__).parent / "silky_soaps_db.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    conn = get_db_connection()
    reviews = conn.execute("""
        SELECT reviews.id, reviews.user_name, reviews.review_text,
               reviews.product_id, products.name AS product_name
        FROM reviews
        JOIN products ON reviews.product_id = products.id
        ORDER BY reviews.id DESC
    """).fetchall()
    conn.close()

    # Debug: print the reviews to your terminal/log
    print("Fetched reviews:")
    for review in reviews:
        print(dict(review))  # This will show each review's data

    return render_template("index.html", reviews=reviews)
    

@app.route("/produkti")
def products():
    conn = get_db_connection()
    products = conn.execute("""
        SELECT products.*, price.price AS price
        FROM products
        LEFT JOIN price ON products.price_id = price.id
    """).fetchall()
    conn.close()
    return render_template("products.html", products=products)

@app.route("/produkti/<int:product_id>")
def products_show(product_id):
    conn = get_db_connection()
    product = conn.execute("""
        SELECT products.*, price.price AS price, properties.properties AS properties, ingredients.ingredients AS ingredients
        FROM products
        LEFT JOIN price ON products.price_id = price.id
        LEFT JOIN properties ON products.properties_id = properties.id
        LEFT JOIN ingredients ON products.ingredients_id = ingredients.id
        WHERE products.id = ?
    """, (product_id,)).fetchone()
    conn.close()
    if product is None:
        return "Product not found", 404
    return render_template("products_show.html", product=product)

@app.route("/par-mums")
def about():
    return render_template("about.html")

#Update
@app.route("/reviews/add", methods=["GET", "POST"])
def add_review():
    if request.method == "GET":
        # Fetch all products to populate the dropdown
        conn = get_db_connection()
        products = conn.execute("SELECT id, name FROM products").fetchall()
        conn.close()

        return render_template("add_review.html", products=products)

    elif request.method == "POST":
        # Handle form submission
        product_id = request.form.get("product_id")
        user_name = request.form.get("user_name", "").strip()
        review_text = request.form.get("review_text", "").strip()

        # Validate form inputs
        if not product_id or not user_name or not review_text:
            flash("Visi lauki ir obligāti!", "error")
            return redirect(url_for("add_review"))

        # Ensure product_id is valid
        conn = get_db_connection()
        product = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            flash("Izvēlētais produkts neeksistē!", "error")
            conn.close()
            return redirect(url_for("add_review"))

        # Insert review into database
        try:
            conn.execute("""
                INSERT INTO reviews (product_id, user_name, review_text)
                VALUES (?, ?, ?)
            """, (product_id, user_name, review_text))
            conn.commit()
        except sqlite3.Error as e:
            flash(f"Database error: {e}", "error")
            return redirect(url_for("add_review"))
        finally:
            conn.close()

        flash("Atsauksme pievienota!", "success")
        return redirect(url_for("view_reviews", product_id=product_id))
    
@app.route("/product/<int:product_id>/reviews", methods=["GET"], endpoint="view_reviews")
def view_reviews(product_id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    reviews = conn.execute("SELECT * FROM reviews WHERE product_id = ?", (product_id,)).fetchall()
    conn.close()

    if not product:
        flash("Product not found!", "error")
        return redirect(url_for("home"))

    return render_template("review.html", product=product, reviews=reviews)

#Edit
@app.route("/review/<int:review_id>/edit", methods=["GET", "POST"])
def edit_review(review_id):
    conn = get_db_connection()
    review = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()

    if not review:
        conn.close()
        flash("Atsauksme netika atrasta!", "error")
        return redirect(url_for("home"))

    if request.method == "POST":
        new_user_name = request.form.get("user_name", "").strip()
        new_review_text = request.form.get("review_text", "").strip()

        if not new_user_name or not new_review_text:
            flash("Visi lauki ir obligāti!", "error")
            return redirect(url_for("edit_review", review_id=review_id))

        conn.execute("""
            UPDATE reviews
            SET user_name = ?, review_text = ?
            WHERE id = ?
        """, (new_user_name, new_review_text, review_id))
        conn.commit()
        conn.close()

        flash("Atsauksme tika atjaunināta!", "success")
        return redirect(url_for("view_reviews", product_id=review["product_id"]))

    conn.close()
    return render_template("edit_review.html", review=review)


@app.route("/review/<int:review_id>/delete", methods=["GET", "POST"])
def delete_review(review_id):
    conn = get_db_connection()
    review = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    conn.close()

    if not review:
        flash("Atsauksme netika atrasta!", "error")
        return redirect(url_for("home"))

    if request.method == "POST":
        conn = get_db_connection()
        conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        conn.commit()
        conn.close()

        flash("Atsauksme dzēsta!", "success")
        return redirect(url_for("view_reviews", product_id=review["product_id"]))

    # GET: show confirmation page
    return render_template("delete_review.html", review=review)

#reviews

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)