"""
Sentinel Drain - Main FastAPI Application
Hyperlocal Wastewater Biosurveillance Network for PHC-Level Outbreak Early-Warning.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import init_database, get_db_connection
from .seed_data import seed_all_data
from .routes import telemetry, incidents, forecasts, supply_chain, alerts, simulation

app = FastAPI(
    title="Sentinel Drain Biosurveillance Network API",
    description="Hyperlocal Wastewater Biosurveillance Network for PHC-Level Outbreak Early-Warning (Build with AI / Google Cloud)",
    version="1.1.0"
)

# Enable CORS for cross-origin frontend interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(telemetry.router)
app.include_router(incidents.router)
app.include_router(forecasts.router)
app.include_router(supply_chain.router)
app.include_router(alerts.router)
app.include_router(simulation.router)

# Mount frontend directory for static assets
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "frontend")

@app.on_event("startup")
def on_startup():
    """Ensure database is initialized and seeded on start."""
    init_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM nodes")
    node_count = cursor.fetchone()["count"]
    conn.close()

    if node_count == 0:
        print("[SentinelDrain] Database is empty. Seeding initial network...")
        seed_all_data()
    else:
        print(f"[SentinelDrain] Database online with {node_count} nodes.")

    # Start continuous live background sensor streaming
    simulation.start_background_streamer()
    print("[SentinelDrain] Live real-time background sensor stream started.")

@app.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "Sentinel Drain Cloud Pipeline",
        "version": "1.1.0",
        "district": "Gorakhpur Pilot Network",
        "target_audience": "State Health Department / Primary Health Centres"
    }

# Serve Dashboard index
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
