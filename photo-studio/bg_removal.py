# -*- coding: utf-8 -*-
"""Λευκό φόντο ΧΩΡΙΣ γενετικό AI — τα pixels του προϊόντος δεν αλλοιώνονται ποτέ.

Δύο μέθοδοι, με αυτόματη επιλογή:

1. «Φωτεινό ομοιόμορφο φόντο» (π.χ. φωτογραφίες προμηθευτών ήδη σε λευκό):
   το φόντο εκτιμάται από τα περιθώρια της εικόνας και αφαιρείται ό,τι
   συνδέεται με αυτά — ντετερμινιστικό, χωρίς μοντέλο. Ό,τι είναι «μέσα»
   στο προϊόν (τρύπες, ετικέτες, ανοιχτόχρωμες περιοχές) μένει ως έχει.
2. Μοντέλο αποκοπής (rembg/U²-Net) για φωτογραφίες με «ζωντανό» φόντο
   (πάγκος, γραφείο κ.λπ.). Χρησιμοποιείται ΜΟΝΟ η μάσκα του — το paste
   γίνεται με την αυθεντική εικόνα (το έτοιμο cutout του rembg αλλοιώνει
   τα RGB κατά ±1).

Και στις δύο, το εσωτερικό της μάσκας σκληραίνει σε πλήρη αδιαφάνεια ώστε
τα pixels του προϊόντος να περνούν bit-ακριβή· ομαλή μετάβαση μένει μόνο
στα άκρα.
"""

import numpy as np
from PIL import Image, ImageFilter

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


def _border_stats(arr: np.ndarray, band: int = 10):
    """Χρώμα και ομοιομορφία του πλαισίου της εικόνας."""
    b = min(band, arr.shape[0] // 4, arr.shape[1] // 4)
    frame = np.concatenate([
        arr[:b].reshape(-1, 3), arr[-b:].reshape(-1, 3),
        arr[:, :b].reshape(-1, 3), arr[:, -b:].reshape(-1, 3),
    ]).astype(np.float32)
    return np.median(frame, axis=0), frame.std(axis=0).max()


def _mask_border_method(arr: np.ndarray, bg: np.ndarray, thr: int = 18) -> np.ndarray:
    """Μάσκα προϊόντος: ό,τι ΔΕΝ ανήκει στο φόντο που «αγγίζει» τα περιθώρια.
    Περιοχές σαν το φόντο αλλά κλεισμένες μέσα στο προϊόν παραμένουν προϊόν."""
    from scipy import ndimage

    diff = np.abs(arr.astype(np.int16) - bg.astype(np.int16)).max(axis=2)
    not_bg = diff > thr
    labels, _ = ndimage.label(~not_bg)
    edge_labels = np.unique(np.concatenate([
        labels[0], labels[-1], labels[:, 0], labels[:, -1]
    ]))
    edge_labels = edge_labels[edge_labels != 0]
    background = np.isin(labels, edge_labels)
    return np.where(background, 0, 255).astype(np.uint8)


def _mask_model_method(src: Image.Image) -> np.ndarray:
    from rembg import remove
    mask = remove(src, session=_get_session(), only_mask=True)
    return np.array(mask.convert("L"))


def _feather(mask: np.ndarray) -> np.ndarray:
    """Ελαφρύ feather στα άκρα και σκλήρυνση εσωτερικού σε πλήρη αδιαφάνεια."""
    soft = np.array(Image.fromarray(mask).filter(ImageFilter.GaussianBlur(1)))
    return np.where(mask >= 200, 255, soft).astype(np.uint8)


def remove_background_local(img: Image.Image, *, margin_pct: float = 0.03) -> Image.Image:
    """Επιστρέφει το προϊόν σε λευκό φόντο, κομμένο γύρω του με μικρό
    περιθώριο, με τα pixels του προϊόντος αναλλοίωτα."""
    src = img.convert("RGB")
    arr = np.asarray(src)
    area = arr.shape[0] * arr.shape[1]

    bg, border_std = _border_stats(arr)
    candidates = []

    # Φωτεινό & ομοιόμορφο πλαίσιο → πρώτα η ντετερμινιστική μέθοδος
    if border_std < 14 and bg.min() > 180:
        candidates.append(("border", lambda: _mask_border_method(arr, bg)))
        candidates.append(("model", lambda: _mask_model_method(src)))
    else:
        candidates.append(("model", lambda: _mask_model_method(src)))
        candidates.append(("border", lambda: _mask_border_method(arr, bg)))

    alpha = None
    for _name, fn in candidates:
        m = fn()
        if (m >= 128).sum() >= 0.08 * area:  # λογικό μέγεθος προϊόντος
            alpha = m
            break
    if alpha is None:
        raise BgRemovalError(
            "Δεν εντοπίστηκε καθαρά το προϊόν στη φωτογραφία. Δοκίμασε "
            "φωτογραφία με μεγαλύτερη αντίθεση από το φόντο, ή συνέχισε "
            "χωρίς αποκοπή (το βήμα διαστάσεων δουλεύει και έτσι)."
        )

    alpha = _feather(alpha)

    ys, xs = np.nonzero(alpha)
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
