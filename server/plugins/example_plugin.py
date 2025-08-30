from flask import Blueprint

example_blueprint = Blueprint('example_plugin', __name__)

@example_blueprint.route('/hello')
def hello():
    return "Hello from the example plugin!"

def register(app, _, __):
    app.register_blueprint(example_blueprint)
