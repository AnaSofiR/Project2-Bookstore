from flask import Flask
from extensions import db
from controllers.purchase_controller import purchase
from controllers.payment_controller import payment
from controllers.delivery_controller import delivery
from models.delivery import DeliveryProvider

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
    app.config['SECRET_KEY'] = 'secretkey'

    db.init_app(app)
    app.register_blueprint(purchase)
    app.register_blueprint(payment)
    app.register_blueprint(delivery)

    with app.app_context():
        db.create_all()
        initialize_delivery_providers()

    return app

def initialize_delivery_providers():
    if DeliveryProvider.query.count() == 0:
        providers = [
            DeliveryProvider(name="DHL", coverage_area="Internacional", cost=50.0),
            DeliveryProvider(name="FedEx", coverage_area="Internacional", cost=45.0),
            DeliveryProvider(name="Envia", coverage_area="Nacional", cost=20.0),
            DeliveryProvider(name="Servientrega", coverage_area="Nacional", cost=15.0),
        ]
        db.session.bulk_save_objects(providers)
        db.session.commit()

app = create_app()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5003)
