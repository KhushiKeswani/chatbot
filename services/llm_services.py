import google.genai as genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()
import os
apikey = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key = apikey)
class Geminiservice:
    def chat_with_gemini(self,user_input):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                config=types.GenerateContentConfig(
                    temperature = 0.2,
                    system_instruction="""

                    Rules:
                    - If uncertain, say you do not know.
                    - Do not make up facts.
                    - Ask for clarification when needed.
                    - Give concise answers.
                    - answer every question correctly.
                    -always ask follow up questions.
                    """),
                contents=user_input
            )
            return response.text
        except Exception:
            return "service unavailable"