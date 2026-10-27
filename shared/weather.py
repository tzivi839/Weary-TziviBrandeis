"""
weather.py - הכלי החיצוני של Weary: מזג אוויר אמיתי מ-Open-Meteo.

Open-Meteo חינמי ולא צריך מפתח. זה עובד בשני צעדים:
  1. geocoding: שם עיר -> קואורדינטות (קו רוחב ואורך)
  2. forecast: קואורדינטות + תאריך -> טמפרטורות, סיכוי לגשם וכמות גשם

הכלי מחזיר אחת משלוש רמות גשם, שאותן find_clothes מבינה:
  dry   - יבש
  rain  - גשם
  heavy - גשם עז (רק אז מוצעים מגפיים)

הפרמטר client מאפשר "להזריק" client מדומה בבדיקות בלבד,
כדי שהבדיקות ירוצו בלי אינטרנט (התרגיל דורש בדיקות offline).
בשימוש רגיל client=None, ואז נוצר חיבור אמיתי לאינטרנט.
"""
import ssl

import httpx
import truststore

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
RAIN_PROBABILITY = 50   # מאיזה אחוז סיכוי נחשב "יורד גשם"
HEAVY_RAIN_MM = 10      # מאיזו כמות גשם ביום (מ"מ) נחשב "גשם עז"


def rain_level(probability, mm):
    if probability < RAIN_PROBABILITY:
        return "dry"
    return "heavy" if mm >= HEAVY_RAIN_MM else "rain"


def make_client():
    # truststore = "תסמוך על אותן תעודות אבטחה שמערכת ההפעלה סומכת עליהן".
    # בלי זה Python משתמש ברשימת תעודות משלו, ובמחשב של ארגון (שבודק תעבורה)
    # מתקבלת השגיאה CERTIFICATE_VERIFY_FAILED.
    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.Client(timeout=10, verify=ctx)


def get_weather(city, day, client=None):
    client = client or make_client()

    # צעד 1: איפה העיר נמצאת?
    geo = client.get(GEO_URL, params={"name": city, "count": 1}).json()
    if not geo.get("results"):
        # שגיאה ברורה -> המודל יוכל לנסות שוב, למשל עם שם באנגלית
        raise ValueError(f"city not found: {city}")
    place = geo["results"][0]

    # צעד 2: התחזית לאותו יום
    data = client.get(FORECAST_URL, params={
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "daily": "temperature_2m_min,temperature_2m_max,"
                 "precipitation_probability_max,precipitation_sum",
        "timezone": "auto",
        "start_date": day,
        "end_date": day,
    }).json()
    if "daily" not in data:
        raise ValueError(f"no forecast for {day}: {data.get('reason', 'unknown error')}")
    daily = data["daily"]

    t_min = round(daily["temperature_2m_min"][0])
    t_max = round(daily["temperature_2m_max"][0])
    prob = daily["precipitation_probability_max"][0] or 0
    mm = daily["precipitation_sum"][0] or 0

    # פלט קומפקטי: שורה אחת במקום כל ה-JSON הענק של ה-API
    return f"{place['name']} {day}: {t_min}-{t_max}C, rain {prob}% {mm}mm -> {rain_level(prob, mm)}"
