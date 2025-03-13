from flask_swagger_ui import get_swaggerui_blueprint

def init_swagger(app):
    SWAGGER_URL = "/apidocs"
    API_URL = "/swagger.yaml"

    swagger_ui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            "app_name": "My Flask API",
            "withCredentials": True  # 🔥 Importante per i cookie JWT
        }
    )

    app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)
