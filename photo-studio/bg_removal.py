# -*- coding: utf-8 -*-
"""Λευκό φόντο ΧΩΡΙΣ γενετικό AI (τοπική αποκοπή φόντου με rembg/U²-Net).

Σε αντίθεση με το Nano Banana, εδώ η εικόνα ΔΕΝ αναδημιουργείται: αφαιρείται
μόνο το φόντο και τα pixels του προϊόντος μένουν ακριβώς όπως στη φωτογραφία.
Η μάσκα «σκληραίνει» στο εσωτερικό (πλήρης αδιαφάνεια), ώστε το blending να
αγγίζει μόνο τα άκρα.
"""

import numpy as np
from PIL import Image

_session = None


class BgRemovalError(Exception):
    pass


def _get_session():
    global _session
    if _session is None:
        try:
            from rembg import new_session
        except ImportError as e:
            raise BgRemovalError(
                "Λείπει το rembg. Τρέξε: pip install rembg onnxruntime "
                "(την πρώτη φορά κατεβάζει το μοντέλο αποκοπής ~176MB)."
            ) from e
        _session = new_session("u2net")
    return _session


def remove_background_local(img: Image.Image, *, margin_pct: float = 0.03) -> Image.Image:
    """Αποκόπτει το φόντο τοπικά και επιστρέφει το προϊόν σε λευκό φόντο,
    κομμένο γύρω από το προϊόν με μικρό περιθώριο."""
    from rembg import remove

    src = img.convert("RGB")
    # Ζητάμε ΜΟΝΟ τη μάσκα: το έτοιμο cutout του rembg πολλαπλασιάζει τα RGB
    # με τη μάσκα (αλλοίωση ±1), ενώ εμείς κάνουμε paste την αυθεντική εικόνα.
    mask = remove(src, session=_get_session(), only_mask=True)
    alpha = np.array(mask.convert("L"))

    # Σκλήρυνση: το εσωτερικό του προϊόντος γίνεται 100% αδιαφανές ώστε τα
    # pixels του να περάσουν αναλλοίωτα· ομαλή μετάβαση μένει μόνο στα άκρα.
    alpha = np.where(alpha >= 200, 255, alpha).astype(np.uint8)

    ys, xs = np.nonzero(alpha)
    if len(xs) == 0:
        raise BgRemovalError(
            "Δεν εντοπίστηκε προϊόν στη φωτογραφία (η αποκοπή επέστρεψε κενή μάσκα)."
        )

    # Crop γύρω από το προϊόν με περιθώριο
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    mx = round((x1 - x0) * margin_pct)
    my = round((y1 - y0) * margin_pct)
    x0, y0 = max(0, x0 - mx), max(0, y0 - my)
    x1, y1 = min(alpha.shape[1] - 1, x1 + mx), min(alpha.shape[0] - 1, y1 + my)

    src_crop = src.crop((x0, y0, x1 + 1, y1 + 1))
    mask_crop = Image.fromarray(alpha[y0:y1 + 1, x0:x1 + 1], mode="L")
    white = Image.new("RGB", src_crop.size, (255, 255, 255))
    white.paste(src_crop, (0, 0), mask_crop)
    return white
