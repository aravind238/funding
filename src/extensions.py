from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS

# initialize our db
db = SQLAlchemy()
bcrypt = Bcrypt()
cors = CORS(expose_headers="Current-Date")

def register_extensions(app):
    """
    Register Flask extensions
    """
    bcrypt.init_app(app)
    cors.init_app(app)
