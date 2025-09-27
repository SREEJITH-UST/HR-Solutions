import google.generativeai as genai

genai.configure(api_key="AIzaSyACb162ZaLWKqw_xqnr1SZbHPWxErtyGbs")

models = genai.list_models()
for m in models:
    print(m)
