from fastapi import FastAPI
import bot

app = FastAPI()

@app.get("/")
def home():
    return bot.get_latest_signal()