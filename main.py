"""Root application entrypoint for the News Article Management API.

Allows running the service via:
    $ uvicorn main:app --reload
or directly via:
    $ python main.py
"""

from app.main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
