from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pathlib import Path
import asyncio
import json
import yaml
from typing import Dict, Any
import threading

from main import BenchmarkRunner

app = FastAPI(title="STT Benchmark Dashboard")

# Global state
benchmark_runner = None
benchmark_thread = None
is_running = False

# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

results_dir = Path(__file__).parent / "results"
results_dir.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main dashboard"""
    html_file = static_dir / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse(content="<h1>Dashboard not found. Please create static/index.html</h1>")

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/benchmark/start")
async def start_benchmark(background_tasks: BackgroundTasks):
    """Start benchmark in background"""
    global benchmark_runner, benchmark_thread, is_running
    
    if is_running:
        return {"status": "error", "message": "Benchmark already running"}
    
    def run_benchmark():
        global is_running
        is_running = True
        try:
            runner = BenchmarkRunner()
            global benchmark_runner
            benchmark_runner = runner
            runner.run()
        finally:
            is_running = False
    
    benchmark_thread = threading.Thread(target=run_benchmark, daemon=True)
    benchmark_thread.start()
    
    return {"status": "started", "message": "Benchmark started"}

@app.get("/api/benchmark/status")
async def get_status():
    """Get current benchmark status"""
    global benchmark_runner, is_running
    
    if benchmark_runner:
        status = benchmark_runner.get_status()
        status['is_running'] = is_running
        return status
    
    return {
        "status": "idle",
        "is_running": False,
        "message": "No benchmark running"
    }

@app.get("/api/benchmark/results")
async def get_results():
    """Get benchmark results"""
    global benchmark_runner
    
    if benchmark_runner:
        return benchmark_runner.get_results()
    
    # Try to load from file
    results_file = results_dir / "results.json"
    if results_file.exists():
        with open(results_file, 'r') as f:
            return json.load(f)
    
    return {}

@app.get("/api/visualizations")
async def list_visualizations():
    """List available visualization files"""
    viz_files = []
    for file in results_dir.glob("*.png"):
        viz_files.append({
            "name": file.stem,
            "filename": file.name,
            "url": f"/api/visualization/{file.name}"
        })
    return viz_files

@app.get("/api/visualization/{filename}")
async def get_visualization(filename: str):
    """Get a specific visualization"""
    file_path = results_dir / filename
    if file_path.exists() and file_path.suffix == '.png':
        return FileResponse(file_path, media_type="image/png")
    return JSONResponse({"error": "File not found"}, status_code=404)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    
    try:
        while True:
            status = await get_status()
            await websocket.send_json(status)
            await asyncio.sleep(1)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "STT Benchmark API"}

if __name__ == "__main__":
    import uvicorn
    
    # Load config
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    api_config = config.get('api', {})
    host = api_config.get('host', '0.0.0.0')
    port = api_config.get('port', 8000)
    reload = api_config.get('reload', False)
    
    print(f"Starting STT Benchmark Dashboard on http://{host}:{port}")
    uvicorn.run("api:app", host=host, port=port, reload=reload)