from flask import Blueprint, current_app, request, jsonify, make_response

from yetiserver import model
from yetiserver.api.v1.utils import authenticate_user

model_management_blueprint = Blueprint('model_management', __name__)

@model_management_blueprint.route('/upload/<user_name>/<model_name>/', methods=["POST"])
def upload_model(user_name, model_name):
    """Uploads a decision tree model with the given name"""
    if not authenticate_user(user_name, request):
        return make_response("Authentication failed", 403)

    model_json = model.deserialize(request.get_json(force=True))
    print(model_json)
    current_app.model.store_model(user_name, model_name, model_json)
    return jsonify(success=True)


@model_management_blueprint.route('/<user_name>/<model_name>/predict/')
def predict_with_model(user_name, model_name):
    if not authenticate_user(user_name, request):
        return make_response("Authentication failed", 403)

    row = request.get_json(force=True)
    current_app.model_log.increment_predictions_counter(user_name, model_name)
    model_func = current_app.model.retrieve_model(user_name, model_name)
    if model_func:
        return jsonify(model_func(row))
    else:
        resp = jsonify("No Such Model")
        resp.status_code = 404
        return resp


