"""
ML Service - Weather Risk Prediction using trained models
"""

import os
import joblib
import numpy as np
import warnings
from datetime import datetime
from config import active_config as config


class MLService:
    def __init__(self):
        self.models_path = config.MODELS_PATH
        self.models_loaded = False
        self._load_models()

    def _load_models(self):
        """Load all trained ML models."""
        try:
            # Load Random Forest model
            self.rf_model = self._safe_load_model(
                os.path.join(self.models_path, 'weather_risk_rf_model.pkl')
            )

            # Load XGBoost model
            self.xgb_model = self._safe_load_model(
                os.path.join(self.models_path, 'weather_risk_xgb_model.pkl')
            )

            # Load Isolation Forest (anomaly detection)
            self.isolation_forest = self._safe_load_model(
                os.path.join(self.models_path, 'anomaly_detector.pkl')
            )

            # Load scaler
            self.scaler = self._safe_load_model(
                os.path.join(self.models_path, 'scaler.pkl')
            )

            # Load label encoder
            self.label_encoder = self._safe_load_model(
                os.path.join(self.models_path, 'label_encoder.pkl')
            )

            # Load feature columns
            self.feature_columns = self._safe_load_model(
                os.path.join(self.models_path, 'feature_columns.pkl')
            )

            # Load crop optimal conditions
            self.crop_optimal = self._safe_load_model(
                os.path.join(self.models_path, 'crop_optimal_conditions.pkl')
            )

            # Load config
            self.model_config = self._safe_load_model(
                os.path.join(self.models_path, 'config.pkl')
            )

            self.models_loaded = True
            print("All ML models loaded successfully!")
            print(f"   Classes: {self.label_encoder.classes_}")
            print(f"   Features: {self.feature_columns}")

        except Exception as e:
            print(f"Error loading models: {e}")
            print("Make sure all .pkl files are in the models/ directory")
            self.models_loaded = False

    def _safe_load_model(self, path: str):
        """Load pickled artifacts while silencing known compatibility chatter.

        These warnings are common when models were trained in a slightly different
        sklearn/xgboost version but still deserialize correctly.
        """
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore',
                message='.*Trying to unpickle estimator.*',
                category=UserWarning
            )
            warnings.filterwarnings(
                'ignore',
                message='.*version.*might not be compatible.*',
                category=UserWarning
            )
            return joblib.load(path)

    def predict_weather_risk(
        self,
        rainfall_annual: float,
        temperature: float,
        humidity: float,
        wind_speed: float,
        model_type: str = 'xgb'
    ) -> dict:
        """
        Predict weather risk category.

        Args:
            rainfall_annual: Annual rainfall in mm
            temperature: Temperature in °C
            humidity: Humidity in %
            wind_speed: Wind speed in km/h
            model_type: 'rf' for Random Forest, 'xgb' for XGBoost

        Returns:
            dict: Prediction results
        """
        if not self.models_loaded:
            return {
                'success': False,
                'error': 'Models not loaded. Check if .pkl files exist in models/ directory.'
            }

        try:
            # Calculate derived features (same as training)
            monsoon_ratio = 0.7  # Default assumption for monsoon contribution
            temp_humidity_index = temperature * humidity / 100
            rainfall_per_month = rainfall_annual / 12

            # Create feature array in correct order
            features = np.array([[
                rainfall_annual,
                temperature,
                humidity,
                wind_speed,
                monsoon_ratio,
                temp_humidity_index,
                rainfall_per_month
            ]])

            # Scale features; silence known sklearn feature-name warning for ndarray input.
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    'ignore',
                    message='.*does not have valid feature names.*',
                    category=UserWarning
                )
                features_scaled = self.scaler.transform(features)

            # Select model
            model = self.xgb_model if model_type == 'xgb' else self.rf_model
            model_name = 'XGBoost' if model_type == 'xgb' else 'Random Forest'

            # Make prediction
            prediction = model.predict(features_scaled)[0]
            probabilities = model.predict_proba(features_scaled)[0]
            confidence = float(max(probabilities))

            # Check for anomaly
            anomaly_score = float(self.isolation_forest.decision_function(features_scaled)[0])
            is_anomaly = self.isolation_forest.predict(features_scaled)[0] == -1

            # Decode label
            risk_category = self.label_encoder.inverse_transform([prediction])[0]

            # Create probability dict
            prob_dict = {
                str(self.label_encoder.classes_[i]): float(round(prob, 4))
                for i, prob in enumerate(probabilities)
            }

            # Determine weather trigger
            weather_trigger = risk_category in ['Drought', 'Flood', 'Heatwave']

            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'model_used': model_name,
                'input': {
                    'rainfall_annual': rainfall_annual,
                    'temperature': temperature,
                    'humidity': humidity,
                    'wind_speed': wind_speed
                },
                'prediction': {
                    'risk_category': risk_category,
                    'confidence': round(confidence, 4),
                    'probabilities': prob_dict
                },
                'weather_trigger': weather_trigger,
                'anomaly_detection': {
                    'is_anomaly': bool(is_anomaly),
                    'anomaly_score': round(anomaly_score, 4)
                },
                'thresholds': {
                    'drought': self.model_config['DROUGHT_THRESHOLD'],
                    'flood': self.model_config['FLOOD_THRESHOLD'],
                    'heatwave': self.model_config['HEATWAVE_TEMP']
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def predict_from_weather_data(self, weather_data: dict, model_type: str = 'xgb') -> dict:
        """
        Predict risk from weather service data.

        Args:
            weather_data: Data from WeatherService
            model_type: Model type to use

        Returns:
            dict: Prediction results
        """
        if not weather_data.get('success'):
            return {
                'success': False,
                'error': 'Invalid weather data provided'
            }

        # Extract features from weather data
        temperature = weather_data.get('current_conditions', {}).get('temperature', 25)
        humidity = weather_data.get('current_conditions', {}).get('humidity', 70)
        wind_speed = weather_data.get('current_conditions', {}).get('wind_speed', 10)

        # Get estimated annual rainfall
        rainfall_annual = weather_data.get('rainfall_analysis', {}).get('estimated_annual_mm', 1000)

        return self.predict_weather_risk(
            rainfall_annual=rainfall_annual,
            temperature=temperature,
            humidity=humidity,
            wind_speed=wind_speed,
            model_type=model_type
        )

    def get_crop_optimal_conditions(self, crop_type: str) -> dict:
        """
        Get optimal growing conditions for a crop.

        Args:
            crop_type: Type of crop

        Returns:
            dict: Optimal conditions
        """
        if not self.models_loaded:
            return {
                'success': False,
                'error': 'Models not loaded'
            }

        crop_lower = crop_type.lower()

        if crop_lower in self.crop_optimal:
            conditions = self.crop_optimal[crop_lower]
            return {
                'success': True,
                'crop': crop_type,
                'optimal_conditions': conditions
            }
        else:
            # Return available crops
            return {
                'success': False,
                'error': f'Crop "{crop_type}" not found',
                'available_crops': list(self.crop_optimal.keys())
            }

    def assess_crop_stress(
        self,
        crop_type: str,
        current_temp: float,
        current_humidity: float,
        current_rainfall: float
    ) -> dict:
        """
        Assess crop stress based on deviation from optimal conditions.

        Args:
            crop_type: Type of crop
            current_temp: Current temperature
            current_humidity: Current humidity
            current_rainfall: Current/recent rainfall

        Returns:
            dict: Stress assessment
        """
        optimal = self.get_crop_optimal_conditions(crop_type)

        if not optimal['success']:
            return optimal

        conditions = optimal['optimal_conditions']

        # Calculate deviations
        temp_optimal = conditions['temp_optimal']
        temp_tolerance = conditions['temp_tolerance']
        temp_deviation = abs(current_temp - temp_optimal) / temp_tolerance if temp_tolerance > 0 else 0

        humidity_optimal = conditions['humidity_optimal']
        humidity_tolerance = conditions['humidity_tolerance']
        humidity_deviation = abs(current_humidity - humidity_optimal) / humidity_tolerance if humidity_tolerance > 0 else 0

        rainfall_optimal = conditions['rainfall_optimal']
        rainfall_tolerance = conditions['rainfall_tolerance']
        rainfall_deviation = abs(current_rainfall - rainfall_optimal) / rainfall_tolerance if rainfall_tolerance > 0 else 0

        # Calculate overall stress score (0-100, higher = more stress)
        stress_score = min(100, (temp_deviation * 30 + humidity_deviation * 30 + rainfall_deviation * 40))

        # Determine stress level
        if stress_score < 20:
            stress_level = 'None'
        elif stress_score < 40:
            stress_level = 'Low'
        elif stress_score < 60:
            stress_level = 'Moderate'
        elif stress_score < 80:
            stress_level = 'High'
        else:
            stress_level = 'Severe'

        # Expected NDVI reduction based on stress
        expected_ndvi_reduction = min(50, stress_score * 0.5)

        return {
            'success': True,
            'crop': crop_type,
            'current_conditions': {
                'temperature': current_temp,
                'humidity': current_humidity,
                'rainfall': current_rainfall
            },
            'optimal_conditions': conditions,
            'deviations': {
                'temperature': round(temp_deviation, 2),
                'humidity': round(humidity_deviation, 2),
                'rainfall': round(rainfall_deviation, 2)
            },
            'stress_score': round(stress_score, 1),
            'stress_level': stress_level,
            'expected_ndvi_reduction_percent': round(expected_ndvi_reduction, 1)
        }

    def get_model_info(self) -> dict:
        """Get information about loaded models."""
        if not self.models_loaded:
            return {
                'success': False,
                'error': 'Models not loaded'
            }

        return {
            'success': True,
            'models': {
                'random_forest': {
                    'type': 'RandomForestClassifier',
                    'accuracy': self.model_config.get('rf_accuracy', 'N/A')
                },
                'xgboost': {
                    'type': 'XGBClassifier',
                    'accuracy': self.model_config.get('xgb_accuracy', 'N/A')
                },
                'anomaly_detector': {
                    'type': 'IsolationForest'
                }
            },
            'feature_columns': self.feature_columns,
            'classes': list(self.label_encoder.classes_),
            'thresholds': {
                'drought': self.model_config.get('DROUGHT_THRESHOLD'),
                'flood': self.model_config.get('FLOOD_THRESHOLD'),
                'heatwave': self.model_config.get('HEATWAVE_TEMP')
            },
            'available_crops': list(self.crop_optimal.keys())
        }


# Test function
if __name__ == '__main__':
    service = MLService()

    if service.models_loaded:
        print("\nTesting ML Service...")

        # Test predictions
        test_cases = [
            {'rainfall': 300, 'temp': 35, 'humidity': 40, 'wind': 10, 'expected': 'Drought'},
            {'rainfall': 2500, 'temp': 28, 'humidity': 85, 'wind': 15, 'expected': 'Flood'},
            {'rainfall': 1200, 'temp': 30, 'humidity': 70, 'wind': 12, 'expected': 'Normal'},
        ]

        print("\n1. Risk Predictions:")
        for case in test_cases:
            result = service.predict_weather_risk(
                case['rainfall'], case['temp'], case['humidity'], case['wind']
            )
            if result['success']:
                pred = result['prediction']['risk_category']
                conf = result['prediction']['confidence']
                status = "✓" if pred == case['expected'] else "✗"
                print(f"   Expected: {case['expected']}, Got: {pred} ({conf:.1%}) {status}")

        print("\n2. Model Info:")
        info = service.get_model_info()
        print(f"   Classes: {info['classes']}")
        print(f"   Available crops: {len(info['available_crops'])}")

        print("\n3. Crop Stress Assessment:")
        stress = service.assess_crop_stress('rice', 35, 60, 50)
        if stress['success']:
            print(f"   Crop: Rice")
            print(f"   Stress Level: {stress['stress_level']}")
            print(f"   Stress Score: {stress['stress_score']}")
    else:
        print("Models not loaded. Please ensure .pkl files are in models/ directory.")
