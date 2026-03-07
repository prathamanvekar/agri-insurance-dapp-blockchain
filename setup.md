# Crop Insurance Project Setup (End-to-End)

This guide sets up the full project locally: backend, frontend, OpenWeatherMap, Google Earth Engine (GEE + GCP), and Ganache smart contract flow.

## 1. Prerequisites

- Windows PowerShell (commands below are for Windows)
- Python 3.10+ installed
- Git installed
- Ganache GUI installed
- MetaMask (optional, for wallet testing)
- OpenWeatherMap account + API key
- Google account with Earth Engine access
- Google Cloud project (you already have: `to-do-app-462708`)

## 2. Project Structure

From project root:

- `backend/` Flask API + ML + NDVI + blockchain integration
- `frontend/` vanilla HTML/CSS/JS app
- `backend/contracts/` Solidity contract + ABI/address artifacts

## 3. Backend Setup

Open PowerShell:

```powershell
cd C:\Users\prath\Desktop\LOCKIN\dev\freelance\qriocity\crop\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create/update `backend/.env`:

```env
OPENWEATHER_API_KEY=YOUR_OPENWEATHER_API_KEY
ENABLE_EE=true
EE_PROJECT=to-do-app-462708
```

## 4. Google Earth Engine + GCP Setup

### 4.1 Enable account/project access

1. Open `https://code.earthengine.google.com/` and ensure Earth Engine access is enabled for your Google account.
2. In Google Cloud Console, select project `to-do-app-462708`.
3. Ensure billing/API permissions are valid for Earth Engine usage in your account/project.

### 4.2 Authenticate Earth Engine locally

Run in backend venv terminal:

```powershell
earthengine authenticate --project to-do-app-462708
```

### 4.3 Verify Earth Engine init

```powershell
python -c "import ee; ee.Initialize(project='to-do-app-462708'); print('EE OK')"
```

Expected output: `EE OK`

## 5. OpenWeatherMap Setup

1. Get API key from `https://openweathermap.org/api`.
2. Put it in `backend/.env` as `OPENWEATHER_API_KEY=...`.
3. Backend uses this key automatically via config.

## 6. Ganache + Smart Contract Setup

### 6.1 Start Ganache

1. Open Ganache GUI.
2. Click `Quickstart Ethereum`.
3. Keep Ganache running at `http://127.0.0.1:7545`.

### 6.2 Deploy and verify contract

In backend venv terminal:

```powershell
python setup_blockchain.py
```

This will:

- compile/deploy `CropInsurance.sol`
- write ABI/address artifacts in `backend/contracts/`
- run test chain transactions
- update contract address in backend config

## 7. Run the Project

## 7.1 Run backend

In `backend/` venv terminal:

```powershell
python app.py
```

Backend URL: `http://localhost:5001`

Health check:

```powershell
curl http://localhost:5001/api/health
```

## 7.2 Run frontend

Open new terminal:

```powershell
cd C:\Users\prath\Desktop\LOCKIN\dev\freelance\qriocity\crop\frontend
python -m http.server 5500
```

Open in browser:

- `http://localhost:5500/index.html`

## 8. Real NDVI Verification (not simulated)

With backend running and `ENABLE_EE=true`:

```powershell
curl "http://localhost:5001/api/ndvi/health/26.8467/80.9462?crop=wheat"
```

Check response field `source`:

- Real mode: `Google Earth Engine - Sentinel-2`
- If not real, backend will fallback to simulation mode (usually auth/project/data availability issue)

## 9. Recommended Test Flow

1. Register farmer and create policy in frontend.
2. Pay premium.
3. Open dashboard and verify weather + NDVI cards load.
4. Check claim eligibility.
5. Process claim (approved/rejected based on triggers).
6. Verify transaction hash in claim/policy responses.

## 10. Common Issues

- `ee.Initialize: no project found`
  - Re-run: `earthengine authenticate --project to-do-app-462708`
  - Ensure `EE_PROJECT=to-do-app-462708` in `.env`
- `ModuleNotFoundError` for backend packages
  - Make sure venv is active before running backend commands
- Blockchain simulation mode always true
  - Ensure Ganache is running on `127.0.0.1:7545`
  - Re-run `python setup_blockchain.py`
- Frontend stale behavior
  - Hard refresh browser (`Ctrl+F5`)
