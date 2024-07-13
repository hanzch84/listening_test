import streamlit as st
from pathlib import Path
import openai
import os
from dotenv import load_dotenv
from collections import Counter
import re
import random

# CSS 스타일 추가
st.markdown(
    """
    <style>
    h3{font-size: 14px;text-align: right;}
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
    if option == "random":
        if gender == "female":
            return random.choice(['alloy', 'fable', 'nova', 'shimmer'])
        else:
            return random.choice(['echo', 'onyx'])
    elif option == "sequential":
        if gender == "female":
            voices = ['alloy', 'fable', 'nova', 'shimmer']
        else:
            voices = ['echo', 'onyx']
        return voices[idx % len(voices)]
    else:
        return option

def add_silence(tts, duration_ms):
    silence = b'\x00' * (duration_ms * 16000 // 1000)
    tts.extend(silence)

load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    st.error("API key not found. Please set the OPENAI_API_KEY environment variable.")
else:
    openai.api_key = api_key

    st.title("듣기평가 음원 만들기: En Listen")
    st.subheader('교사 박현수, 버그 및 개선 문의: hanzch84@gmail.com')
    col_voice, col_interval = st.columns([9, 2])
    ko_option = col_voice.radio("한국어 음성", ['alloy', 'echo', 'fable', 'nova', 'onyx', 'shimmer'], key="korean_option", index=2, horizontal=True)
    female_voice = col_voice.radio("여성 음성", ['alloy', 'fable', 'nova', 'shimmer', "sequential", "random"], key="female_option", horizontal=True)
    male_voice = col_voice.radio("남성 음성", ['echo', 'onyx', "sequential", "random"], key="male_option", horizontal=True)
    
    interline = col_interval.slider("대사 간격(ms)", value=300, min_value=30, max_value=3000, key="interline")
    internum = col_interval.slider("문제 간격(ms)", value=300, min_value=30, max_value=3000, key="internum")

    if 'female_sequence' not in st.session_state:
        st.session_state.female_sequence = 0
    if 'male_sequence' not in st.session_state:
        st.session_state.male_sequence = 0

    col_btn2, col_btn3 = st.columns([8, 3])
    success_message = st.empty()
    warning_message = st.empty()
    audio_placeholder = col_btn2.empty()
    if 'input_text' not in st.session_state:
        st.session_state.input_text = """1. 다음을 듣고, 남자가 하는 말의 목적으로 가장 적절한 것을 고르시오.
M: Hello, Maplewood High School students. This is your school librarian, Mr. Johnson. I want to remind you that our school library is hosting a book review contest.
#1. testing the app.
#2. tasting the app.
#3. toasting the app.

2번 다음 대화를 듣고, 여자의 의견으로 가장 적절한 것을 고르시오.
M: Sweetie, would you like some oranges for breakfast?
W: Sounds wonderful. Could you keep the orange peels for me?
M: Why? What are you going to do with them?
W: I’m planning to use them to make a natural cleaner. Orange peels are great for cleaning surfaces."""
    st.code("아래 예시문장을 지우고 듣기평가 대본을 넣어 주세요.\n음성지표에 따라 음성이 바뀝니다.(M:남성,W:여성), 예시문 원본 출처:EBS", language="haskell")
    st.session_state.input_text = st.text_area("대본입력 후 CTRL+ENTER", st.session_state.input_text, key="input_area", height=max(st.session_state.input_text.count('\n') * 30+10, 600))

    if col_interval.button("음원 생성", disabled=is_input_exist(st.session_state.input_text)):
        overlay_container = st.empty()
        overlay_container.markdown("""
        <style>
        .overlay {
            position: fixed;top: 0;left: 0;width: 100%;height: 100%;
            background: rgba(0, 0, 0, 0.7);z-index: 999;display: flex;
            justify-content: center;align-items: center;                }
        .spinner {margin-bottom: 10px;}
        </style>
        <div class="overlay"><div><div class="spinner">
                    <span class="fa fa-spinner fa-spin fa-3x"></span>
                </div><div style="color: white;">음원을 출력하는 중...</div></div></div>""", unsafe_allow_html=True)
        try:
            speech_file_path = Path("speech.mp3")
            input_text = st.session_state.input_text
            lines = input_text.split('\n')
            sentences = merge_lines(lines)
            tts = bytearray()
            current_number = None

            for sentence in sentences:
                sentence = sentence.lstrip()
                lang = which_eng_kor(sentence)

                number, sentence = extract_question(sentence)
                if number and number != current_number:
                    current_number = number
                    if female_voice in ["random", "sequential"]:
                        current_voice = get_voice(female_voice, st.session_state.female_sequence, "female")
                        if female_voice == "sequential":
                            st.session_state.female_sequence += 1
                    if male_voice in ["random", "sequential"]:
                        current_voice = get_voice(male_voice, st.session_state.male_sequence, "male")
                        if male_voice == "sequential":
                            st.session_state.male_sequence += 1
                    add_silence(tts, internum)
                else:
                    if re.match(r'W:|W :', sentence):
                        current_voice = get_voice(female_voice, st.session_state.female_sequence, "female")
                    elif re.match(r'M:|M :', sentence):
                        current_voice = get_voice(male_voice, st.session_state.male_sequence, "male")
                    elif lang == 'ko':
                        current_voice = ko_option

                text_to_convert = f"{number[:-1]}번.\n'.....'\n {sentence}" if number else sentence

                if text_to_convert.strip():
                    response = openai.Audio.create(
                        model="text-to-speech",
                        voice=current_voice,
                        text=text_to_convert
                    )

                    tts.extend(response["audio_data"].encode())

                    add_silence(tts, interline)  # Add interline interval

            with open(speech_file_path, 'wb') as audio_file:
                audio_file.write(tts)

            st.session_state.speech_file_path = str(speech_file_path)
            st.session_state.success_message = "Speech conversion successful!"
            st.session_state.en_warning_message = "고지 사항: 이 목소리는 인공지능(AI)으로 생성된 것이며, 실제 사람의 목소리가 아닙니다."

        except Exception as e:
            st.session_state.success_message = f"An error occurred: {e}"
        overlay_container.empty()

    if 'speech_file_path' in st.session_state:
        success_message.success(st.session_state.success_message)
        warning_message.warning(st.session_state.en_warning_message, icon="🚨")
        audio_placeholder.audio(st.session_state.speech_file_path)

        with open(st.session_state.speech_file_path, "rb") as file:
            btn = col_btn3.download_button(
                label="MP3 다운로드",
                data=file,
                file_name="speech.mp3",
                mime="audio/mpeg"
            )
