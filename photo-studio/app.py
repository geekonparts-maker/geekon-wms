# -*- coding: utf-8 -*-
"""GeekOn Product Photo Studio — Streamlit app.

Ροή: Ανέβασμα φωτό → (προαιρετικά) καθάρισμα/λευκό φόντο με Nano Banana +
ελεύθερες εντολές → διαστάσεις πάνω στο προϊόν (προγραμματιστικά, πάντα
ακριβείς) → export έτοιμο για το eshop, με όνομα αρχείου από το SKU.

Εκτέλεση:  streamlit run app.py
"""

import io
import os
import re

import streamlit as st
from PIL import Image

from annotator import render_annotated
from bg_removal import BgRemovalError, remove_background_local
from gemini_client import CLEANUP_PROMPT, DEFAULT_MODEL, MODELS, GeminiError, edit_image

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(APP_DIR, "..", "assets", "geekon-logo-on-light.png")

st.set_page_config(page_title="GeekOn Product Photo Studio", page_icon="📐", layout="wide")

# ---------------------------------------------------------------- session state
ss = st.session_state
ss.setdefault("original", None)   # PIL: όπως ανέβηκε
ss.setdefault("current", None)    # PIL: τρέχουσα (μετά από AI βήματα)
ss.setdefault("history", [])      # στοίβα προηγούμενων εκδόσεων για Undo
ss.setdefault("upload_key", None) # για ανίχνευση νέου αρχείου
ss.setdefault("final", None)      # PIL: τελική εικόνα με διαστάσεις


def push_history(img: Image.Image):
    ss.history.append(img)
    if len(ss.history) > 10:
        ss.history.pop(0)


def run_ai(prompt: str, spinner: str):
    try:
        with st.spinner(spinner):
            result = edit_image(api_key, model, ss.current, prompt)
        push_history(ss.current)
        ss.current = result
        ss.final = None
        st.rerun()
    except GeminiError as e:
        st.error(f"⚠️ {e}")


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("⚙️ Ρυθμίσεις")
    api_key = st.text_input(
        "Gemini API key",
        value=os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", "")),
        type="password",
        help="Από το Google AI Studio. Καλύτερα βάλε το σε αρχείο .env ως GEMINI_API_KEY.",
    )
    model = st.selectbox("Μοντέλο εικόνας", MODELS, index=MODELS.index(DEFAULT_MODEL),
                         help="Nano Banana = gemini-2.5-flash-image (~$0.04/εικόνα).")
    canvas_size = st.select_slider("Μέγεθος τελικής εικόνας (px)",
                                   options=[1000, 1200, 1500, 2000], value=1500)
    jpeg_quality = st.slider("Ποιότητα JPEG", 70, 100, 92)
    use_logo = st.checkbox("Λογότυπο GeekOn στη γωνία",
                           value=os.path.exists(LOGO_PATH),
                           disabled=not os.path.exists(LOGO_PATH))

st.title("📐 GeekOn Product Photo Studio")
st.caption("Καθάρισμα φωτογραφίας με AI (Nano Banana) + ακριβείς διαστάσεις πάνω στο προϊόν, έτοιμο για το eshop.")

# ---------------------------------------------------------------- 1. Upload
st.header("1️⃣ Φωτογραφία προϊόντος")
uploaded = st.file_uploader("Ανέβασε φωτογραφία (JPG/PNG/WebP)", type=["jpg", "jpeg", "png", "webp"])

if uploaded is not None:
    key = (uploaded.name, uploaded.size)
    if key != ss.upload_key:
        ss.upload_key = key
        ss.original = Image.open(io.BytesIO(uploaded.read())).convert("RGB")
        ss.current = ss.original
        ss.history = []
        ss.final = None

if ss.original is None:
    st.info("Ανέβασε μια φωτογραφία για να ξεκινήσεις.")
    st.stop()

# ---------------------------------------------------------------- 2. AI editing
st.header("2️⃣ Επεξεργασία με AI (προαιρετικά)")

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Αρχική")
    st.image(ss.original, width="stretch")
with col_b:
    st.subheader("Τρέχουσα")
    st.image(ss.current, width="stretch")

b1, b2, b3 = st.columns([2, 1, 1])
with b1:
    if st.button("✂️ Λευκό φόντο ΧΩΡΙΣ AI — δεν πειράζει το προϊόν",
                 type="primary", width="stretch"):
        try:
            with st.spinner("Τοπική αποκοπή φόντου… (την 1η φορά κατεβαίνει το μοντέλο ~176MB)"):
                result = remove_background_local(ss.current)
            push_history(ss.current)
            ss.current = result
            ss.final = None
            st.rerun()
        except BgRemovalError as e:
            st.error(f"⚠️ {e}")
with b2:
    if st.button("↩️ Αναίρεση", disabled=not ss.history, width="stretch"):
        ss.current = ss.history.pop()
        ss.final = None
        st.rerun()
with b3:
    if st.button("🔄 Επαναφορά αρχικής", width="stretch"):
        ss.current = ss.original
        ss.history = []
        ss.final = None
        st.rerun()

st.caption("✅ Η τοπική αποκοπή αφαιρεί μόνο το φόντο — τα pixels του προϊόντος μένουν ακριβώς όπως στη φωτογραφία σου. Το βήμα των διαστάσεων επίσης δεν αγγίζει ποτέ το προϊόν.")

with st.expander("🤖 AI εργαλεία (Nano Banana) — μόνο για δύσκολες περιπτώσεις"):
    st.warning(
        "Το γενετικό AI **ξαναδημιουργεί ολόκληρη την εικόνα** — μικρολεπτομέρειες "
        "του προϊόντος (γράμματα ετικέτας, pins, βίδες) μπορεί να αλλοιωθούν. "
        "Χρησιμοποίησέ το μόνο όταν χρειάζεται (π.χ. υδατογράφημα) και έλεγξε "
        "προσεκτικά το αποτέλεσμα στη σύγκριση Αρχική/Τρέχουσα."
    )
    cleanup_prompt = st.text_area("Οδηγία καθαρίσματος", value=CLEANUP_PROMPT, height=140)
    if st.button("🧽 Λευκό φόντο & καθάρισμα (AI)"):
        run_ai(cleanup_prompt, "Επεξεργασία με Nano Banana…")

    extra = st.text_input("💬 Extra εντολή προς το AI (π.χ. «αφαίρεσε το καλώδιο», «σβήσε το υδατογράφημα»)")
    if st.button("Εφαρμογή εντολής", disabled=not extra.strip()):
        run_ai(
            extra.strip() + " Do not alter the product itself in any other way; "
            "keep its exact shape, proportions, colors and labels unchanged.",
            "Εφαρμογή εντολής…",
        )
    st.caption("⚖️ Αφαίρεση υδατογραφήματος μόνο σε φωτογραφίες που έχεις δικαίωμα χρήσης (δικές σου ή από προμηθευτή με άδεια).")

# ---------------------------------------------------------------- 3. Dimensions
st.header("3️⃣ Διαστάσεις & τελική εικόνα")

PRESETS = {
    "Panel / Οθόνη (εξωτερικές + Active Area)": {"outer": True, "active": True, "depth": True},
    "Απλό (Πλάτος × Ύψος)": {"outer": True, "active": False, "depth": False},
    "Μ × Π × Υ (π.χ. μπαταρία)": {"outer": True, "active": False, "depth": True},
}
preset_name = st.radio("Preset", list(PRESETS), horizontal=True)
preset = PRESETS[preset_name]

c1, c2, c3 = st.columns(3)
with c1:
    sku = st.text_input("SKU (για το όνομα αρχείου)", placeholder="π.χ. NV156FHM-N48")
    title = st.text_input("Τίτλος", placeholder="π.χ. 15.6″ LCD PANEL")
    subtitle = st.text_input("Υπότιτλος (προαιρετικό)", placeholder="π.χ. Slim 30-pin eDP • FHD")
with c2:
    unit = st.selectbox("Μονάδα", ["CM", "MM", "IN"])
    outer_w = st.text_input("Πλάτος (εξωτερικό)", placeholder="π.χ. 35.1") if preset["outer"] else ""
    outer_h = st.text_input("Ύψος (εξωτερικό)", placeholder="π.χ. 21.6") if preset["outer"] else ""
    depth = st.text_input("Πάχος / Βάθος (προαιρετικό)", placeholder="π.χ. 3.2 mm") if preset["depth"] else ""
with c3:
    active_w = st.text_input("Active Area — πλάτος", placeholder="π.χ. 34.4") if preset["active"] else ""
    active_h = st.text_input("Active Area — ύψος", placeholder="π.χ. 19.4") if preset["active"] else ""
    footer = st.text_input("Footer (κενό = αυτόματο από Active Area)")

with st.expander("🔧 Προχωρημένα"):
    show_bottom = st.checkbox("Και κάτω βέλος πλάτους (όπως στο δείγμα)", value=False)
    inset_pct = st.slider("Εσοχή πλαισίου Active Area (% του προϊόντος)", 2, 20, 7) / 100.0


def with_unit(value: str) -> str:
    v = value.strip()
    if v and not re.search(r"[A-Za-zΑ-Ωα-ω]", v):
        return f"{v} {unit}"
    return v


if st.button("🎯 Δημιουργία τελικής εικόνας", type="primary"):
    logo = Image.open(LOGO_PATH) if (use_logo and os.path.exists(LOGO_PATH)) else None
    ss.final = render_annotated(
        ss.current,
        title=title.strip(),
        subtitle=subtitle.strip(),
        outer_w=with_unit(outer_w),
        outer_h=with_unit(outer_h),
        active_w=with_unit(active_w),
        active_h=with_unit(active_h),
        footer=footer.strip(),
        depth_chip=(f"Πάχος: {with_unit(depth)}" if depth.strip() and "άχος" not in depth else depth.strip()),
        show_bottom=show_bottom,
        canvas=canvas_size,
        inset_pct=inset_pct,
        logo=logo,
    )

if ss.final is not None:
    st.image(ss.final, caption="Τελική εικόνα", width="stretch")

    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", sku.strip()) or "product"
    buf_jpg, buf_png = io.BytesIO(), io.BytesIO()
    ss.final.save(buf_jpg, format="JPEG", quality=jpeg_quality)
    ss.final.save(buf_png, format="PNG")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button("⬇️ Λήψη JPEG", data=buf_jpg.getvalue(),
                           file_name=f"{stem}_dimensions.jpg", mime="image/jpeg",
                           width="stretch")
    with d2:
        st.download_button("⬇️ Λήψη PNG", data=buf_png.getvalue(),
                           file_name=f"{stem}_dimensions.png", mime="image/png",
                           width="stretch")
