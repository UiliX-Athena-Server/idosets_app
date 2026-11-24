from flask import Flask, render_template, request


def include(app: Flask):
    def handler(code: int):
        def handle(_error):
            if request.path.startswith("/api/"):
                return {"status": "error", "message": f"Error {code}"}, code
            return render_template(f"errors/{code}.html"), code

        return handle

    for status_code in (400, 401, 403, 404, 405, 500):
        app.register_error_handler(status_code, handler(status_code))
