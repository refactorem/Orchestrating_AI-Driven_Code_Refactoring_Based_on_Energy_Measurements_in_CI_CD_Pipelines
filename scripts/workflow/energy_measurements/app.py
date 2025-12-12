import os
import logging
import logging.config
import yaml
from flask import Flask, request
from flask_cors import CORS
from controllers.upload_controller import upload_blueprint
from controllers.result_controller import result_blueprint
from controllers.consumption_controller import consumption_blueprint
from controllers.refactor_compare import compare_blueprint
from db.db import db_session

if not os.path.exists('logs'):
    os.makedirs('logs')

with open('config/logging_config.yaml', 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)
access_logger = logging.getLogger("access_logger")

app = Flask(__name__)
CORS(app)

app.register_blueprint(upload_blueprint)
app.register_blueprint(result_blueprint)
app.register_blueprint(consumption_blueprint)
app.register_blueprint(compare_blueprint)

@app.before_request
def log_request_info():
    access_logger.info(f"{request.remote_addr} {request.method} {request.path}")

@app.teardown_appcontext
def shutdown_session(exception=None):
    if exception:
        logger.error(f"Error closing DB session: {exception}")
    else:
        logger.info("DB session closed successfully")
    db_session.remove()

if __name__ == "__main__":
    logger.info("Starting Flask server on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000)
