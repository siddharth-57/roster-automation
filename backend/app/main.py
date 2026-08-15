from fastapi import FastAPI

from app.api.team_members import router as team_members_router


app = FastAPI()


app.include_router(team_members_router)


@app.get("/")
def root():
    return {"message": "Roster Automation API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}