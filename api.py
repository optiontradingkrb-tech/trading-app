from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    try:
        import bot
        data = bot.get_latest_signal()
        return {"status": "OK", "data": data}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}
