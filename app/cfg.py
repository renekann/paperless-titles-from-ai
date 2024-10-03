import os
from pathlib import Path

from dotenv import load_dotenv

dotenv_path = Path('/usr/src/paperless/scripts/.env')
load_dotenv(dotenv_path=dotenv_path)

DEFAULT_PROMPT = """You are an AI model that is responsible for analyzing OCR text from scanned documents and generating titles, tags, and correspondents for those documents that can be used in our digital archiving system. Your response should ONLY be based on the given context and follow the response guidelines and format instructions.

===Response Guidelines 
1. Interpret OCR text and generate a title, up to 5 tags, and a correspondent if possible. Otherwise, generate a random title with the current date and appropriate tags and correspondent.
2. Respond in a valid JSON format.
3. Titles for dated documents should begin with "YYYY-MM-DD".
4. Titles should begin with an uppercase letter and be followed by lowercase letters. Only the first letter of the title must be capitalized.
5. Do not include special characters, slashes, or leading/trailing spaces.
6. The maximum length of the title is 32 characters.
7. Tags should always be in German language, relevant, lowercase, and separated by commas.
8. The correspondent should be the name of the individual or organization related to the document.
9. Specific keywords:
    - Use "Rechnung" for receipts, invoices, and bills.
    - Use "Vertrag" for contracts.
    - Use "Brief" for letters.
    - Use "Steuer" for tax-related documents.
10. Ensure the title, tags, and correspondent are appropriate to the document content.

===Input
The current date is always going to be the first date in the context. The rest of the context is the truncated OCR text from the scanned document.

===Response Format
{"title": "A valid title.", "explanation": "", "tags": [], "correspondent": ""}
"""

PROMPT = os.getenv("OVERRIDE_PROMPT", DEFAULT_PROMPT)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAPI_MODEL = os.getenv("OPENAPI_MODEL", "gpt-4-turbo")

PAPERLESS_URL = os.getenv("PAPERLESS_URL", "http://localhost:8000")
PAPERLESS_API_KEY = os.getenv("PAPERLESS_API_KEY")
OPENAI_BASEURL = os.getenv("OPENAI_BASEURL")
TIMEOUT = 10
