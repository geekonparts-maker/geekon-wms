# -*- coding: utf-8 -*-
"""Σύνδεση με τα image models του Gemini (Nano Banana) μέσω του google-genai SDK.

Καμία σιωπηλή αποτυχία: αν το μοντέλο δεν επιστρέψει εικόνα, σηκώνεται
GeminiError με το μήνυμα/κείμενο του μοντέλου ώστε να φανεί στο UI.
"""

from io import BytesIO
from PIL import Image

# Nano Banana = gemini-2.5-flash-image. Το Pro είναι ακριβότερο αλλά καλύτερο
# σε δύσκολα καθαρίσματα.
MODELS = [
    "gemini-2.5-flash-image",
    "gemini-3-pro-image-preview",
]
DEFAULT_MODEL = MODELS[0]

CLEANUP_PROMPT = (
    "Professional e-commerce product photo retouching. Isolate the product and "
    "place it on a pure white background (#FFFFFF), centered, evenly lit, with "
    "no shadows and no background clutter. Remove any watermark text or logo "
    "overlays that were stamped on top of the photo. CRITICAL: do not alter, "
    "redraw, distort or restyle the product itself in any way - keep its exact "
    "shape, proportions, colors, connectors, ports, stickers and printed labels "
    "unchanged and sharp. Keep the entire product fully in frame."
)


class GeminiError(Exception):
    """Σφάλμα κλήσης ή άρνηση του μοντέλου — εμφανίζεται αυτούσιο στον χρήστη."""


def edit_image(api_key: str, model: str, image: Image.Image, prompt: str) -> Image.Image:
    """Στέλνει εικόνα + οδηγία στο μοντέλο και επιστρέφει τη νέα εικόνα."""
    if not api_key:
        raise GeminiError(
            "Δεν έχει οριστεί API key. Βάλε το στο πεδίο της πλαϊνής μπάρας "
            "ή σε αρχείο .env ως GEMINI_API_KEY."
        )
    try:
        from google import genai  # import εδώ ώστε το υπόλοιπο app να δουλεύει χωρίς το SDK
    except ImportError as e:
        raise GeminiError(
            "Λείπει το google-genai SDK. Τρέξε: pip install google-genai"
        ) from e

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=[prompt, image],
        )
    except Exception as e:
        raise GeminiError(f"Η κλήση στο Gemini API απέτυχε: {e}") from e

    texts: list[str] = []
    for candidate in (response.candidates or []):
        content = getattr(candidate, "content", None)
        for part in (getattr(content, "parts", None) or []):
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None):
                return Image.open(BytesIO(inline.data))
            if getattr(part, "text", None):
                texts.append(part.text)

    detail = " ".join(texts).strip() or "Το μοντέλο δεν επέστρεψε εικόνα (πιθανή άρνηση ή φίλτρο)."
    raise GeminiError(f"Δεν παραλήφθηκε εικόνα από το μοντέλο. Απάντηση: {detail}")
