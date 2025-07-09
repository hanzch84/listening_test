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
            print(f"Randomly selected {gender} voice: {selected_voice}")
            return selected_voice
        else:
            selected_voice = voices[idx % len(voices)]
            print(f"Sequentially selected {gender} voice: {selected_voice}")
            return selected_voice
    else:
        print(f"Selected {gender} voice: {option}")
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
    col_subheader.markdown('<p style="font-size:10pt; color: #6b6c70;text-align: right;">제작: 교사 박현수, 버그 및 개선 문의: <a href="mailto:hanzch84@gmail.com">hanzch84@gmail.com</a></p>', unsafe_allow_html=True)
    col_subheader.markdown('<p style="font-size:14pt; color: #6b6c70;text-align: right;"><a href="https://platform.openai.com/docs/guides/text-to-speech/voice-options">음성 옵션 미리듣기(openai TTS api overview page)</a></p>', unsafe_allow_html=True)
    col_voice, col_interval = st.columns([10, 3])
    ko_option = col_voice.radio("한국어 음성", ['alloy', 'fable', 'nova', 'shimmer', 'echo', 'onyx'], key="korean_option", index=2, horizontal=True, help="한국어 음성을 선택하세요.")
    female_voice = col_voice.radio("여성 음성", ['alloy', 'fable', 'nova', 'shimmer', "order", "random"], key="female_option", horizontal=True, help="여성 음성을 선택하세요. random은 문제마다 무작위의 음성을 선택합니다. sequential은 문제마다 음성을 차례로 바꿔 줍니다.")
    male_voice = col_voice.radio("남성 음성", ['echo', 'onyx', "order", "random"], key="male_option", horizontal=True, help="남성 음성을 선택하세요. random은 문제마다 무작위의 음성을 선택합니다. sequential은 문제마다 음성을 차례로 바꿔 줍니다.")

    print(f"Selected Korean voice: {ko_option}")
    print(f"Selected female voice: {female_voice}")
    print(f"Selected male voice: {male_voice}")

    interline = 1000*col_interval.slider("대사 간격(s)", min_value=0.2, max_value=2.0, value=0.7, step=0.1, key="interline", disabled=False, help="문장 사이의 무음 구간 길이")
    internum = col_interval.slider("문제 간격(s)", min_value=1, max_value=25, value=10, key="internum", disabled=False, help="문제와 문제 사이의 무음 구간 길이")

    # 무음을 미리 생성
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
        st.session_state.input_text = """1. 다음을 듣고, 남자가 하는 말의 목적으로 가장 적절한 것을 고르시오.
M: Hello, Maplewood High School students.
This is your school librarian, Mr. Johnson. 

W: Number One.
    testing and tasting the app.

W: Number Three.
    toasting and twisting the app.

W: Number Five.
    tossing and trusting the app.


2번 다음 대화를 듣고, 여자의 의견으로 가장 적절한 것을 고르시오.
M: Hi, Sweetie.
W: Could you keep the orange peels for me?
M: Why? What are you going to do with them?
W: I’m planning to use them to make a natural cleaner."""

    st.code("""'대본 입력란'의 예시를 지우고 듣기평가 대본을 입력하세요.
앞에 숫자와 '번'또는 '.'을 쓰면 문제번호를 인식합니다.
앞에 음성지표(M:남성,W:여성)를 넣으면 해당 성별 음성으로 바뀝니다.
'random'은 문제마다 해당 성별의 음성을 무작위로 선택합니다.
'order'는 문제마다 해당 성별의 음성을 순서대로 바꿔 줍니다.
문장, 문제 간격을 조절할 수 있습니다. (각색된 예시 대본 원본 출처:EBS)""", language="haskell")
    st.session_state.input_text = st.text_area("대본 입력란", st.session_state.input_text, key="input_area", height=max(st.session_state.input_text.count('\n') * 26 + 10, 400))

    if col_interval.button("🔊 음원 생성하기", disabled=is_input_exist(st.session_state.input_text),):
        print("Generating audio...")

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
            tts = AudioSegment.silent(duration=0)  # 초기 음성
            current_number = None
            is_first_question = True  # 첫 문제 여부 확인 변수 추가

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

                    if not is_first_question:  # 첫 문제 앞에는 무음을 추가하지 않음
                        tts += internum_silence  # 문제 간 무음 추가
                    is_first_question = False

                if re.match(r'W:|W :', sentence):
                    current_voice = current_female_voice
                elif re.match(r'M:|M :', sentence):
                    current_voice = current_male_voice
                elif lang == 'ko':
                    current_voice = ko_option
                else:
                    if not current_voice:
                        current_voice = current_male_voice if current_number and current_number[-1] == '.' else current_female_voice

                text_to_convert = f"{number[:-1]}번.\n'.....'\n {sentence}" if number else sentence

                if text_to_convert.strip():
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice=current_voice,
                        input=text_to_convert,
                        speed=speed_rate
                    )

                    # response.iter_bytes()를 통해 생성된 바이트 데이터를 읽어옵니다.
                    audio_bytes = BytesIO(b"".join(response.iter_bytes()))
                    audio_chunk = AudioSegment.from_file(audio_bytes, format="mp3")
                    tts += audio_chunk

                    tts += interline_silence  # 문장 간 무음 추가

            tts.export(speech_file_path, format="mp3")
            st.session_state.speech_file_path = str(speech_file_path)
            st.session_state.success_message = "음성 변환이 성공적으로 완료되었습니다!"
            st.session_state.en_warning_message = "고지 사항: 이 목소리는 인공지능(AI)으로 생성된 것이며, 실제 사람의 목소리가 아닙니다."
            print("Audio file saved successfully.")

        except Exception as e:
            st.session_state.success_message = f"An error occurred: {e}"
            print(f"An error occurred: {e}")
        overlay_container.empty()
        st.balloons()

    if 'speech_file_path' in st.session_state:
        success_message.success(st.session_state.success_message)
        warning_message.warning(st.session_state.en_warning_message, icon="🚨")
        audio_placeholder.audio(st.session_state.speech_file_path)

        with open(st.session_state.speech_file_path, "rb") as file:
            btn = col_btn3.download_button(
                label="📥 MP3 다운로드",
                data=file,
                file_name="speech.mp3",
                mime="audio/mpeg"
            )
