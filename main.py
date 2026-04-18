from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware

# 🔑 Add your API key here
import os
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (for now)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 Run ONCE when server starts
try:
    available_models = [
        m.name for m in genai.list_models()
        if 'generateContent' in m.supported_generation_methods
    ]

    if not available_models:
        raise Exception("No compatible models found.")

    model_name = next((m for m in available_models if '1.5-flash' in m), None)
    if not model_name:
        model_name = next((m for m in available_models if 'flash' in m), available_models[0])

    clean_model_name = model_name.replace("models/", "")
    model = genai.GenerativeModel(clean_model_name)

    print(f"✅ Using model: {clean_model_name}")

except Exception as e:
    print(f"❌ Model initialization failed: {e}")
    model = None

# Request body structure
class CodeInput(BaseModel):
    code: str

@app.post("/decide")
def decide(input: CodeInput):

    if model is None:
        raise HTTPException(status_code=500, detail="Model not initialized.")

    prompt = f"""
    You are a senior software engineer performing a professional code review.

    Analyze the given code and return the response STRICTLY in JSON format like this:

    {{
      "bugs": "...",
      "improvements": "...",
      "performance": "...",
      "refactored_code": "..."
    }}

    Rules:
    - Do NOT add any explanation outside JSON
    - Keep response clean and valid JSON
    - refactored_code should be proper code

    Code:
    {input.code}
    """

    try:
        response = model.generate_content(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model generation failed: {str(e)}")

    return {
        "result": response.text
    }

import json


@app.post("/review")
def review(input: CodeInput):
    if not input.code or input.code.strip() == "":
        raise HTTPException(status_code=400, detail="Code input cannot be empty.")

    if model is None:
        raise HTTPException(status_code=500, detail="Model not initialized.")

    prompt = f"""
    You are a senior software engineer performing a professional code review.

    Analyze the given code and return ONLY valid JSON (no markdown, no ```).

    Format:
    {{
      "bugs": "...",
      "improvements": "...",
      "performance": "...",
      "refactored_code": "..."
    }}

    Code:
    {input.code}
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # 🔥 CLEAN STEP (important)
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(text)

        return parsed

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))