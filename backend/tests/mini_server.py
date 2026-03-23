from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/test")
def test():
    return {"status": "ok"}

if __name__ == "__main__":
    print("Starting minimal test server...")
    uvicorn.run(app, host="127.0.0.1", port=8001)
