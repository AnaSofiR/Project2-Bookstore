from flask import Flask
from extensions import db, login_manager
from models.user import User
from controllers.auth_controller import auth

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookstore.db'

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


app.register_blueprint(auth)

if __name__ == '__main__':
    with app.app_context():
        # Debería mostrar 'sqlite:///bookstore.db'
        print(app.config['SQLALCHEMY_DATABASE_URI'])
        db.create_all()
    app.run(host="0.0.0.0", port=5001, debug=True)
