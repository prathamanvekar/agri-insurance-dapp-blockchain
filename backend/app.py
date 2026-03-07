"""
Crop Insurance Backend - Main Flask Application
"""

import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from config import active_config as config
from services import WeatherService, NDVIService, MLService, BlockchainService

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config)
CORS(app)

# Initialize database
os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
db = SQLAlchemy(app)

# Initialize services
weather_service = WeatherService()
ndvi_service = NDVIService()
ml_service = MLService()
blockchain_service = BlockchainService()


# =============================================================================
# DATABASE MODELS
# =============================================================================

class Farmer(db.Model):
    __tablename__ = 'farmers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    wallet_address = db.Column(db.String(42))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    policies = db.relationship('Policy', backref='farmer', lazy=True)


class Policy(db.Model):
    __tablename__ = 'policies'

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.String(20), unique=True, nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id'), nullable=False)

    # Farm details
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    crop_type = db.Column(db.String(50), nullable=False)
    sowing_date = db.Column(db.Date)
    expected_yield = db.Column(db.Float)
    farm_area_acres = db.Column(db.Float)

    # Insurance details
    premium_amount = db.Column(db.Float, nullable=False)
    coverage_amount = db.Column(db.Float, nullable=False)
    premium_paid = db.Column(db.Boolean, default=False)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_claimed = db.Column(db.Boolean, default=False)

    # Blockchain
    blockchain_tx_hash = db.Column(db.String(66))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)

    claims = db.relationship('Claim', backref='policy', lazy=True)


class Claim(db.Model):
    __tablename__ = 'claims'

    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.String(20), unique=True, nullable=False)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)

    # Trigger status
    weather_trigger = db.Column(db.Boolean, default=False)
    ndvi_trigger = db.Column(db.Boolean, default=False)

    # Weather data
    weather_risk = db.Column(db.String(20))
    rainfall_mm = db.Column(db.Float)
    temperature = db.Column(db.Float)

    # NDVI data
    current_ndvi = db.Column(db.Float)
    expected_ndvi = db.Column(db.Float)
    ndvi_drop_percent = db.Column(db.Float)

    # Decision
    status = db.Column(db.String(20), default='PENDING')  # PENDING, APPROVED, REJECTED
    payout_amount = db.Column(db.Float)
    payout_tx_hash = db.Column(db.String(66))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)


class WeatherLog(db.Model):
    __tablename__ = 'weather_logs'

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)

    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    rainfall = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    risk_category = db.Column(db.String(20))

    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)


class NDVILog(db.Model):
    __tablename__ = 'ndvi_logs'

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.id'), nullable=False)

    ndvi_value = db.Column(db.Float)
    health_status = db.Column(db.String(30))
    source = db.Column(db.String(50))

    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)


# Create tables
with app.app_context():
    db.create_all()
    print("Database tables created!")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_policy_id():
    """Generate unique policy ID."""
    year = datetime.now().year
    count = Policy.query.filter(
        Policy.policy_id.like(f'POL-{year}-%')
    ).count() + 1
    return f"POL-{year}-{count:04d}"


def generate_claim_id():
    """Generate unique claim ID."""
    year = datetime.now().year
    count = Claim.query.filter(
        Claim.claim_id.like(f'CLM-{year}-%')
    ).count() + 1
    return f"CLM-{year}-{count:04d}"


def _is_truthy(value):
    """Parse common truthy query/body values."""
    if value is None:
        return False
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _evaluate_claim_eligibility(policy, force_eligible=False):
    """Evaluate claim eligibility with optional debug override for local testing."""
    if not policy.is_active:
        return {
            'success': False,
            'error': 'Policy is not active'
        }

    if policy.is_claimed:
        return {
            'success': False,
            'error': 'Policy already claimed'
        }

    if not policy.premium_paid:
        return {
            'success': False,
            'error': 'Premium not paid'
        }

    weather_analysis = weather_service.analyze_weather_risk(policy.latitude, policy.longitude)
    ndvi_analysis = ndvi_service.analyze_crop_health(policy.latitude, policy.longitude, policy.crop_type)

    if weather_analysis['success']:
        ml_prediction = ml_service.predict_from_weather_data(weather_analysis)
    else:
        ml_prediction = {'success': False, 'error': 'Weather data unavailable'}

    weather_trigger = weather_analysis.get('weather_trigger', False) or \
                      (ml_prediction.get('weather_trigger', False) if ml_prediction.get('success') else False)
    ndvi_trigger = ndvi_analysis.get('ndvi_trigger', False)
    claim_eligible = weather_trigger and ndvi_trigger

    test_override_applied = bool(force_eligible and config.DEBUG)
    if test_override_applied:
        weather_trigger = True
        ndvi_trigger = True
        claim_eligible = True

    payout_amount = 0
    if claim_eligible:
        ndvi_drop = ndvi_analysis.get('ndvi_drop_percent', 0)
        if test_override_applied:
            ndvi_drop = max(ndvi_drop, 35)

        if ndvi_drop > 50:
            payout_amount = policy.coverage_amount * 1.0
        elif ndvi_drop > 30:
            payout_amount = policy.coverage_amount * 0.7
        elif ndvi_drop > 15:
            payout_amount = policy.coverage_amount * 0.4
        else:
            payout_amount = policy.coverage_amount * 0.2

    return {
        'success': True,
        'policy_id': policy.policy_id,
        'farmer_name': policy.farmer.name,
        'crop_type': policy.crop_type,
        'location': {
            'lat': policy.latitude,
            'lon': policy.longitude
        },
        'weather_analysis': {
            'risk_level': weather_analysis.get('risk_level', 'Unknown'),
            'trigger': weather_trigger,
            'details': weather_analysis.get('risks', [])
        },
        'ndvi_analysis': {
            'current_ndvi': ndvi_analysis.get('current_ndvi'),
            'expected_ndvi': ndvi_analysis.get('expected_ndvi'),
            'drop_percent': ndvi_analysis.get('ndvi_drop_percent'),
            'health_status': ndvi_analysis.get('health_status'),
            'trigger': ndvi_trigger,
            'reasons': ndvi_analysis.get('trigger_reasons', [])
        },
        'ml_prediction': {
            'risk_category': ml_prediction.get('prediction', {}).get('risk_category', 'Unknown'),
            'confidence': ml_prediction.get('prediction', {}).get('confidence', 0)
        } if ml_prediction.get('success') else None,
        'double_verification': {
            'weather_trigger': weather_trigger,
            'ndvi_trigger': ndvi_trigger,
            'claim_eligible': claim_eligible
        },
        'payout': {
            'eligible': claim_eligible,
            'amount': payout_amount,
            'coverage': policy.coverage_amount
        },
        'test_mode': {
            'override_requested': bool(force_eligible),
            'override_applied': test_override_applied
        }
    }


# =============================================================================
# API ROUTES - HEALTH CHECK
# =============================================================================

@app.route('/')
def home():
    return jsonify({
        'name': 'Crop Insurance API',
        'version': '1.0.0',
        'status': 'running',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'services': {
            'database': 'connected',
            'ml_models': 'loaded' if ml_service.models_loaded else 'not loaded',
            'blockchain': 'connected' if blockchain_service.connected else 'not connected'
        },
        'timestamp': datetime.now().isoformat()
    })


# =============================================================================
# API ROUTES - FARMER MANAGEMENT
# =============================================================================

@app.route('/api/farmers', methods=['GET'])
def get_farmers():
    """Get all farmers."""
    farmers = Farmer.query.all()
    return jsonify({
        'success': True,
        'count': len(farmers),
        'farmers': [{
            'id': f.id,
            'name': f.name,
            'phone': f.phone,
            'email': f.email,
            'wallet_address': f.wallet_address,
            'created_at': f.created_at.isoformat()
        } for f in farmers]
    })


@app.route('/api/farmers', methods=['POST'])
def register_farmer():
    """Register new farmer."""
    data = request.json

    # Validate required fields
    required = ['name']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400

    farmer = Farmer(
        name=data['name'],
        phone=data.get('phone'),
        email=data.get('email'),
        wallet_address=data.get('wallet_address')
    )

    db.session.add(farmer)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Farmer registered successfully',
        'farmer': {
            'id': farmer.id,
            'name': farmer.name,
            'wallet_address': farmer.wallet_address
        }
    }), 201


@app.route('/api/farmers/<int:farmer_id>', methods=['GET'])
def get_farmer(farmer_id):
    """Get farmer by ID."""
    farmer = Farmer.query.get_or_404(farmer_id)
    return jsonify({
        'success': True,
        'farmer': {
            'id': farmer.id,
            'name': farmer.name,
            'phone': farmer.phone,
            'email': farmer.email,
            'wallet_address': farmer.wallet_address,
            'policies_count': len(farmer.policies),
            'created_at': farmer.created_at.isoformat()
        }
    })


# =============================================================================
# API ROUTES - POLICY MANAGEMENT
# =============================================================================

@app.route('/api/policies', methods=['GET'])
def get_policies():
    """Get all policies."""
    policies = Policy.query.all()
    return jsonify({
        'success': True,
        'count': len(policies),
        'policies': [{
            'id': p.id,
            'policy_id': p.policy_id,
            'farmer_id': p.farmer_id,
            'crop_type': p.crop_type,
            'location': {'lat': p.latitude, 'lon': p.longitude},
            'premium': p.premium_amount,
            'coverage': p.coverage_amount,
            'is_active': p.is_active,
            'is_claimed': p.is_claimed,
            'premium_paid': p.premium_paid,
            'created_at': p.created_at.isoformat()
        } for p in policies]
    })


@app.route('/api/policies', methods=['POST'])
def create_policy():
    """Create new insurance policy."""
    data = request.json

    # Validate required fields
    required = ['farmer_id', 'latitude', 'longitude', 'crop_type', 'premium_amount']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400

    # Check if farmer exists
    farmer = db.session.get(Farmer, data['farmer_id'])
    if not farmer:
        return jsonify({'success': False, 'error': 'Farmer not found'}), 404

    # Generate policy ID
    policy_id = generate_policy_id()

    # Calculate coverage (default: 10x premium)
    coverage = data.get('coverage_amount', data['premium_amount'] * config.MAX_PAYOUT_MULTIPLIER)

    # Create policy
    policy = Policy(
        policy_id=policy_id,
        farmer_id=data['farmer_id'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        crop_type=data['crop_type'],
        sowing_date=datetime.strptime(data['sowing_date'], '%Y-%m-%d').date() if data.get('sowing_date') else None,
        expected_yield=data.get('expected_yield'),
        farm_area_acres=data.get('farm_area_acres'),
        premium_amount=data['premium_amount'],
        coverage_amount=coverage
    )

    db.session.add(policy)
    db.session.commit()

    # Try to record on blockchain (fallback to simulation mode if unavailable)
    if blockchain_service.connected:
        try:
            farmer_wallet = farmer.wallet_address or blockchain_service.account
            premium_wei = int(blockchain_service.web3.to_wei(policy.premium_amount / 100000, 'ether'))
            coverage_wei = int(blockchain_service.web3.to_wei(policy.coverage_amount / 100000, 'ether'))

            chain_tx = blockchain_service.create_policy_on_chain(
                policy_id=policy.policy_id,
                farmer=farmer_wallet,
                premium_wei=premium_wei,
                coverage_wei=coverage_wei,
                crop_type=policy.crop_type,
            )

            if chain_tx.get('success'):
                policy.blockchain_tx_hash = chain_tx.get('transaction_hash')
                db.session.commit()
            else:
                print(f"Blockchain create_policy_on_chain failed: {chain_tx.get('error')}")
        except Exception as chain_error:
            print(f"Blockchain create policy exception: {chain_error}")

    return jsonify({
        'success': True,
        'message': 'Policy created successfully',
        'policy': {
            'policy_id': policy.policy_id,
            'farmer_name': farmer.name,
            'crop_type': policy.crop_type,
            'location': {'lat': policy.latitude, 'lon': policy.longitude},
            'premium': policy.premium_amount,
            'coverage': policy.coverage_amount,
            'created_at': policy.created_at.isoformat()
        }
    }), 201


@app.route('/api/policies/<policy_id>', methods=['GET'])
def get_policy(policy_id):
    """Get policy by ID."""
    policy = Policy.query.filter_by(policy_id=policy_id).first_or_404()
    farmer = db.session.get(Farmer, policy.farmer_id)

    return jsonify({
        'success': True,
        'policy': {
            'policy_id': policy.policy_id,
            'farmer': {
                'id': farmer.id,
                'name': farmer.name,
                'wallet_address': farmer.wallet_address
            },
            'farm': {
                'latitude': policy.latitude,
                'longitude': policy.longitude,
                'crop_type': policy.crop_type,
                'sowing_date': policy.sowing_date.isoformat() if policy.sowing_date else None,
                'expected_yield': policy.expected_yield,
                'area_acres': policy.farm_area_acres
            },
            'insurance': {
                'premium': policy.premium_amount,
                'coverage': policy.coverage_amount,
                'premium_paid': policy.premium_paid
            },
            'status': {
                'is_active': policy.is_active,
                'is_claimed': policy.is_claimed
            },
            'blockchain_tx': policy.blockchain_tx_hash,
            'created_at': policy.created_at.isoformat()
        }
    })


@app.route('/api/policies/<policy_id>/pay-premium', methods=['POST'])
def pay_premium(policy_id):
    """Mark premium as paid."""
    policy = Policy.query.filter_by(policy_id=policy_id).first_or_404()

    if policy.premium_paid:
        return jsonify({'success': False, 'error': 'Premium already paid'}), 400

    policy.premium_paid = True
    policy.is_active = True

    # Record premium payment on-chain when available; fallback to simulation.
    if blockchain_service.connected:
        try:
            premium_wei = int(blockchain_service.web3.to_wei(policy.premium_amount / 100000, 'ether'))
            payer_wallet = policy.farmer.wallet_address or blockchain_service.account
            tx = blockchain_service.pay_premium_on_chain(policy_id, payer_wallet, premium_wei)
            if not tx.get('success'):
                tx = blockchain_service.simulate_transaction(policy_id, policy.premium_amount / 100000, action='pay_premium')
        except Exception as chain_error:
            print(f"Blockchain pay premium exception: {chain_error}")
            tx = blockchain_service.simulate_transaction(policy_id, policy.premium_amount / 100000, action='pay_premium')
    else:
        tx = blockchain_service.simulate_transaction(policy_id, policy.premium_amount / 100000, action='pay_premium')

    policy.blockchain_tx_hash = tx['transaction_hash']

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Premium paid successfully',
        'transaction': tx
    })


# =============================================================================
# API ROUTES - WEATHER DATA
# =============================================================================

@app.route('/api/weather/<float:lat>/<float:lon>', methods=['GET'])
def get_weather(lat, lon):
    """Get current weather for location."""
    return jsonify(weather_service.get_current_weather(lat, lon))


@app.route('/api/weather/forecast/<float:lat>/<float:lon>', methods=['GET'])
def get_weather_forecast(lat, lon):
    """Get weather forecast."""
    days = request.args.get('days', 5, type=int)
    return jsonify(weather_service.get_forecast(lat, lon, days))


@app.route('/api/weather/risk/<float:lat>/<float:lon>', methods=['GET'])
def analyze_weather_risk(lat, lon):
    """Analyze weather risk for location."""
    return jsonify(weather_service.analyze_weather_risk(lat, lon))


# =============================================================================
# API ROUTES - NDVI DATA
# =============================================================================

@app.route('/api/ndvi/<float:lat>/<float:lon>', methods=['GET'])
def get_ndvi(lat, lon):
    """Get NDVI data for location."""
    days = request.args.get('days', 90, type=int)
    return jsonify(ndvi_service.get_ndvi(lat, lon, days))


@app.route('/api/ndvi/health/<float:lat>/<float:lon>', methods=['GET'])
def analyze_crop_health(lat, lon):
    """Analyze crop health based on NDVI."""
    crop_type = request.args.get('crop')
    return jsonify(ndvi_service.analyze_crop_health(lat, lon, crop_type))


# =============================================================================
# API ROUTES - ML PREDICTIONS
# =============================================================================

@app.route('/api/predict/risk', methods=['POST'])
def predict_risk():
    """Predict weather risk from input parameters."""
    data = request.json

    required = ['rainfall_annual', 'temperature', 'humidity', 'wind_speed']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400

    model_type = data.get('model', 'xgb')

    return jsonify(ml_service.predict_weather_risk(
        data['rainfall_annual'],
        data['temperature'],
        data['humidity'],
        data['wind_speed'],
        model_type
    ))


@app.route('/api/predict/crop-stress', methods=['POST'])
def predict_crop_stress():
    """Predict crop stress level."""
    data = request.json

    required = ['crop_type', 'temperature', 'humidity', 'rainfall']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400

    return jsonify(ml_service.assess_crop_stress(
        data['crop_type'],
        data['temperature'],
        data['humidity'],
        data['rainfall']
    ))


@app.route('/api/models/info', methods=['GET'])
def get_model_info():
    """Get ML model information."""
    return jsonify(ml_service.get_model_info())


# =============================================================================
# API ROUTES - CLAIM PROCESSING
# =============================================================================

@app.route('/api/claims/check/<policy_id>', methods=['GET'])
def check_claim_eligibility(policy_id):
    """Check if policy is eligible for claim."""
    policy = Policy.query.filter_by(policy_id=policy_id).first_or_404()
    force_eligible = _is_truthy(request.args.get('force_eligible'))
    return jsonify(_evaluate_claim_eligibility(policy, force_eligible=force_eligible))


@app.route('/api/claims/process/<policy_id>', methods=['POST'])
def process_claim(policy_id):
    """Process and approve/reject claim."""
    policy = Policy.query.filter_by(policy_id=policy_id).first_or_404()

    # Check eligibility first
    body = request.get_json(silent=True) or {}
    force_eligible = _is_truthy(body.get('force_eligible'))
    eligibility_data = _evaluate_claim_eligibility(policy, force_eligible=force_eligible)

    if not eligibility_data.get('success'):
        return jsonify(eligibility_data)

    if not eligibility_data['double_verification']['claim_eligible']:
        # Create rejected claim record
        claim = Claim(
            claim_id=generate_claim_id(),
            policy_id=policy.id,
            weather_trigger=eligibility_data['double_verification']['weather_trigger'],
            ndvi_trigger=eligibility_data['double_verification']['ndvi_trigger'],
            weather_risk=eligibility_data['weather_analysis']['risk_level'],
            current_ndvi=eligibility_data['ndvi_analysis']['current_ndvi'],
            expected_ndvi=eligibility_data['ndvi_analysis']['expected_ndvi'],
            ndvi_drop_percent=eligibility_data['ndvi_analysis']['drop_percent'],
            status='REJECTED',
            processed_at=datetime.utcnow()
        )

        db.session.add(claim)
        db.session.commit()

        return jsonify({
            'success': True,
            'claim_id': claim.claim_id,
            'status': 'REJECTED',
            'reason': 'Double verification failed - both triggers must be TRUE',
            'details': eligibility_data['double_verification']
        })

    # Process approved claim
    payout_amount = eligibility_data['payout']['amount']
    claim_id = generate_claim_id()

    # Process payout on-chain when available; fallback to simulation.
    if blockchain_service.connected:
        try:
            payout_wei = int(blockchain_service.web3.to_wei(payout_amount / 100000, 'ether'))
            tx = blockchain_service.process_claim_on_chain(
                claim_id=claim_id,
                policy_id=policy_id,
                weather_trigger=True,
                ndvi_trigger=True,
                payout_amount_wei=payout_wei,
            )
            if not tx.get('success'):
                tx = blockchain_service.simulate_transaction(
                    policy_id,
                    payout_amount / 100000,
                    action='process_claim',
                    extra={'claim_id': claim_id, 'approved': True},
                )
        except Exception as chain_error:
            print(f"Blockchain process claim exception: {chain_error}")
            tx = blockchain_service.simulate_transaction(
                policy_id,
                payout_amount / 100000,
                action='process_claim',
                extra={'claim_id': claim_id, 'approved': True},
            )
    else:
        tx = blockchain_service.simulate_transaction(
            policy_id,
            payout_amount / 100000,
            action='process_claim',
            extra={'claim_id': claim_id, 'approved': True},
        )

    # Create approved claim record
    claim = Claim(
        claim_id=claim_id,
        policy_id=policy.id,
        weather_trigger=True,
        ndvi_trigger=True,
        weather_risk=eligibility_data['weather_analysis']['risk_level'],
        rainfall_mm=eligibility_data.get('weather_analysis', {}).get('rainfall'),
        temperature=eligibility_data.get('weather_analysis', {}).get('temperature'),
        current_ndvi=eligibility_data['ndvi_analysis']['current_ndvi'],
        expected_ndvi=eligibility_data['ndvi_analysis']['expected_ndvi'],
        ndvi_drop_percent=eligibility_data['ndvi_analysis']['drop_percent'],
        status='APPROVED',
        payout_amount=payout_amount,
        payout_tx_hash=tx['transaction_hash'],
        processed_at=datetime.utcnow()
    )

    # Update policy
    policy.is_claimed = True
    policy.is_active = False

    db.session.add(claim)
    db.session.commit()

    return jsonify({
        'success': True,
        'claim_id': claim.claim_id,
        'policy_id': policy_id,
        'status': 'APPROVED',
        'payout': {
            'amount': payout_amount,
            'transaction_hash': tx['transaction_hash'],
            'farmer_wallet': policy.farmer.wallet_address
        },
        'verification': {
            'weather_trigger': True,
            'ndvi_trigger': True,
            'weather_risk': eligibility_data['weather_analysis']['risk_level'],
            'ndvi_drop': eligibility_data['ndvi_analysis']['drop_percent']
        },
        'message': f'Claim approved! ₹{payout_amount:,.2f} will be transferred to farmer wallet.'
    })


@app.route('/api/claims', methods=['GET'])
def get_claims():
    """Get all claims."""
    claims = Claim.query.all()
    return jsonify({
        'success': True,
        'count': len(claims),
        'claims': [{
            'claim_id': c.claim_id,
            'policy_id': c.policy.policy_id,
            'status': c.status,
            'weather_trigger': c.weather_trigger,
            'ndvi_trigger': c.ndvi_trigger,
            'payout_amount': c.payout_amount,
            'created_at': c.created_at.isoformat()
        } for c in claims]
    })


# =============================================================================
# API ROUTES - BLOCKCHAIN
# =============================================================================

@app.route('/api/blockchain/status', methods=['GET'])
def blockchain_status():
    """Get blockchain connection status."""
    return jsonify(blockchain_service.get_connection_status())


# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("CROP INSURANCE BACKEND")
    print("=" * 60)
    print(f"\nStarting server...")
    print(f"Database: {config.DATABASE_PATH}")
    print(f"Models: {config.MODELS_PATH}")
    print(f"\nAPI Endpoints:")
    print(f"  - Health: http://localhost:5001/api/health")
    print(f"  - Farmers: http://localhost:5001/api/farmers")
    print(f"  - Policies: http://localhost:5001/api/policies")
    print(f"  - Weather: http://localhost:5001/api/weather/<lat>/<lon>")
    print(f"  - NDVI: http://localhost:5001/api/ndvi/<lat>/<lon>")
    print(f"  - Claims: http://localhost:5001/api/claims/check/<policy_id>")
    print("\n" + "=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5001)
