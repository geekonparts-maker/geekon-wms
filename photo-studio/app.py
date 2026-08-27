# -*- coding: utf-8 -*-
"""GeekOn Product Photo Studio — Streamlit app.

Ροή: Ανέβασμα φωτό → λευκό φόντο (χωρίς AI, προεπιλογή) ή AI εργαλεία →
διαστάσεις πάνω στο προϊόν (με κλικ στη φωτογραφία ή με presets) →
export έτοιμο για το eshop, με όνομα αρχείου από το SKU.

Εκτέλεση:  streamlit run app.py
"""

import io
import os
import re

import streamlit as st
from PIL import Image, ImageDraw

from annotator import draw_dim_on_image, render_annotated, render_custom_dims
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
ss.setdefault("original", None)    # PIL: όπως ανέβηκε
ss.setdefault("current", None)     # PIL: τρέχουσα (μετά από βήματα επεξεργασίας)
ss.setdefault("history", [])       # στοίβα προηγούμενων εκδόσεων για Undo
ss.setdefault("upload_key", None)  # για ανίχνευση νέου αρχείου
ss.setdefault("final", None)       # PIL: τελική εικόνα με διαστάσεις
ss.setdefault("dims", [])          # μετρήσεις από κλικ: [{x1,y1,x2,y2,label}]
ss.setdefault("pending_pt", None)  # πρώτο κλικ μέτρησης
ss.setdefault("pending_seg", None) # (p1, p2) — περιμένει τιμή
ss.setdefault("last_click", None)  # τελευταίο κλικ του component


def reset_dims():
    ss.dims = []
    ss.pending_pt = None
    ss.pending_seg = None
    ss.last_click = None


def set_current(img: Image.Image):
    ss.history.append(ss.current)
    if len(ss.history) > 10:
        ss.history.pop(0)
    ss.current = img
    ss.final = None
    reset_dims()


def run_ai(prompt: str, spinner: str):
    try:
        with st.spinner(spinner):
            result = edit_image(api_key, model, ss.current, prompt)
        set_current(result)
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
        help="Χρειάζεται μόνο για τα AI εργαλεία. Καλύτερα σε αρχείο .env ως GEMINI_API_KEY.",
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
st.caption("Λευκό φόντο χωρίς αλλοίωση του προϊόντος + ακριβείς διαστάσεις, έτοιμο για το eshop.")

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
        reset_dims()

if ss.original is None:
    st.info("Ανέβασε μια φωτογραφία για να ξεκινήσεις.")
    st.stop()

# ---------------------------------------------------------------- 2. Καθάρισμα
st.header("2️⃣ Λευκό φόντο / καθάρισμα")

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
            set_current(result)
            st.rerun()
        except BgRemovalError as e:
            st.error(f"⚠️ {e}")
with b2:
    if st.button("↩️ Αναίρεση", disabled=not ss.history, width="stretch"):
        ss.current = ss.history.pop()
        ss.final = None
        reset_dims()
        st.rerun()
with b3:
    if st.button("🔄 Επαναφορά αρχικής", width="stretch"):
        ss.current = ss.original
        ss.history = []
        ss.final = None
        reset_dims()
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

# ---------------------------------------------------------------- 3. Διαστάσεις
st.header("3️⃣ Διαστάσεις & τελική εικόνα")

c1, c2, c3 = st.columns(3)
with c1:
    sku = st.text_input("SKU (για το όνομα αρχείου)", placeholder="π.χ. NV156FHM-N48")
with c2:
    title = st.text_input("Τίτλος", placeholder="π.χ. 14.0″ LCD PANEL")
with c3:
    subtitle = st.text_input("Υπότιτλος (προαιρετικό)", placeholder="π.χ. Slim 30-pin eDP • HD")

tab_click, tab_preset = st.tabs(["🖱️ Κλικ στη φωτογραφία", "Πεδία (presets)"])

# --- Λειτουργία «κλικ στη φωτογραφία»: 2 κλικ ορίζουν τη μέτρηση, μετά τιμή ---
with tab_click:
    from streamlit_image_coordinates import streamlit_image_coordinates

    u1, u2 = st.columns([1, 3])
    with u1:
        unit_click = st.selectbox("Μονάδα", ["cm", "mm", "in"], key="unit_click")
    with u2:
        st.caption("**Κάνε 2 κλικ** πάνω στη φωτογραφία — ένα σε κάθε άκρο της μέτρησης "
                   "(π.χ. από την άκρη του κονέκτορα ως την άκρη της οθόνης). "
                   "Μετά γράψε το νούμερο στο πεδίο που ανοίγει. Το βέλος ισιώνει μόνο του.")

    # Preview με τις υπάρχουσες μετρήσεις + σημάδι πρώτου κλικ
    preview = ss.current.copy()
    for d in ss.dims:
        preview = draw_dim_on_image(preview, (d["x1"], d["y1"]), (d["x2"], d["y2"]), d["label"])
    if ss.pending_seg:
        preview = draw_dim_on_image(preview, ss.pending_seg[0], ss.pending_seg[1], "…")
    elif ss.pending_pt:
        pd = ImageDraw.Draw(preview)
        r = max(6, preview.width // 120)
        x, y = ss.pending_pt
        pd.ellipse([x - r, y - r, x + r, y + r], outline=(237, 135, 45), width=max(2, r // 3))

    DISP_W = 760
    click = streamlit_image_coordinates(preview, width=DISP_W, key="clickimg")
    if click is not None and click != ss.last_click:
        ss.last_click = click
        f = ss.current.width / DISP_W
        pt = (click["x"] * f, click["y"] * f)
        if ss.pending_seg is None:
            if ss.pending_pt is None:
                ss.pending_pt = pt
            else:
                ss.pending_seg = (ss.pending_pt, pt)
                ss.pending_pt = None
            st.rerun()

    if ss.pending_seg:
        v1, v2, v3 = st.columns([2, 1, 1])
        with v1:
            val = st.text_input("📏 Τιμή μέτρησης", placeholder="π.χ. 32",
                                key=f"dim_value_{len(ss.dims)}")
        with v2:
            st.write("")
            if st.button("✔ Προσθήκη", type="primary", width="stretch", disabled=not val.strip()):
                label = val.strip()
                if not re.search(r"[A-Za-zΑ-Ωα-ω\"″]", label):
                    label = f"{label} {unit_click}"
                (p1, p2) = ss.pending_seg
                ss.dims.append({"x1": p1[0], "y1": p1[1], "x2": p2[0], "y2": p2[1], "label": label})
                ss.pending_seg = None
                st.rerun()
        with v3:
            st.write("")
            if st.button("✖ Άκυρο", width="stretch"):
                ss.pending_seg = None
                ss.pending_pt = None
                st.rerun()

    if ss.dims:
        st.write("**Μετρήσεις:**")
        for i, d in enumerate(ss.dims):
            r1, r2 = st.columns([5, 1])
            ori = "οριζόντια" if abs(d["x2"] - d["x1"]) >= abs(d["y2"] - d["y1"]) else "κατακόρυφη"
            r1.write(f"• {d['label']} ({ori})")
            if r2.button("🗑", key=f"del{i}"):
                ss.dims.pop(i)
                st.rerun()

    footer_click = st.text_input("Footer (προαιρετικό)", key="footer_click")
    if st.button("🎯 Δημιουργία τελικής εικόνας", type="primary",
                 key="gen_click", disabled=not ss.dims):
        logo = Image.open(LOGO_PATH) if (use_logo and os.path.exists(LOGO_PATH)) else None
        ss.final = render_custom_dims(
            ss.current, ss.dims,
            title=title.strip(), subtitle=subtitle.strip(),
            footer=footer_click.strip(), canvas=canvas_size, logo=logo,
        )

# --- Λειτουργία presets (πεδία) ---
with tab_preset:
    PRESETS = {
        "Panel / Οθόνη (εξωτερικές + Active Area)": {"outer": True, "active": True, "depth": True},
        "Απλό (Πλάτος × Ύψος)": {"outer": True, "active": False, "depth": False},
        "Μ × Π × Υ (π.χ. μπαταρία)": {"outer": True, "active": False, "depth": True},
    }
    preset_name = st.radio("Preset", list(PRESETS), horizontal=True)
    preset = PRESETS[preset_name]

    p1c, p2c, p3c = st.columns(3)
    with p1c:
        unit = st.selectbox("Μονάδα", ["CM", "MM", "IN"])
        outer_w = st.text_input("Πλάτος (εξωτερικό)", placeholder="π.χ. 35.1") if preset["outer"] else ""
        outer_h = st.text_input("Ύψος (εξωτερικό)", placeholder="π.χ. 21.6") if preset["outer"] else ""
    with p2c:
        active_w = st.text_input("Active Area — πλάτος", placeholder="π.χ. 34.4") if preset["active"] else ""
        active_h = st.text_input("Active Area — ύψος", placeholder="π.χ. 19.4") if preset["active"] else ""
        depth = st.text_input("Πάχος / Βάθος (προαιρετικό)", placeholder="π.χ. 3.2 mm") if preset["depth"] else ""
    with p3c:
        footer = st.text_input("Footer (κενό = αυτόματο από Active Area)")

    with st.expander("🔧 Προχωρημένα"):
        show_bottom = st.checkbox("Και κάτω βέλος πλάτους (όπως στο δείγμα)", value=False)
        inset_pct = st.slider("Εσοχή πλαισίου Active Area (% του προϊόντος)", 2, 20, 7) / 100.0

    def with_unit(value: str) -> str:
        v = value.strip()
        if v and not re.search(r"[A-Za-zΑ-Ωα-ω]", v):
            return f"{v} {unit}"
        return v

    if st.button("🎯 Δημιουργία τελικής εικόνας", type="primary", key="gen_preset"):
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

# ---------------------------------------------------------------- Τελική εικόνα
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
