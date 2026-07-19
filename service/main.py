from fastapi import FastAPI
import config

app = FastAPI(title="Varve", version="0.1.0")


@app.on_event("startup")
def on_startup():
    config.validate_config()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_name": config.MODEL_NAME,
        "datahub_gms_url": config.DATAHUB_GMS_URL,
    }