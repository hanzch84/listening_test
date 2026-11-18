import base64
import re
from collections import Counter
from io import BytesIO

import streamlit as st
from google import genai
from google.genai import types
from pydub import AudioSegment


MODEL = "gemini-3.8-flash-tts"
VOICES = [
    "Achernar", "Achird", "Algenib", "Algieba", "Alnilam", "Aoede",
    "Autonoe", "Callirrhoe", "Charon", "Despina", "Enceladus", "Erinome",
    "Fenrir", "Gacrux", "Iapetus", "Kore", "Laomedeia", "Leda",
    "Orus", "Pulcherrima", "Puck", "Rasalgethi", "Sadachbia",
    "Schedar", "Sulafat", "Umbriel", "Vindemiatrix", "Zephyr",
]


def is_input_empty(text):
    return not re.search(r"[a-zA-Z가-힣]", text)


def which_language(text):
    counts = Counter(text)
    korean = sum(counts[c] for c in counts if "가" <= c <= "힣")
    english = sum(counts[c] for c in counts if "a" <= c.lower() <= "z")
    return "ko" if korean > english else "en"


def split_sentences(text):
    result = []
    current = ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        current = f"{current} {line}".strip()
        if re.search(r"[.!?][\"')\]]?$", line):
            result.append(current)
            current = ""
    if current:
        result.append(current)
    return result


def extract_question(text):
    match = re.match(r"^\s*(\d+)\s*\.?\s*번?\s*(.*)", text)
    return (match.group(1), match.group(2).strip()) if match else (None, text.strip())


def extract_speaker(text):
    match = re.match(r"^\s*([MW])\s*:\s*(.*)", text, re.IGNORECASE)
    if not match:
        return None, text
    return ("male" if match.group(1).upper() == "M" else "female"), match.group(2).strip()


def extract_style(text):
    match = re.match(r"^\s*\[([^\]]+)\]\s*(.*)", text)
    return (match.group(1).strip(), match.group(2).strip()) if match else (None, text.strip())


def number_to_korean(value):
    digits = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
    units = ["", "십", "백", "천"]
    result = ""
    for i, char in enumerate(value):
        digit = int(char)
        unit = units[len(value) - i - 1]
        if digit:
            result += (unit if digit == 1 and unit else digits[digit] + unit)
    return result or "영"


def generate_wav(client, text, voice, style):
    annotation = []
    if style:
        annotation.append({"type": "speech_metadata", "style": style})
    content = {"type": "text", "text": text}
    if annotation:
        content["annotations"] = annotation
    interaction = client.interactions.create(
        model=MODEL,
        input=[{"type": "user_input", "content": [content]}],
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"voice": voice}]},
    )
    audio = interaction.output_audio.data
    return base64.b64decode(audio) if isinstance(audio, str) else audio


st.set_page_config(page_title="En Listen · Gemini 테스트", page_icon="🔊")
st.title("듣기평가 음원 만들기: En Listen")
st.caption("Gemini 3.8 Flash TTS 테스트 버전 · 기존 OpenAI 앱과 분리된 브랜치")

api_key = st.text_input(
    "Gemini API 키",
    type="password",
    help="Google AI Studio에서 발급한 Gemini API 키를 입력하세요. 입력한 키는 이 세션에서만 사용하며 앱에 저장하지 않습니다.",
)
st.caption("Gemini API 사용량은 입력한 키의 Google 프로젝트에 청구됩니다. 테스트 대본으로 먼저 확인하세요.")

col1, col2 = st.columns(2)
voice_default = VOICES.index("Kore")
voice_male = col1.selectbox("남성/기본 음성", VOICES, index=VOICES.index("Puck"))
voice_female = col2.selectbox("여성 음성", VOICES, index=voice_default)

col3, col4 = st.columns(2)
interline_ms = int(col3.slider("대사 간격 (초)", 0.2, 2.0, 0.7, 0.1) * 1000)
between_questions_s = col4.slider("문제 간격 (초)", 1, 25, 10)

st.markdown(
    """대본의 각 줄 앞에 `M:` 또는 `W:`를 붙이면 화자를 바꿉니다.
문장 첫머리의 `[차분하고 또렷한 말투]`처럼 대괄호에 스타일을 적으면
해당 문장에만 적용합니다. 문제 번호는 `13.` 또는 `13번` 형식을 인식합니다."""
)
example = """13. 다음을 듣고, 남자가 하는 말의 목적으로 가장 적절한 것을 고르시오.
M: Hello, Maplewood High School students.
This is your school librarian, Mr. Johnson.

W: Number One.
[밝고 신나는 목소리로]Testing and tasting the app.
W: Number Three.
[화가 난 말투로]Toasting and twisting the app.

29번 다음 대화를 듣고, 여자의 의견으로 가장 적절한 것을 고르시오.
M: Hi, Sweetie.
W: Could you keep the orange peels for me?
M: Why? What are you going to do with them?
W: I’m planning to use them to make a natural cleaner."""
script = st.text_area("대본 입력란", example, height=360)

if st.button("🔊 Gemini 음원 생성하기", type="primary", disabled=not api_key or is_input_empty(script)):
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version="v1beta"),
        )
        assembled = AudioSegment.silent(duration=0)
        previous_question = None
        first_question = True
        current_voice = voice_default

        with st.spinner("Gemini가 음원을 생성하고 있습니다..."):
            for raw_sentence in split_sentences(script):
                sentence = raw_sentence.strip()
                style, sentence = extract_style(sentence)
                speaker, sentence = extract_speaker(sentence)
                question, sentence = extract_question(sentence)
                lang = which_language(sentence)

                if question and question != previous_question:
                    if not first_question:
                        assembled += AudioSegment.silent(duration=between_questions_s * 1000)
                    first_question = False
                    previous_question = question
                    prefix = f"{number_to_korean(question)}번 문제입니다. "
                    sentence = prefix + sentence

                if speaker == "male":
                    current_voice = voice_male
                elif speaker == "female":
                    current_voice = voice_female
                elif lang == "ko" and previous_question is None:
                    current_voice = voice_default

                style_parts = [style] if style else []
                style_parts.append("Speak clearly and naturally at a steady pace.")
                wav = generate_wav(client, sentence, current_voice, "; ".join(style_parts))
                assembled += AudioSegment.from_file(BytesIO(wav), format="wav")
                assembled += AudioSegment.silent(duration=interline_ms)

        output = BytesIO()
        assembled.export(output, format="mp3")
        st.session_state["gemini_audio"] = output.getvalue()
        st.session_state["gemini_audio_name"] = "en_listen_gemini_test.mp3"
        st.success("음원 생성이 완료되었습니다.")
        st.audio(st.session_state["gemini_audio"], format="audio/mpeg")
        st.download_button(
            "📥 MP3 다운로드",
            data=st.session_state["gemini_audio"],
            file_name=st.session_state["gemini_audio_name"],
            mime="audio/mpeg",
        )
    except Exception as exc:
        st.error(f"생성 실패: {type(exc).__name__}")
        st.info("Gemini API 키, 프로젝트의 API 사용 설정/한도, 모델 접근 권한을 확인하세요. 오류 문구에 키가 포함될 수 있어 상세 응답은 화면에 표시하지 않습니다.")
elif "gemini_audio" in st.session_state:
    st.audio(st.session_state["gemini_audio"], format="audio/mpeg")
    st.download_button(
        "📥 MP3 다운로드",
        data=st.session_state["gemini_audio"],
        file_name=st.session_state["gemini_audio_name"],
        mime="audio/mpeg",
    )
