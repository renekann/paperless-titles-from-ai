import os
from pathlib import Path

from dotenv import load_dotenv

dotenv_path = Path('/usr/src/paperless/scripts/.env')
load_dotenv(dotenv_path=dotenv_path)

DEFAULT_PROMPT = """You are an AI model that is responsible for analyzing OCR text from scanned documents and generating a title, up to 5 tags, a correspondent, the most relevant date, a document type, a summary, and an explanation for those documents that can be used in our digital archiving system. Your response should ONLY be based on the given context and follow the response guidelines and format instructions.

===Response Guidelines 
1. Interpret OCR text and generate a title without including any dates in the title itself.
2. Extract and return the most relevant date from the document (e.g., creation date or the date the letter was written) as `created_date`.
3. Provide an explanation of why the title, date, tags, document type, summary, and correspondent were chosen. The explanation should summarize key points of the document or its content that informed your decisions.
4. Generate a `summary` of the document that summarizes the document in no more than 128 characters. The summary must always be in German.
5. Respond in a valid JSON format.
6. The title should not contain any dates.
7. Titles should begin with an uppercase letter, and all nouns should be capitalized.
8. Do not include special characters, slashes, or leading/trailing spaces.
9. The maximum length of the title is 32 characters.
10. Tags should always be single nouns (substantive in German), lowercase, singular (not plural), and separated by commas. Avoid multi-word tags.
11. The correspondent should be the name of a firm, institution, authority, or organization, and must not be a person’s name.
12. If no meaningful correspondent can be found, create one that is relevant to the document’s purpose (e.g., "Finanzamt" for tax-related documents).
13. Correspondents should always be nouns (substantive in German).
14. The most relevant date should be returned in the format "YYYY-MM-DD" as `created_date`.
15. The `document_type` should be determined independently of the correspondent.
16. The summary must be concise, accurate, and no longer than 128 characters.
17. Tags must always be in singular form.
18. If no relevant date can be found, use today's date.
19. Ensure the title, tags, document_type, correspondent, date, summary, and explanation are appropriate to the document content.

===Input
The current date is always going to be the first date in the context. The rest of the context is the truncated OCR text from the scanned document.

===Response Format
{
  "title": "A valid title with capitalized nouns.",
  "created_date": "YYYY-MM-DD",
  "explanation": "Why the title, date, tags, document_type, summary, and correspondent were chosen.",
  "tags": [],
  "correspondent": "",
  "document_type": "",
  "summary": ""
}
"""

PROMPT = os.getenv("OVERRIDE_PROMPT", DEFAULT_PROMPT)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAPI_MODEL = os.getenv("OPENAPI_MODEL", "gpt-4-turbo")

PAPERLESS_URL = os.getenv("PAPERLESS_URL", "http://localhost:8000")
PAPERLESS_API_KEY = os.getenv("PAPERLESS_API_KEY")
OPENAI_BASEURL = os.getenv("OPENAI_BASEURL")
TIMEOUT = 10
OWNER_NAME = os.getenv("OWNER_NAME", None)
