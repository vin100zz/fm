"""FastAPI app — a thin layer over `core` (CLAUDE.md: "api/ FastAPI,
couche mince au-dessus de core"). All game state lives in
`api.etat_serveur`; route modules only translate HTTP <-> core calls.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api import routes_clubs, routes_competitions, routes_joueurs, routes_matches, routes_monde, routes_partie
from api.etat_serveur import initialiser

DOSSIER_WEB = Path(__file__).resolve().parent.parent.parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialiser()
    yield


def creer_app() -> FastAPI:
    app = FastAPI(title="Football Manager Light", lifespan=lifespan)

    app.include_router(routes_monde.routeur, prefix="/api/monde", tags=["monde"])
    app.include_router(routes_clubs.routeur, prefix="/api/clubs", tags=["clubs"])
    app.include_router(routes_competitions.routeur, prefix="/api/competitions", tags=["competitions"])
    app.include_router(routes_joueurs.routeur, prefix="/api/joueurs", tags=["joueurs"])
    app.include_router(routes_matches.routeur, prefix="/api/matches", tags=["matches"])
    app.include_router(routes_partie.routeur, prefix="/api/partie", tags=["partie"])

    if DOSSIER_WEB.exists():
        app.mount("/", StaticFiles(directory=DOSSIER_WEB, html=True), name="web")

    return app


app = creer_app()
