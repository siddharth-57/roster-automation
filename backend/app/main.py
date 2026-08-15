from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.team_members import router as team_members_router


app = FastAPI()


# CORS (Cross-Origin Resource Sharing): A browser security mechanism that controls whether a frontend from one origin (e.g., localhost:5173) 
# can make requests to a backend on another origin (e.g., localhost:8000).
# The backend must explicitly allow the frontend's origin through CORS headers; 
# otherwise, the browser blocks the request.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(team_members_router)


@app.get("/")
def root():
    return {"message": "Roster Automation API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}