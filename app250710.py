
import streamlit as st
from pathlib import Path
from openai import OpenAI
import os
from dotenv import load_dotenv
from collections import Counter
import re
import random
from pydub import AudioSegment
from io import BytesIO

# CSS 스타일 추가
st.markdown(
    """
    <style>
        a:link {
            color : #ff4b4b;
        }
        a:visited {
            color : #ffa657;
        }
        a:hover {
            color : red;
        }
        a:active {
            color : green
        }
    h1{font-size: 36px;}
    div.stButton > button,div.stDownloadButton > button {
        height: 54px;
        font-size: 24px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def is_input_exist(text):
    pattern = re.compile(r'[a-zA-Z가-힣]')
    return not bool(pattern.search(text))

def which_eng_kor(input_s):
    count = Counter(input_s)
    k_count = sum(count[c] for c in count if ord('가') <= ord(c) <= ord('힣'))
    e_count = sum(count[c] for c in count if 'a' <= c.lower() <= 'z')
    return "ko" if k_count > e_count else "en"

def extract_question(text):
    match = re.match(r'(\d{1,2}\s*\.?\s*번?)\s*(.*)', text)
    if match:
        number = match.group(1).strip()
        question = match.group(2).strip()
        return number, question
    else:
        return None, text.lstrip()

def merge_lines(lines):
    merged = []
    current_sentence = ""
    for line in lines:
        line = line.strip()
        if line.endswith('.') or line.endswith('?') or line.endswith('!'):
            current_sentence += " " + line
            merged.append(current_sentence.strip())
            current_sentence = ""
        else:
            current_sentence += " " + line
    if current_sentence:
        merged.append(current_sentence.strip())
    return merged

def get_voice(option, idx, gender):
    if option in ["random", "order"]:
        if gender == "female":
            voices = ['alloy', 'fable', 'nova', 'shimmer']
        else:
            voices = ['echo', 'onyx']
        if option == "random":
            selected_voice = random.choice(voices)
            return selected_voice
        else:
            selected_voice = voices[idx % len(voices)]
            return selected_voice
    else:
        return option

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    st.error("API key not found. Please set the OPENAI_API_KEY environment variable.")
else:
    client = OpenAI(api_key=api_key)

    st.title("듣기평가 음원 만들기: En Listen")
    col_speed, col_subheader = st.columns([5, 7])
    speed_rate = col_speed.slider("음성 속도(배)", 0.55, 1.85, 1.0, 0.05)
    col_subheader.markdown('<p style="font-size:10pt; color: #6b6c70;text-align: right;">제작: 교사 박현수</p>', unsafe_allow_html=True)
    col_voice, col_interval = st.columns([10, 3])
    ko_option = col_voice.radio("한국어 음성", ['alloy', 'fable', 'nova', 'shimmer', 'echo', 'onyx'], key="korean_option", index=2, horizontal=True)
    female_voice = col_voice.radio("여성 음성", ['alloy', 'fable', 'nova', 'shimmer', "order", "random"], key="female_option", horizontal=True)
    male_voice = col_voice.radio("남성 음성", ['echo', 'onyx', "order", "random"], key="male_option", horizontal=True)

    interline = 1000 * col_interval.slider("대사 간격(s)", min_value=0.2, max_value=2.0, value=0.7, step=0.1)
    internum = col_interval.slider("문제 간격(s)", min_value=1, max_value=25, value=10)

    interline_silence = AudioSegment.silent(duration=interline)
    internum_silence = AudioSegment.silent(duration=internum * 1000)

    if 'female_sequence' not in st.session_state:
        st.session_state.female_sequence = 0
    if 'male_sequence' not in st.session_state:
        st.session_state.male_sequence = 0

    col_btn2, col_btn3 = st.columns([10, 3])
    success_message = st.empty()
    warning_message = st.empty()
    audio_placeholder = col_btn2.empty()
    if 'input_text' not in st.session_state:
        st.session_state.input_text = "1. 예시 문제입니다.\nM: Hello.\nW: Hi."

    st.session_state.input_text = st.text_area("대본 입력란", st.session_state.input_text, height=400)

    if col_interval.button("🔊 음원 생성하기", disabled=is_input_exist(st.session_state.input_text)):
        try:
            speech_file_path = Path("speech.mp3")
            input_text = st.session_state.input_text
            lines = input_text.split('\n')
            sentences = merge_lines(lines)
            tts = AudioSegment.silent(duration=0)
            current_number = None
            is_first_question = True

            current_female_voice = get_voice(female_voice, st.session_state.female_sequence, "female")
            current_male_voice = get_voice(male_voice, st.session_state.male_sequence, "male")
            current_voice = None

            for sentence in sentences:
                sentence = sentence.lstrip()
                lang = which_eng_kor(sentence)
                number, sentence = extract_question(sentence)

                if number and number != current_number:
                    current_number = number
                    if female_voice in ["random", "order"]:
                        st.session_state.female_sequence += 1
                        current_female_voice = get_voice(female_voice, st.session_state.female_sequence, "female")
                    if male_voice in ["random", "order"]:
                        st.session_state.male_sequence += 1
                        current_male_voice = get_voice(male_voice, st.session_state.male_sequence, "male")
                    if not is_first_question:
                        tts += internum_silence
                    is_first_question = False

                if re.match(r'W:|W :', sentence):
                    current_voice = current_female_voice
                elif re.match(r'M:|M :', sentence):
                    current_voice = current_male_voice
                elif lang == 'ko':
                    current_voice = ko_option
                else:
                    current_voice = current_female_voice

                text_to_convert = f"{number[:-1]}번. {sentence}" if number else sentence

                if text_to_convert.strip():
                    with client.audio.speech.with_streaming_response.create(
                        model="gpt-4o-mini-tts",
                        voice=current_voice,
                        input=text_to_convert,
                        speed=speed_rate,
                        instructions="Speak in a calm, clear, and educational tone."
                    ) as response:
                        audio_bytes = BytesIO()
                        for chunk in response.iter_bytes():
                            audio_bytes.write(chunk)
                    audio_chunk = AudioSegment.from_file(BytesIO(audio_bytes.getvalue()), format="mp3")
                    tts += audio_chunk
                    tts += interline_silence

            tts.export(speech_file_path, format="mp3")
            st.session_state.speech_file_path = str(speech_file_path)
            st.session_state.success_message = "음성 변환이 성공적으로 완료되었습니다!"
            st.session_state.en_warning_message = "해당 음성은 AI로 생성된 음성입니다."

        except Exception as e:
            st.session_state.success_message = f"An error occurred: {e}"

    if 'speech_file_path' in st.session_state:
        success_message.success(st.session_state.success_message)
        warning_message.warning(st.session_state.en_warning_message)
        audio_placeholder.audio(st.session_state.speech_file_path)
        with open(st.session_state.speech_file_path, "rb") as file:
            col_btn3.download_button(
                label="📥 MP3 다운로드",
                data=file,
                file_name="speech.mp3",
                mime="audio/mpeg"
            )
