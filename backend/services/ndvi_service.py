"""
NDVI Service - Google Earth Engine Integration
"""

import os
import numpy as np
from datetime import datetime, timedelta
from config import active_config as config


class NDVIService:
    def __init__(self):
        self.ee_initialized = False
        self.ee = None

        if config.ENABLE_EE:
            self._initialize_ee()
        else:
            print("Earth Engine disabled by config (ENABLE_EE=false). Using simulation mode for NDVI.")

    def _initialize_ee(self):
        """Initialize Google Earth Engine."""
        try:
            import ee  # Lazy import to avoid startup failures when GEE deps/auth are missing
            self.ee = ee

            # Try to authenticate and initialize
            # For first time, run: earthengine authenticate
            if config.EE_PROJECT:
                self.ee.Initialize(project=config.EE_PROJECT)
                print(f"Google Earth Engine initialized with project: {config.EE_PROJECT}")
            else:
                self.ee.Initialize()
            self.ee_initialized = True
            print("Google Earth Engine initialized successfully!")
        except Exception as e:
            print(f"Earth Engine initialization failed: {e}")
            print("Using simulation mode for NDVI.")
            self.ee_initialized = False
            self.ee = None

    def get_ndvi_real(self, lat: float, lon: float, days_back: int = 30) -> dict:
        """
        Get real NDVI data from Google Earth Engine (Sentinel-2).

        Args:
            lat: Latitude
            lon: Longitude
            days_back: Number of days to look back

        Returns:
            dict: NDVI data
        """
        if not self.ee_initialized:
            return self.get_ndvi_simulated(lat, lon, days_back)

        try:
            ee = self.ee

            # Create point geometry
            point = ee.Geometry.Point([lon, lat])

            # Define date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Get Sentinel-2 imagery
            collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                         .filterBounds(point)
                         .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                         .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                         .sort('system:time_start', False))

            # Check if we have images
            count = collection.size().getInfo()

            if count == 0:
                return {
                    'success': False,
                    'error': 'No cloud-free images available for this period',
                    'fallback': self.get_ndvi_simulated(lat, lon, days_back)
                }

            # Get the most recent image
            latest_image = collection.first()

            # Calculate NDVI
            ndvi = latest_image.normalizedDifference(['B8', 'B4']).rename('NDVI')

            # Sample the NDVI value at our point
            ndvi_value = ndvi.sample(point, 10).first().get('NDVI').getInfo()

            # Get image date
            image_date = datetime.fromtimestamp(
                latest_image.get('system:time_start').getInfo() / 1000
            ).strftime('%Y-%m-%d')

            # Get historical NDVI values for time series
            def get_ndvi_for_image(image):
                ndvi_img = image.normalizedDifference(['B8', 'B4'])
                value = ndvi_img.sample(point, 10).first().get('nd')
                return ee.Feature(None, {
                    'ndvi': value,
                    'date': image.date().format('YYYY-MM-dd')
                })

            historical = collection.limit(10).map(get_ndvi_for_image)
            historical_data = historical.getInfo()

            time_series = []
            for feature in historical_data['features']:
                props = feature['properties']
                if props['ndvi'] is not None:
                    time_series.append({
                        'date': props['date'],
                        'ndvi': round(props['ndvi'], 4)
                    })

            # Calculate statistics
            ndvi_values = [ts['ndvi'] for ts in time_series if ts['ndvi'] is not None]

            return {
                'success': True,
                'source': 'Google Earth Engine - Sentinel-2',
                'timestamp': datetime.now().isoformat(),
                'location': {'lat': lat, 'lon': lon},
                'current_ndvi': round(ndvi_value, 4) if ndvi_value else None,
                'image_date': image_date,
                'images_found': count,
                'time_series': time_series,
                'statistics': {
                    'mean': round(np.mean(ndvi_values), 4) if ndvi_values else None,
                    'min': round(min(ndvi_values), 4) if ndvi_values else None,
                    'max': round(max(ndvi_values), 4) if ndvi_values else None,
                    'std': round(np.std(ndvi_values), 4) if ndvi_values else None
                }
            }

        except Exception as e:
            print(f"GEE Error: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback': self.get_ndvi_simulated(lat, lon, days_back)
            }

    def get_ndvi_simulated(self, lat: float, lon: float, days_back: int = 90) -> dict:
        """
        Generate simulated NDVI data based on location and season.
        Used as fallback when GEE is not available.

        Args:
            lat: Latitude
            lon: Longitude
            days_back: Number of days for time series

        Returns:
            dict: Simulated NDVI data
        """
        np.random.seed(int(abs(lat * 1000 + lon * 1000)) % 2**32)

        # Base NDVI depends on region (agricultural zones)
        # Higher NDVI for fertile regions
        if 20 <= lat <= 30 and 75 <= lon <= 88:  # Indo-Gangetic Plain
            base_ndvi = 0.65
        elif 8 <= lat <= 15 and 75 <= lon <= 80:  # South India
            base_ndvi = 0.55
        elif 20 <= lat <= 28 and 68 <= lon <= 75:  # Western India (drier)
            base_ndvi = 0.45
        else:
            base_ndvi = 0.50

        # Seasonal variation
        current_month = datetime.now().month

        # Growing season patterns for India
        # Kharif (monsoon): June-October - higher NDVI
        # Rabi (winter): October-March - moderate NDVI
        # Summer: March-June - lower NDVI
        seasonal_factor = {
            1: 0.85, 2: 0.80, 3: 0.70, 4: 0.55,
            5: 0.45, 6: 0.50, 7: 0.75, 8: 0.90,
            9: 0.95, 10: 0.85, 11: 0.80, 12: 0.85
        }

        # Generate time series
        time_series = []
        for i in range(days_back, 0, -5):  # Every 5 days (like Sentinel-2)
            date = datetime.now() - timedelta(days=i)
            month = date.month

            # Calculate NDVI for this date
            seasonal = seasonal_factor.get(month, 0.7)
            noise = np.random.normal(0, 0.05)
            ndvi = base_ndvi * seasonal + noise
            ndvi = max(0.1, min(0.95, ndvi))  # Clamp to valid range

            time_series.append({
                'date': date.strftime('%Y-%m-%d'),
                'ndvi': round(ndvi, 4)
            })

        # Current NDVI
        current_ndvi = time_series[-1]['ndvi'] if time_series else base_ndvi

        # Calculate expected NDVI (based on historical average for this season)
        expected_ndvi = base_ndvi * seasonal_factor.get(current_month, 0.7)

        # NDVI values
        ndvi_values = [ts['ndvi'] for ts in time_series]

        return {
            'success': True,
            'source': 'Simulated (based on location and season)',
            'timestamp': datetime.now().isoformat(),
            'location': {'lat': lat, 'lon': lon},
            'current_ndvi': round(current_ndvi, 4),
            'expected_ndvi': round(expected_ndvi, 4),
            'image_date': datetime.now().strftime('%Y-%m-%d'),
            'images_found': len(time_series),
            'time_series': time_series,
            'statistics': {
                'mean': round(np.mean(ndvi_values), 4),
                'min': round(min(ndvi_values), 4),
                'max': round(max(ndvi_values), 4),
                'std': round(np.std(ndvi_values), 4)
            }
        }

    def get_ndvi(self, lat: float, lon: float, days_back: int = 90) -> dict:
        """
        Get NDVI data - tries real GEE first, falls back to simulation.

        Args:
            lat: Latitude
            lon: Longitude
            days_back: Days to look back

        Returns:
            dict: NDVI data
        """
        if self.ee_initialized:
            result = self.get_ndvi_real(lat, lon, days_back)
            if result['success']:
                return result
            # Use fallback if real data failed
            return result.get('fallback', self.get_ndvi_simulated(lat, lon, days_back))
        else:
            return self.get_ndvi_simulated(lat, lon, days_back)

    def analyze_crop_health(self, lat: float, lon: float, crop_type: str = None) -> dict:
        """
        Analyze crop health based on NDVI data.

        Args:
            lat: Latitude
            lon: Longitude
            crop_type: Type of crop (for optimal NDVI comparison)

        Returns:
            dict: Crop health analysis
        """
        # Get NDVI data
        ndvi_data = self.get_ndvi(lat, lon, days_back=90)

        if not ndvi_data['success']:
            return ndvi_data

        current_ndvi = ndvi_data['current_ndvi']
        expected_ndvi = ndvi_data.get('expected_ndvi', 0.6)

        # Calculate NDVI drop
        ndvi_drop = 0
        if len(ndvi_data['time_series']) > 1:
            # Compare current to 30-day average
            recent_values = [ts['ndvi'] for ts in ndvi_data['time_series'][-6:]]  # Last 30 days
            older_values = [ts['ndvi'] for ts in ndvi_data['time_series'][:-6]]   # Before that

            if older_values:
                avg_older = np.mean(older_values)
                avg_recent = np.mean(recent_values)
                ndvi_drop = (avg_older - avg_recent) / avg_older * 100 if avg_older > 0 else 0

        # Determine crop health status
        if current_ndvi >= config.NDVI_HEALTHY_MIN:
            health_status = 'Healthy'
            health_score = 90 + (current_ndvi - config.NDVI_HEALTHY_MIN) * 20
        elif current_ndvi >= config.NDVI_STRESS_THRESHOLD:
            health_status = 'Moderate Stress'
            health_score = 60 + (current_ndvi - config.NDVI_STRESS_THRESHOLD) * 200
        elif current_ndvi >= config.NDVI_SEVERE_THRESHOLD:
            health_status = 'Severe Stress'
            health_score = 30 + (current_ndvi - config.NDVI_SEVERE_THRESHOLD) * 200
        else:
            health_status = 'Critical - Crop Damage'
            health_score = current_ndvi * 150

        health_score = max(0, min(100, health_score))

        # Determine NDVI trigger
        ndvi_trigger = False
        trigger_reasons = []

        if current_ndvi < config.NDVI_STRESS_THRESHOLD:
            ndvi_trigger = True
            trigger_reasons.append(f'Current NDVI ({current_ndvi:.2f}) below stress threshold ({config.NDVI_STRESS_THRESHOLD})')

        if ndvi_drop > config.NDVI_DROP_THRESHOLD * 100:
            ndvi_trigger = True
            trigger_reasons.append(f'NDVI dropped by {ndvi_drop:.1f}% (threshold: {config.NDVI_DROP_THRESHOLD * 100}%)')

        # Compare to expected
        if current_ndvi < expected_ndvi * 0.7:  # More than 30% below expected
            ndvi_trigger = True
            trigger_reasons.append(f'NDVI {((expected_ndvi - current_ndvi) / expected_ndvi * 100):.1f}% below expected')

        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'location': ndvi_data['location'],
            'source': ndvi_data['source'],
            'current_ndvi': current_ndvi,
            'expected_ndvi': round(expected_ndvi, 4),
            'ndvi_drop_percent': round(ndvi_drop, 2),
            'health_status': health_status,
            'health_score': round(health_score, 1),
            'ndvi_trigger': ndvi_trigger,
            'trigger_reasons': trigger_reasons,
            'time_series': ndvi_data['time_series'],
            'statistics': ndvi_data['statistics'],
            'thresholds': {
                'healthy_min': config.NDVI_HEALTHY_MIN,
                'stress': config.NDVI_STRESS_THRESHOLD,
                'severe': config.NDVI_SEVERE_THRESHOLD,
                'drop_threshold': config.NDVI_DROP_THRESHOLD * 100
            }
        }


# Test function
if __name__ == '__main__':
    service = NDVIService()

    # Test with sample coordinates (Lucknow, India)
    lat, lon = 26.8467, 80.9462

    print("Testing NDVI Service...")
    print(f"\nLocation: {lat}, {lon}")

    print("\n1. Get NDVI Data:")
    ndvi = service.get_ndvi(lat, lon)
    print(f"   Source: {ndvi['source']}")
    print(f"   Current NDVI: {ndvi['current_ndvi']}")
    print(f"   Statistics: {ndvi['statistics']}")

    print("\n2. Crop Health Analysis:")
    health = service.analyze_crop_health(lat, lon)
    print(f"   Health Status: {health['health_status']}")
    print(f"   Health Score: {health['health_score']}")
    print(f"   NDVI Trigger: {health['ndvi_trigger']}")
    if health['trigger_reasons']:
        print(f"   Trigger Reasons: {health['trigger_reasons']}")
