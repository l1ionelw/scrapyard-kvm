from flask import Blueprint, Response

screenshot_blueprint = Blueprint('screenshot_plugin', __name__)
get_latest_frame = None
get_active_viewers = None

@screenshot_blueprint.route('/screenshot')
def screenshot():
    if get_active_viewers() == 0:
        return "No one is viewing right now.", 404
    frame = get_latest_frame()
    if frame:
        return Response(frame, mimetype='image/jpeg')
    else:
        return "No frame available yet.", 404

def register(app, frame_getter, viewers_getter):
    global get_latest_frame, get_active_viewers
    get_latest_frame = frame_getter
    get_active_viewers = viewers_getter
    app.register_blueprint(screenshot_blueprint)
