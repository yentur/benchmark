from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from pathlib import Path
import asyncio
import json
import yaml
from typing import Dict, Any, Set
import threading
import traceback
import io

from main import BenchmarkRunner

app = FastAPI(title="STT Benchmark Dashboard")

# Global state
benchmark_runner = None
benchmark_thread = None
is_running = False
current_sample = {"reference": "", "hypothesis": "", "sample_index": 0}
active_websockets: Set[WebSocket] = set()

# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

results_dir = Path(__file__).parent / "results"
results_dir.mkdir(exist_ok=True)

cache_dir = Path(__file__).parent / "cache"
cache_dir.mkdir(exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main dashboard"""
    html_file = static_dir / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse(content="""
        <html>
            <head><title>STT Benchmark</title></head>
            <body>
                <h1>Dashboard not found</h1>
                <p>Please create static/index.html</p>
                <p>API is running at <a href="/docs">/docs</a></p>
            </body>
        </html>
    """)


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    try:
        config_path = Path("config.yaml")
        if not config_path.exists():
            return JSONResponse(
                {"error": "config.yaml not found"},
                status_code=404
            )
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@app.get("/api/cache/status")
async def get_cache_status():
    """Check which models have cached results"""
    try:
        cached_models = []
        cache_file = cache_dir / "benchmark_cache.json"
        
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                cached_models = list(cache_data.keys())
        
        return {
            "cached_models": cached_models,
            "cache_file": str(cache_file),
            "cache_exists": cache_file.exists()
        }
    except Exception as e:
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@app.post("/api/benchmark/start")
async def start_benchmark(background_tasks: BackgroundTasks):
    """Start benchmark in background"""
    global benchmark_runner, benchmark_thread, is_running
    
    if is_running:
        return JSONResponse(
            {"status": "error", "message": "Benchmark already running"},
            status_code=400
        )
    
    def run_benchmark():
        global is_running, current_sample, benchmark_runner
        is_running = True
        
        try:
            print("\n" + "=" * 80)
            print("Starting benchmark from API...")
            print("=" * 80 + "\n")
            
            runner = BenchmarkRunner()
            benchmark_runner = runner
            
            # Set callback for sample updates
            def sample_callback(ref, hyp, idx):
                global current_sample
                current_sample = {
                    "reference": ref,
                    "hypothesis": hyp,
                    "sample_index": idx
                }
            
            runner.set_sample_callback(sample_callback)
            runner.run()
            
            print("\n" + "=" * 80)
            print("Benchmark completed successfully!")
            print("=" * 80 + "\n")
            
        except Exception as e:
            print(f"\n✗ Error in benchmark thread: {e}")
            traceback.print_exc()
        finally:
            is_running = False
            current_sample = {"reference": "", "hypothesis": "", "sample_index": 0}
            print("Benchmark thread finished")
    
    # Start benchmark in separate thread
    benchmark_thread = threading.Thread(target=run_benchmark, daemon=True, name="BenchmarkThread")
    benchmark_thread.start()
    
    return {
        "status": "started",
        "message": "Benchmark started in background"
    }


@app.get("/api/benchmark/status")
async def get_status():
    """Get current benchmark status - OPTIMIZED: Reduced data transfer"""
    global benchmark_runner, is_running, current_sample
    
    try:
        if benchmark_runner:
            status = benchmark_runner.get_status()
            status['is_running'] = is_running
            status['current_sample'] = current_sample
            status['thread_alive'] = benchmark_thread.is_alive() if benchmark_thread else False
            return status
        
        return {
            "status": "idle",
            "is_running": False,
            "message": "No benchmark running",
            "current_sample": {"reference": "", "hypothesis": "", "sample_index": 0},
            "thread_alive": False
        }
    except Exception as e:
        return JSONResponse(
            {"error": str(e), "status": "error"},
            status_code=500
        )


@app.get("/api/benchmark/results")
async def get_results():
    """Get benchmark results (from cache or running benchmark)"""
    global benchmark_runner
    
    try:
        # Try cache first
        cache_file = cache_dir / "benchmark_cache.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_results = json.load(f)
                
                # If benchmark is running, merge with new results
                if benchmark_runner:
                    try:
                        running_results = benchmark_runner.get_results()
                        cached_results.update(running_results)
                    except:
                        pass
                
                return cached_results
        
        # Otherwise return running results
        if benchmark_runner:
            return benchmark_runner.get_results()
        
        # Last resort: try results.json
        results_file = results_dir / "results.json"
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {}
        
    except Exception as e:
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@app.get("/api/model/{model_name}/examples")
async def get_model_examples(model_name: str, limit: int = 10):
    """Get example predictions for a specific model - WITH AUDIO PATHS"""
    try:
        # Try cache first
        cache_file = cache_dir / "benchmark_cache.json"
        results = None
        
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
        else:
            results_file = results_dir / "results.json"
            if results_file.exists():
                with open(results_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
        
        if not results:
            return JSONResponse(
                {"error": "No results found"},
                status_code=404
            )
        
        if model_name not in results:
            return JSONResponse(
                {"error": f"Model '{model_name}' not found in results"},
                status_code=404
            )
        
        detailed_results = results[model_name].get('detailed_results', [])
        
        if not detailed_results:
            return {
                "model": model_name,
                "examples": [],
                "message": "No detailed results available"
            }
        
        # Get diverse examples (good, medium, bad WER)
        sorted_results = sorted(detailed_results, key=lambda x: x.get('wer', 0))
        
        examples = []
        step = max(len(sorted_results) // limit, 1)
        
        for i in range(0, min(len(sorted_results), limit * step), step):
            if i < len(sorted_results):
                example = sorted_results[i].copy()
                # Add audio file availability check
                if 'id' in example:
                    example['has_audio'] = True  # We'll check this in frontend
                examples.append(example)
        
        return {
            "model": model_name,
            "examples": examples[:limit],
            "total_samples": len(detailed_results)
        }
        
    except Exception as e:
        return JSONResponse(
            {"error": str(e), "traceback": traceback.format_exc()},
            status_code=500
        )


@app.get("/api/audio/{sample_id}")
async def get_audio(sample_id: str):
    """Serve audio file for a sample - NEW ENDPOINT"""
    try:
        # Check if audio file exists in cache
        audio_files = list(cache_dir.glob(f"*{sample_id}*.wav"))
        
        if not audio_files:
            # Try to find by pattern matching
            audio_files = list(cache_dir.glob("*.wav"))
            matching = [f for f in audio_files if sample_id in f.name]
            if matching:
                audio_files = matching
        
        if not audio_files:
            return JSONResponse(
                {"error": "Audio file not found"},
                status_code=404
            )
        
        audio_file = audio_files[0]
        
        # Stream the audio file
        return FileResponse(
            audio_file,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"inline; filename={audio_file.name}"
            }
        )
        
    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


@app.get("/api/visualizations")
async def list_visualizations():
    """List available visualization files"""
    try:
        viz_files = []
        
        # HTML visualizations (Plotly)
        for file in results_dir.glob("*.html"):
            viz_files.append({
                "name": file.stem,
                "filename": file.name,
                "url": f"/api/visualization/{file.name}",
                "type": "html"
            })
        
        # PNG visualizations (fallback)
        for file in results_dir.glob("*.png"):
            viz_files.append({
                "name": file.stem,
                "filename": file.name,
                "url": f"/api/visualization/{file.name}",
                "type": "png"
            })
        
        # JSON data files
        for file in results_dir.glob("*.json"):
            viz_files.append({
                "name": file.stem,
                "filename": file.name,
                "url": f"/api/visualization/{file.name}",
                "type": "json"
            })
        
        return {
            "visualizations": viz_files,
            "count": len(viz_files)
        }
        
    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


@app.get("/api/visualization/{filename}")
async def get_visualization(filename: str):
    """Get a specific visualization"""
    try:
        file_path = results_dir / filename
        
        if not file_path.exists():
            return JSONResponse(
                {"error": f"File '{filename}' not found"},
                status_code=404
            )
        
        # Determine media type
        if file_path.suffix == '.png':
            return FileResponse(file_path, media_type="image/png")
        elif file_path.suffix == '.html':
            return FileResponse(file_path, media_type="text/html")
        elif file_path.suffix == '.json':
            return FileResponse(file_path, media_type="application/json")
        else:
            return FileResponse(file_path)
            
    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


@app.post("/api/cache/clear")
async def clear_cache():
    """Clear the benchmark cache"""
    try:
        cache_file = cache_dir / "benchmark_cache.json"
        
        if cache_file.exists():
            cache_file.unlink()
            return {
                "status": "success",
                "message": "Cache cleared successfully"
            }
        else:
            return {
                "status": "success",
                "message": "Cache was already empty"
            }
            
    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates - OPTIMIZED: 2 second intervals"""
    await websocket.accept()
    active_websockets.add(websocket)
    
    try:
        print(f"WebSocket client connected. Total clients: {len(active_websockets)}")
        
        while True:
            try:
                # Send status update - REDUCED FREQUENCY
                status = await get_status()
                await websocket.send_json(status)
                
                # Wait before next update - OPTIMIZED: 2 seconds instead of 1
                await asyncio.sleep(2.0)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket send error: {e}")
                break
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_websockets.discard(websocket)
        print(f"WebSocket client disconnected. Total clients: {len(active_websockets)}")
        try:
            await websocket.close()
        except:
            pass


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "STT Benchmark API",
        "benchmark_running": is_running,
        "active_websockets": len(active_websockets),
        "cache_exists": (cache_dir / "benchmark_cache.json").exists()
    }


@app.on_event("startup")
async def startup_event():
    """Run on startup"""
    print("\n" + "=" * 80)
    print("STT Benchmark API Server Starting...")
    print("=" * 80)
    print(f"Static directory: {static_dir}")
    print(f"Results directory: {results_dir}")
    print(f"Cache directory: {cache_dir}")
    print("=" * 80 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on shutdown"""
    global is_running
    print("\n" + "=" * 80)
    print("STT Benchmark API Server Shutting Down...")
    print("=" * 80 + "\n")
    
    # Close all websockets
    for ws in list(active_websockets):
        try:
            await ws.close()
        except:
            pass
    
    is_running = False


if __name__ == "__main__":
    import uvicorn
    
    # Load config
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("Error: config.yaml not found!")
        exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    api_config = config.get('api', {})
    host = api_config.get('host', '0.0.0.0')
    port = api_config.get('port', 8000)
    reload = api_config.get('reload', False)
    
    print(f"\nStarting STT Benchmark Dashboard")
    print(f"URL: http://{host}:{port}")
    print(f"Docs: http://{host}:{port}/docs")
    print(f"Health: http://{host}:{port}/api/health\n")
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )