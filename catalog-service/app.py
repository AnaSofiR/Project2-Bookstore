from flask import Flask
from extensions import db
from controllers.book_controller import book

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://bookstore_user:bookstore_pass@<DB_HOST>:3306/bookstore'

db.init_app(app)
app.register_blueprint(book, url_prefix='/book')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5002, debug=True)
