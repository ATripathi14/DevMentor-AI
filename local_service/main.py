from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    """Basic health-check route confirming the server is running."""
    return {"message": "DevMentor is running"}