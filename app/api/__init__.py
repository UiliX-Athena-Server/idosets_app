from flask_imp import ImpBlueprint
from flask_imp.config import ImpBlueprintConfig

bp = ImpBlueprint(
    __name__,
    ImpBlueprintConfig(
        enabled=True,
        url_prefix="/api",
    ),
)

bp.import_resources("routes")


@bp.errorhandler(404)
def api_not_found(_):
    return {"status": "error", "message": "Not found."}, 404


@bp.errorhandler(405)
def api_method_not_allowed(_):
    return {"status": "error", "message": "Method not allowed."}, 405


@bp.errorhandler(500)
def api_server_error(_):
    return {"status": "error", "message": "Something went wrong."}, 500
