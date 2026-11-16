from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from functools import wraps
from werkzeug.utils import secure_filename
import time

BASE = Path(__file__).parent
DB = BASE / 'bishe.db'
UP = BASE / 'static' / 'uploads'
UP.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'bishe-coffee-change-this-secret-key'
ADMIN_PASSWORD = 'bishe123'
CATS = ['Coffee', 'Hot Drinks', 'Cold Drinks', 'Food', 'Pastry']
PAYMENTS = {
    'CBE': {'account': '1000620790471', 'name': 'Adam Getachew'},
    'Telebirr': {'phone': '0989629972', 'name': 'Adam'}
}
START = [
('Ethiopian Coffee','የኢትዮጵያ ቡና',80,'Coffee','https://images.unsplash.com/photo-1498804103079-a6351b050096?auto=format&fit=crop&w=900&q=80','Fresh Ethiopian coffee with a rich traditional aroma.'),
('Macchiato','ማኪያቶ',100,'Coffee','https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=900&q=80','Espresso topped with smooth steamed milk.'),
('Latte','ላቴ',120,'Hot Drinks','https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=900&q=80','Creamy espresso blended with steamed milk.'),
('Iced Coffee','አይስድ ቡና',140,'Cold Drinks','https://images.unsplash.com/photo-1517701604599-bb29b565090c?auto=format&fit=crop&w=900&q=80','Refreshing chilled coffee served over ice.'),
('Fresh Juice','ትኩስ ጭማቂ',130,'Cold Drinks','https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=900&q=80','Fresh seasonal fruit juice.'),
('Pizza','ፒዛ',350,'Food','https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=900&q=80','Fresh pizza with premium ingredients.'),
('Classic Burger','በርገር',300,'Food','https://images.unsplash.com/photo-1568901346375-23c9450c58ab?auto=format&fit=crop&w=900&q=80','Juicy burger with fresh vegetables.'),
('Fresh Pastry','ፓስትሪ',100,'Pastry','https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&w=900&q=80','Freshly baked pastry, perfect with coffee.')
]

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = db()
    c.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,amharic TEXT,price REAL NOT NULL,category TEXT,image TEXT,description TEXT)")
    if c.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 0:
        c.executemany('INSERT INTO products(name,amharic,price,category,image,description) VALUES(?,?,?,?,?,?)', START)
    c.commit()
    c.close()

def auth(f):
    @wraps(f)
    def w(*a, **k):
        return f(*a, **k) if session.get('admin') else redirect(url_for('login'))
    return w

@app.context_processor
def ctx():
    return {'categories': CATS, 'payments': PAYMENTS}

@app.route('/')
def menu():
    cat = request.args.get('category', 'All')
    q = request.args.get('q', '').strip()
    c = db()
    sql = 'SELECT * FROM products WHERE (name LIKE ? OR amharic LIKE ? OR description LIKE ?)'
    args = [f'%{q}%'] * 3
    if cat in CATS:
        sql += ' AND category=?'
        args.append(cat)
    products = c.execute(sql + ' ORDER BY id DESC', args).fetchall()
    c.close()
    return render_template('menu.html', products=products, active=cat, q=q)

@app.route('/manage-bishe-2026', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return redirect(url_for('manage'))
    if request.method == 'POST':
        flash('Incorrect password.')
    return render_template('login.html')

@app.route('/manage-bishe-2026/products')
@auth
def manage():
    c = db()
    products = c.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    c.close()
    return render_template('manage.html', products=products)

@app.post('/manage-bishe-2026/save')
@auth
def save_product():
    product_id = request.form.get('id', '').strip()
    name = request.form.get('name', '').strip()
    amharic = request.form.get('amharic', '').strip()
    category = request.form.get('category', 'Coffee').strip()
    description = request.form.get('description', '').strip()
    image_url = request.form.get('image_url', '').strip()
    try:
        price = float(request.form.get('price', 0))
    except ValueError:
        flash('Please enter a valid price.')
        return redirect(url_for('manage'))
    if not name or price < 0:
        flash('Product name and valid price are required.')
        return redirect(url_for('manage'))

    image = image_url
    f = request.files.get('image')
    if f and f.filename:
        ext = Path(f.filename).suffix.lower()
        if ext not in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}:
            flash('Invalid image type. Use PNG, JPG, JPEG, WEBP or GIF.')
            return redirect(url_for('manage'))
        fn = f'{Path(secure_filename(f.filename)).stem[:50]}-{time.time_ns()}{ext}'
        f.save(UP / fn)
        image = url_for('static', filename='uploads/' + fn)

    c = db()
    if product_id:
        old = c.execute('SELECT image FROM products WHERE id=?', (product_id,)).fetchone()
        if not image and old:
            image = old['image'] or ''
        c.execute('UPDATE products SET name=?,amharic=?,price=?,category=?,image=?,description=? WHERE id=?',
                  (name, amharic, price, category, image, description, product_id))
        flash('Product updated successfully.')
    else:
        c.execute('INSERT INTO products(name,amharic,price,category,image,description) VALUES(?,?,?,?,?,?)',
                  (name, amharic, price, category, image, description))
        flash('Product added successfully.')
    c.commit()
    c.close()
    return redirect(url_for('manage'))

@app.post('/manage-bishe-2026/delete/<int:pid>')
@auth
def delete_product(pid):
    c = db()
    c.execute('DELETE FROM products WHERE id=?', (pid,))
    c.commit()
    c.close()
    flash('Product deleted.')
    return redirect(url_for('manage'))

@app.get('/manage-bishe-2026/logout')
def logout():
    session.clear()
    return redirect(url_for('menu'))

init()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
