class WeatherService:
    @staticmethod
    def get_forecast(county):
        """
        Returns a mock weather forecast dictionary tailored to specific Kenyan agricultural counties.
        """
        county_cleaned = county.strip().lower() if county else "general"
        
        # Kakamega - high rainfall / humid
        if "kakamega" in county_cleaned:
            return {
                "temp": 24.5,
                "condition": "Mvua ya Wastani (Moderate Rain / Showers)",
                "precipitation": 75,
                "wind": 12.0,
                "alert": "Tahadhari ya mvua kubwa usiku wa leo. Hakikisha mitaro ya kupitisha maji ipo safi."
            }
        # Bungoma - warm, seasonal rains
        elif "bungoma" in county_cleaned:
            return {
                "temp": 26.2,
                "condition": "Mawingu kiasi (Partly Cloudy)",
                "precipitation": 20,
                "wind": 9.5,
                "alert": None
            }
        # Uasin Gishu - high altitude, cool grain basket
        elif "uasin" in county_cleaned or "gishu" in county_cleaned:
            return {
                "temp": 21.0,
                "condition": "Upepo mwingi na baridi (Windy & Cool)",
                "precipitation": 10,
                "wind": 18.0,
                "alert": "Hali ya hewa inafaa kwa uvunaji na kukausha nafaka."
            }
        # Default fallback
        return {
            "temp": 23.0,
            "condition": "Jua na Mawingu (Sunny Intervals)",
            "precipitation": 30,
            "wind": 10.0,
            "alert": None
        }
