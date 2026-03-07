"""
Weather Service - OpenWeatherMap API Integration
"""

import requests
from datetime import datetime, timedelta
import numpy as np
from config import active_config as config


class WeatherService:
    def __init__(self):
        self.api_key = config.OPENWEATHER_API_KEY
        self.base_url = config.OPENWEATHER_BASE_URL

    def get_current_weather(self, lat: float, lon: float) -> dict:
        """
        Get current weather data for a location.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            dict: Weather data including temp, humidity, rainfall, etc.
        """
        try:
            # Current weather endpoint
            url = f"{self.base_url}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract relevant data
            weather_data = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'location': {
                    'lat': lat,
                    'lon': lon,
                    'name': data.get('name', 'Unknown'),
                    'country': data.get('sys', {}).get('country', 'Unknown')
                },
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'temp_min': data['main']['temp_min'],
                'temp_max': data['main']['temp_max'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'wind_speed': data['wind']['speed'] * 3.6,  # Convert m/s to km/h
                'wind_direction': data['wind'].get('deg', 0),
                'clouds': data['clouds']['all'],
                'weather_condition': data['weather'][0]['main'],
                'weather_description': data['weather'][0]['description'],
                'rainfall_1h': data.get('rain', {}).get('1h', 0),
                'rainfall_3h': data.get('rain', {}).get('3h', 0),
            }

            return weather_data

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_forecast(self, lat: float, lon: float, days: int = 5) -> dict:
        """
        Get weather forecast for next N days.

        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days (max 5 for free tier)

        Returns:
            dict: Forecast data
        """
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': min(days * 8, 40)  # 8 readings per day, max 40
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Process forecast data
            forecasts = []
            daily_data = {}

            for item in data['list']:
                dt = datetime.fromtimestamp(item['dt'])
                date_key = dt.strftime('%Y-%m-%d')

                if date_key not in daily_data:
                    daily_data[date_key] = {
                        'temps': [],
                        'humidity': [],
                        'rainfall': [],
                        'wind': []
                    }

                daily_data[date_key]['temps'].append(item['main']['temp'])
                daily_data[date_key]['humidity'].append(item['main']['humidity'])
                daily_data[date_key]['rainfall'].append(item.get('rain', {}).get('3h', 0))
                daily_data[date_key]['wind'].append(item['wind']['speed'] * 3.6)

            # Aggregate daily data
            for date_key, values in daily_data.items():
                forecasts.append({
                    'date': date_key,
                    'temp_avg': round(np.mean(values['temps']), 1),
                    'temp_min': round(min(values['temps']), 1),
                    'temp_max': round(max(values['temps']), 1),
                    'humidity_avg': round(np.mean(values['humidity']), 1),
                    'rainfall_total': round(sum(values['rainfall']), 1),
                    'wind_avg': round(np.mean(values['wind']), 1)
                })

            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'location': {
                    'lat': lat,
                    'lon': lon,
                    'name': data['city']['name'],
                    'country': data['city']['country']
                },
                'forecasts': forecasts[:days]
            }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_historical_rainfall(self, lat: float, lon: float, days: int = 30) -> dict:
        """
        Estimate historical rainfall based on current conditions and seasonal patterns.
        Note: Free OpenWeatherMap doesn't provide historical data, so we estimate.

        Args:
            lat: Latitude
            lon: Longitude
            days: Number of past days to estimate

        Returns:
            dict: Estimated rainfall data
        """
        # Get current weather
        current = self.get_current_weather(lat, lon)

        if not current['success']:
            return current

        # Estimate based on current conditions and Indian monsoon patterns
        current_month = datetime.now().month

        # Monsoon months (June-September) have higher rainfall
        monsoon_multiplier = {
            1: 0.1, 2: 0.1, 3: 0.15, 4: 0.2,
            5: 0.3, 6: 0.8, 7: 1.0, 8: 0.9,
            9: 0.7, 10: 0.4, 11: 0.15, 12: 0.1
        }

        base_daily_rainfall = current['rainfall_1h'] * 24 if current['rainfall_1h'] > 0 else 2
        multiplier = monsoon_multiplier.get(current_month, 0.5)

        # Generate estimated daily rainfall for past N days
        daily_rainfall = []
        total_rainfall = 0

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            # Add some randomness
            variation = np.random.uniform(0.5, 1.5)
            daily_rain = base_daily_rainfall * multiplier * variation

            daily_rainfall.append({
                'date': date.strftime('%Y-%m-%d'),
                'rainfall_mm': round(daily_rain, 1)
            })
            total_rainfall += daily_rain

        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'location': current['location'],
            'period_days': days,
            'total_rainfall_mm': round(total_rainfall, 1),
            'avg_daily_rainfall_mm': round(total_rainfall / days, 1),
            'estimated_annual_mm': round((total_rainfall / days) * 365, 1),
            'daily_data': daily_rainfall[::-1],  # Chronological order
            'note': 'Estimated based on current conditions and seasonal patterns'
        }

    def analyze_weather_risk(self, lat: float, lon: float) -> dict:
        """
        Analyze weather conditions for risk assessment.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            dict: Weather risk analysis
        """
        current = self.get_current_weather(lat, lon)
        historical = self.get_historical_rainfall(lat, lon, days=30)
        forecast = self.get_forecast(lat, lon, days=5)

        if not current['success']:
            return current

        # Analyze risks
        risks = []
        weather_trigger = False
        risk_level = 'Normal'

        # Check drought
        estimated_annual = historical.get('estimated_annual_mm', 1000)
        if estimated_annual < config.DROUGHT_THRESHOLD:
            risks.append({
                'type': 'Drought',
                'severity': 'High' if estimated_annual < 500 else 'Medium',
                'details': f'Estimated annual rainfall: {estimated_annual:.0f}mm (threshold: {config.DROUGHT_THRESHOLD}mm)'
            })
            weather_trigger = True
            risk_level = 'Drought'

        # Check flood
        if estimated_annual > config.FLOOD_THRESHOLD:
            risks.append({
                'type': 'Flood',
                'severity': 'High' if estimated_annual > 2500 else 'Medium',
                'details': f'Estimated annual rainfall: {estimated_annual:.0f}mm (threshold: {config.FLOOD_THRESHOLD}mm)'
            })
            weather_trigger = True
            risk_level = 'Flood'

        # Check heatwave
        if current['temperature'] > config.HEATWAVE_TEMP:
            risks.append({
                'type': 'Heatwave',
                'severity': 'High' if current['temperature'] > 45 else 'Medium',
                'details': f'Current temperature: {current["temperature"]}°C (threshold: {config.HEATWAVE_TEMP}°C)'
            })
            weather_trigger = True
            risk_level = 'Heatwave'

        # Check forecast for upcoming risks
        if forecast['success']:
            upcoming_rain = sum(f['rainfall_total'] for f in forecast['forecasts'])
            if upcoming_rain > 200:  # Heavy rain expected
                risks.append({
                    'type': 'Heavy Rain Warning',
                    'severity': 'Medium',
                    'details': f'Expected rainfall in next 5 days: {upcoming_rain:.0f}mm'
                })

        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'location': current['location'],
            'current_conditions': {
                'temperature': current['temperature'],
                'humidity': current['humidity'],
                'wind_speed': current['wind_speed'],
                'weather': current['weather_description']
            },
            'rainfall_analysis': {
                'last_30_days_mm': historical.get('total_rainfall_mm', 0),
                'estimated_annual_mm': estimated_annual,
                'daily_average_mm': historical.get('avg_daily_rainfall_mm', 0)
            },
            'risk_level': risk_level,
            'weather_trigger': weather_trigger,
            'risks': risks,
            'forecast_summary': forecast.get('forecasts', [])[:3]
        }


# Test function
if __name__ == '__main__':
    service = WeatherService()

    # Test with sample coordinates (Lucknow, India)
    lat, lon = 26.8467, 80.9462

    print("Testing Weather Service...")
    print("\n1. Current Weather:")
    current = service.get_current_weather(lat, lon)
    print(f"   Success: {current['success']}")
    if current['success']:
        print(f"   Location: {current['location']['name']}")
        print(f"   Temperature: {current['temperature']}°C")
        print(f"   Humidity: {current['humidity']}%")

    print("\n2. Weather Risk Analysis:")
    risk = service.analyze_weather_risk(lat, lon)
    if risk['success']:
        print(f"   Risk Level: {risk['risk_level']}")
        print(f"   Weather Trigger: {risk['weather_trigger']}")
