import google.genai as genai
from google.genai import types
from dotenv import load_dotenv
from utils.logger import logger
load_dotenv()
import os
client = genai.Client(api_key = os.getenv("GEMINI_API_KEY"))
class Geminiservice:
    def chat_with_gemini(self,user_input):
        try:
            logger.info('sending request to Gemini')
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
        except Exception as e:
            logger.error(f'Gemini API failed: {e}')
            return "service unavailable"