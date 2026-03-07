# Agri Insurance DApp

**A blockchain-based crop insurance platform using AI, satellite imaging (NDVI), and real-time weather data to automate premium calculations and claim settlements.**

---

## Overview

Agri Insurance DApp is an end-to-end decentralized application that provides automated crop insurance coverage. It combines:

- **Blockchain Smart Contracts** (Solidity/Ganache) for transparent policy and claim management
- **Machine Learning** for risk assessment and premium calculation
- **Satellite Data** (Google Earth Engine NDVI) for crop health monitoring
- **Real-time Weather Data** (OpenWeatherMap API) for event-triggered claims
- **Web Frontend** for farmers to manage policies and file claims

### Key Features

✅ Automated policy creation with risk-based premium calculation
✅ Real-time crop health monitoring via NDVI (Normalized Difference Vegetation Index)
✅ Weather-trigger claim detection (drought, flood, heatwave)
✅ Blockchain-backed claim settlements
✅ Farmer wallet integration for payouts
✅ Transparent transaction records on smart contracts

---

## Tech Stack

| Component              | Technology                     |
| ---------------------- | ------------------------------ |
| **Backend API**        | Flask (Python)                 |
| **Database**           | SQLite                         |
| **Smart Contracts**    | Solidity 0.8.19                |
| **Blockchain (Local)** | Ganache                        |
| **ML/Risk Analysis**   | Python (scikit-learn, models/) |
| **Satellite Data**     | Google Earth Engine (GEE)      |
| **Weather Data**       | OpenWeatherMap API             |
| **Frontend**           | Vanilla HTML/CSS/JavaScript    |
| **Web3 Integration**   | web3.py                        |

---

## Prerequisites

- **Python 3.10+**
- **Node.js / npm** (for Ganache)
- **Git**
- **Accounts & Keys:**
  - OpenWeatherMap API key: https://openweathermap.org/api
  - Google account with Earth Engine access: https://code.earthengine.google.com/
  - Google Cloud project with Earth Engine enabled
- **Ganache GUI** (for local blockchain)
- **MetaMask** (optional, for wallet testing)

---

## Setup Instructions

### 1. Clone & Navigate

```bash
git clone <repository-url>
cd agri-insurance-dapp
```

### 2. Backend Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Environment Configuration

Create `backend/.env`:

```env
OPENWEATHER_API_KEY=your_openweather_api_key_here
ENABLE_EE=true
EE_PROJECT=your_gcp_project_id
```

### 4. Google Earth Engine Authentication

```powershell
earthengine authenticate --project your_gcp_project_id
```

Verify:

```powershell
python -c "import ee; ee.Initialize(project='your_gcp_project_id'); print('EE OK')"
```

### 5. Blockchain Setup (Ganache)

1. **Start Ganache GUI:**
   - Open Ganache
   - Click "Quickstart Ethereum"
   - Ganache runs at `http://127.0.0.1:7545`

2. **Deploy Smart Contract:**

```powershell
python setup_blockchain.py
```

This will:

- Compile `CropInsurance.sol`
- Deploy to Ganache
- Save contract ABI and address in `backend/contracts/`
- Update `config.py` with contract address

### 6. Run the Application

#### Start Backend API:

```powershell
cd backend
flask run
# Runs at http://localhost:5000
```

#### Start Frontend:

Open `frontend/index.html` in your browser or serve it:

```bash
cd frontend
python -m http.server 8000
# Open http://localhost:8000
```

---

## Project Structure

```
.
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── config.py              # Configuration & API keys
│   ├── setup_blockchain.py    # Smart contract deployment
│   ├── deploy_contract.py     # Contract compilation & deployment
│   ├── requirements.txt        # Python dependencies
│   ├── contracts/
│   │   ├── CropInsurance.sol  # Smart contract source
│   │   ├── abi.json           # Contract ABI (auto-generated)
│   │   └── address.txt        # Deployed address (auto-generated)
│   ├── models/                # ML models for risk assessment
│   ├── services/
│   │   ├── blockchain_service.py  # Web3 & contract interactions
│   │   ├── weather_service.py     # OpenWeatherMap integration
│   │   ├── ndvi_service.py        # Google Earth Engine integration
│   │   ├── ml_service.py          # Risk scoring & ML inference
│   │   └── __init__.py
│   └── database/
│       └── crop_insurance.db  # SQLite database (auto-created)
├── frontend/
│   ├── index.html             # Main UI
│   ├── app.js                 # Frontend logic & API calls
│   └── styles.css             # Styling
├── contracts/
│   └── CropInsurance.sol      # Smart contract source
├── setup.md                   # Detailed setup guide
└── README.md

```

---

## API Endpoints

| Method | Endpoint             | Description                   |
| ------ | -------------------- | ----------------------------- |
| POST   | `/api/farmers`       | Register a new farmer         |
| GET    | `/api/farmers/<id>`  | Get farmer details            |
| POST   | `/api/policies`      | Create a new insurance policy |
| GET    | `/api/policies/<id>` | Get policy details            |
| POST   | `/api/claims`        | File a new claim              |
| GET    | `/api/claims/<id>`   | Get claim status              |
| POST   | `/api/health-check`  | System health check           |

---

## Smart Contract Functions

### Policy Management

- `createPolicy()` – Register a new insurance policy
- `payPremium()` – Farmer pays premium in ETH
- `activatePolicy()` – Activate after premium payment

### Claim Processing

- `fileClaim()` – Submit a claim with weather/NDVI triggers
- `approveClaim()` – Contract owner approves and processes payout
- `rejectClaim()` – Contract owner rejects claim

---

## Risk Assessment

The platform assesses crop risk using:

1. **Weather Data:**
   - Drought risk: annual rainfall < 804mm
   - Flood risk: annual rainfall > 1645mm
   - Heatwave risk: temperature > 38°C

2. **Satellite Imagery (NDVI):**
   - Healthy vegetation: NDVI ≥ 0.5
   - Vegetation stress: NDVI 0.35–0.5
   - Severe damage: NDVI < 0.2
   - Trigger claim: ≥30% NDVI drop

3. **ML Model:**
   - Trained on historical crop & weather data
   - Predicts risk probability
   - Determines premium based on risk tier

---

## Development & Testing

### Run Backend Tests

```powershell
cd backend
pytest tests/
```

### Ganache Accounts (Pre-funded)

Ganache provides 10 pre-funded accounts with 100 ETH each.
Use Account 0 as the contract owner and others as farmer wallets.

---

## Troubleshooting

| Issue                             | Solution                                                                  |
| --------------------------------- | ------------------------------------------------------------------------- |
| Ganache connection failed         | Ensure Ganache is running at `http://127.0.0.1:7545`                      |
| Earth Engine authentication error | Run `earthengine authenticate` again with correct project                 |
| OpenWeatherMap API error          | Verify API key in `.env` is valid                                         |
| Contract deployment fails         | Check Ganache is running; clear `backend/contracts/address.txt` and retry |
| NDVI data unavailable             | Verify GEE access is enabled; check coordinates are valid                 |

---

## License

MIT License – See LICENSE file for details

---

## Contributing

Contributions are welcome! Please fork this repository and submit a pull request with your improvements.

---

## Authors

Developed as a crop insurance DApp for climate-resilient agriculture.
