import google.generativeai as genai
from django.conf import settings

def get_gemini_client():
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel('models/gemini-2.5-flash')
