from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Optional
import logging

app = FastAPI(title="AgriGuard API Orchestrator", version="1.1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCSI_URL = "http://mcsi:8000"
YIELD_URL = "http://yield:8001"
MCSI_URL_LOCAL = "http://localhost:8000"
YIELD_URL_LOCAL = "http://localhost:8001"

@app.get("/health")
async def health_check():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            mcsi_health = False
            yield_health = False
            try:
                r = await client.get(f"{MCSI_URL}/health")
                mcsi_health = r.status_code == 200
            except:
                try:
                    r = await client.get(f"{MCSI_URL_LOCAL}/health")
                    mcsi_health = r.status_code == 200
                except:
                    pass
            try:
                r = await client.get(f"{YIELD_URL}/health")
                yield_health = r.status_code == 200
            except:
                try:
                    r = await client.get(f"{YIELD_URL_LOCAL}/health")
                    yield_health = r.status_code == 200
                except:
                    pass
        return {"status": "healthy" if mcsi_health and yield_health else "degraded", "services": {"mcsi": "healthy" if mcsi_health else "unhealthy", "yield": "healthy" if yield_health else "unhealthy"}}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/mcsi/{fips}/timeseries")
async def get_mcsi_timeseries(fips: str, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: Optional[int] = 30):
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"{MCSI_URL}/mcsi/county/{fips}/timeseries?limit={limit}"
            if start_date:
                url += f"&start_date={start_date}"
            if end_date:
                url += f"&end_date={end_date}"
            try:
                response = await client.get(url)
            except:
                url_local = f"{MCSI_URL_LOCAL}/mcsi/county/{fips}/timeseries?limit={limit}"
                if start_date:
                    url_local += f"&start_date={start_date}"
                if end_date:
                    url_local += f"&end_date={end_date}"
                response = await client.get(url_local)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"MCSI error: {e}")
        raise HTTPException(status_code=503, detail="MCSI unavailable")

@app.get("/mcsi/{fips}")
async def get_mcsi(fips: str):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{MCSI_URL}/mcsi/county/{fips}")
            except:
                response = await client.get(f"{MCSI_URL_LOCAL}/mcsi/county/{fips}")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail="MCSI unavailable")

@app.get("/yield/{fips}")
async def get_yield_forecast(fips: str, week: Optional[int] = None):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                ts_res = await client.get(f"{MCSI_URL}/mcsi/county/{fips}/timeseries?limit=30")
            except:
                ts_res = await client.get(f"{MCSI_URL_LOCAL}/mcsi/county/{fips}/timeseries?limit=30")
            ts_res.raise_for_status()
            timeseries = ts_res.json()
            if not isinstance(timeseries, list):
                timeseries = [timeseries]
            
            current_week = week if week else max(item.get("week_of_season", 0) for item in timeseries)
            filtered = [item for item in timeseries if item.get("week_of_season", 0) <= current_week]
            
            raw_data = {}
            for item in filtered:
                w = item.get("week_of_season", 0)
                indicators = item.get("indicators", {})
                raw_data[str(w)] = {
                    "water_deficit_mean": indicators.get("water_deficit_mean", 0),
                    "lst_days_above_32C": int(indicators.get("lst_mean", 0)),
                    "ndvi_mean": indicators.get("ndvi_mean", 0.5),
                    "vpd_mean": indicators.get("vpd_mean", 0),
                    "pr_sum": indicators.get("precipitation_mean", 0)
                }
            
            yield_req = {"fips": fips, "current_week": current_week, "year": 2025, "raw_data": raw_data}
            logger.info(f"Yield forecast {fips} week {current_week}")
            
            try:
                yres = await client.post(f"{YIELD_URL}/forecast", json=yield_req, timeout=15.0)
            except:
                yres = await client.post(f"{YIELD_URL_LOCAL}/forecast", json=yield_req, timeout=15.0)
            yres.raise_for_status()
            ydata = yres.json()
            
            return {
                "fips": fips,
                "week": current_week,
                "predicted_yield": ydata.get("yield_forecast_bu_acre"),
                "confidence_interval": ydata.get("forecast_uncertainty", 0.31),
                "confidence_lower": ydata.get("confidence_interval_lower"),
                "confidence_upper": ydata.get("confidence_interval_upper"),
                "primary_driver": ydata.get("primary_driver", "unknown"),
                "model_r2": ydata.get("model_r2", 0.835),
            }
    except Exception as e:
        logger.error(f"Yield error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
