import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import random
import speech_recognition as sr
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
import tempfile

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Session state
for key in ["user_name", "latest_input", "poem_history", "image_history"]:
    if key not in st.session_state:
        st.session_state[key] = [] if "history" in key else "Guest"

# UI Styling
st.markdown("""
<style>
.stApp {
    background: linear-gradient(45deg, #2b1d5e, #4a3b8c, #6b5b95, #8878c3, #2b1d5e);
    background-size: 200% 200%;
    animation: gradientFlow 10s ease infinite;
    min-height: 100vh;
    color: white;
}
@keyframes gradientFlow {
    0% { background-position: 0% 0%; }
    50% { background-position: 100% 100%; }
    100% { background-position: 0% 0%; }
}
[data-testid="stSidebar"] {
    background: linear-gradient(135deg, #1e1a3f, #3c2f70);
    color: white;
    padding: 15px;
}
[data-testid="stSidebar"]::before {
    content: '✨✏️📝🎨✨';
    display: block;
    text-align: center;
    font-size: 25px;
    margin-bottom: 15px;
}
.dev-footer {
    text-align: center;
    color: #d4c4ff;
    font-size: 14px;
    font-family: 'Georgia', serif;
    padding: 15px 0;
    margin-top: 20px;
    border-top: 1px solid rgba(255, 255, 255, 0.2);
    background: linear-gradient(90deg, rgba(40, 30, 80, 0.3), rgba(80, 60, 120, 0.3));
    border-radius: 10px;
    width: 80%;
    margin-left: auto;
    margin-right: auto;
    letter-spacing: 0.8px;
}
.dev-footer span {
    color: #ffb3ff;
    font-weight: 600;
    text-shadow: 0 0 5px rgba(255, 179, 255, 0.5);
}
</style>
""", unsafe_allow_html=True)

# Sidebar Inputs
with st.sidebar:
    st.title("✨ **Poetry Craft**")
    st.session_state.user_name = st.text_input("👤 Your Name", value=st.session_state.user_name)

    styles = ["Shakespearean", "Modern", "Haiku", "Romantic", "Free Verse", "Gothic", "Fantasy"]
    moods = ["Happy", "Sad", "Inspirational", "Dark", "Dreamy"]
    languages = ["English", "French", "Spanish", "German", "Hindi"]
    tones = ["Soft", "Bold", "Whimsical"]
    lengths = ["Short", "Medium", "Long"]
    themes = ["Nature", "Love", "Time", "Mystery", "Fantasy", "Loss", "Hope"]

    poetry_style = st.selectbox("📜 Style", styles)
    mood = st.selectbox("🎭 Mood", moods)
    language = st.selectbox("🌍 Language", languages)
    tone = st.selectbox("🎙️ Tone", tones)
    length = st.selectbox("📏 Length", lengths)
    theme = st.selectbox("🌟 Theme", themes)

    if st.button("🎲 Surprise Me!"):
        poetry_style = random.choice(styles)
        mood = random.choice(moods)
        language = random.choice(languages)
        tone = random.choice(tones)
        length = random.choice(lengths)
        theme = random.choice(themes)
        st.success(f"Surprise settings: {poetry_style}, {mood}, {language}, {tone}, {length}, {theme}")

    if st.button("🗑️ Clear Chat"):
        st.session_state.poem_history = []
        st.session_state.image_history = []
        st.session_state.latest_input = ""
        st.success("Chat cleared!")

# Voice Input
def listen_to_user():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙️ Listening... Speak your inspiration!")
        try:
            audio = recognizer.listen(source, timeout=5)
            return recognizer.recognize_google(audio)
        except:
            return None

# Relevance Checker
def is_poetry_related(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Is this poetic? Yes or No only.\n\n{prompt}")
        return "yes" in response.text.lower()
    except:
        return True

# Poem Generator
def get_poetic_response(user_input, style, mood, language, tone, length, theme):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Write a {length} {style} poem in {language} with a {mood} mood, {tone} tone, and {theme} theme:\n\n{user_input}"
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        return f"⚠️ Error: {e}"

# Fallback Image
def generate_fallback_image(poem_text):
    width, height = 800, 600
    image = Image.new("RGB", (width, height), color="#c9d6ff")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 24)  # Use a system font if available
    except:
        font = ImageFont.load_default()  # Fallback to default font
    snippet = poem_text[:200]
    draw.rectangle([50, 50, 750, 550], fill="#ffffffcc", outline="#222222", width=2)
    draw.text((60, 100), snippet, fill="black", font=font)
    path = "fallback_image.png"
    image.save(path)
    return path

# PDF Generator
def generate_pdf(poem_text, image_path):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    content = [
        Paragraph("<b>Your Poem</b>", styles['Title']),
        Spacer(1, 12),
        Paragraph(poem_text.replace('\n', '<br/>'), styles['Normal']),
        Spacer(1, 24),
        Paragraph("<b>Poem Illustration</b>", styles['Heading2']),
        Spacer(1, 12),
        ReportLabImage(image_path, width=400, height=300)
    ]
    doc.build(content)
    return buffer.getvalue()

# Text-to-Speech
def speak_poem(poem_text):
    try:
        tts = gTTS(poem_text)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            st.audio(fp.name)
    except Exception as e:
        st.warning(f"TTS Error: {e}")

# UI Layout
st.title("📜 **Poetry Weaver**")
st.subheader(f"🌙 Greetings, {st.session_state.user_name}!")

col1, col2 = st.columns([3, 1])
with col1:
    user_input = st.text_input("💭 Share your muse:", value=st.session_state.latest_input)
with col2:
    if st.button("🎙️ Speak"):
        result = listen_to_user()
        if result:
            user_input = result
            st.session_state.latest_input = result

# Generation
if st.button("🚀 Weave Poem"):
    if user_input:
        st.session_state.latest_input = user_input
        if not is_poetry_related(user_input):
            st.warning("Try something more poetic!")
        else:
            poem = get_poetic_response(user_input, poetry_style, mood, language, tone, length, theme)
            st.markdown(f"**🤖 Weaver:**\n\n{poem}")
            st.session_state.poem_history.append(poem)

            speak_poem(poem)

            img_path = generate_fallback_image(poem)  # Use fallback image directly
            if img_path:
                st.image(img_path, caption="🖼️ Poem Artwork")
                with open(img_path, "rb") as f:
                    st.download_button("⬇️ Download Image", data=f, file_name="Poem_Image.png", mime="image/png")
                st.session_state.image_history.append(img_path)

            pdf_bytes = generate_pdf(poem, img_path)
            st.download_button("📄 Download Poem + Image PDF", data=pdf_bytes, file_name="Poem_With_Image.pdf", mime="application/pdf")
    else:
        st.warning("Please enter something!")

# Image Gallery
if st.session_state.image_history:
    st.markdown("### 🎨 Image Gallery")
    for i, path in enumerate(st.session_state.image_history):
        with st.expander(f"Artwork {i+1}"):
            st.image(path)
            with open(path, "rb") as img_file:
                st.download_button(f"Download Artwork {i+1}", data=img_file, file_name=f"Artwork_{i+1}.png", mime="image/png")

# Footer
st.markdown("""
<div class="dev-footer">
    Crafted by <span>Akshita</span> © 2024
</div>
""", unsafe_allow_html=True)