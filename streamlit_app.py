import streamlit as st
from pathlib import Path
from openai import OpenAI
import os
from dotenv import load_dotenv
from collections import Counter
import re

# CSS 스타일 추가
st.markdown(
    """
    <style>
    div.stButton > button,div.stDownloadButton > button {
        height: 54px;
        font-size: 24px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def is_input_exist(text):
    # 정규 표현식: \S는 공백이 아닌 모든 문자, [a-zA-Z가-힣]는 알파벳과 한글
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
        print(number, question,sep="\n")
        return number, question
    else:
        return None, text.lstrip()

load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    st.error("API key not found. Please set the OPENAI_API_KEY environment variable.")
else:
    client = OpenAI(api_key=api_key)

    st.title("듣기평가 음원 만들기")

    col_kr_voice, col_fe_voice, col_ma_voice, col_interval = st.columns([3, 3, 3, 3])
    ko_option = col_kr_voice.radio("Korean voice.", ['alloy', 'echo', 'fable', 'nova', 'onyx', 'shimmer'], key="korean_option", index=2)
    female_voice = col_fe_voice.radio("Female voice.", ['alloy', 'fable', 'nova', 'shimmer'], key="female_option")
    male_voice = col_ma_voice.radio("Male voice.", ['echo', 'onyx'], key="male_option")
    interline = col_interval.number_input("대사 간 간격(ms)", value=300, min_value=30, max_value=3000, key="interline")
    internum = col_interval.number_input("문제 간 간격(ms)", value=300, min_value=30, max_value=3000, key="internum")

    col_btn1, col_btn2, col_btn3 = st.columns([1.5,8,3])
    st.write = female_voice

    col_lang, col_name, col_line = st.columns([1, 2, 8])


    success_message = st.empty()
    warning_message = st.empty()
    audio_placeholder = col_btn2.empty()
    if 'input_text' not in st.session_state:
        st.session_state.input_text = """1. 다음을 듣고, 남자가 하는 말의 목적으로 가장 적절한 것을 고르시오.
                                M: Hello, Lockwood High School students. This is your school librarian,
                                Mr. Wilkins. I’m sure you’re aware that our school library is hosting a
                                bookmark design competition. I encourage students of all grades to
                                participate in the competition.

                                2번 대화를 듣고, 여자의 의견으로 가장 적절한 것을 고르시오.
                                M: Honey, do you want some apples with breakfast?
                                W: Sounds great. Can you save the apple peels for me?
                                M: Why? What do you want them for?
                                W: I’m going to use them to make a face pack. Apple peels are effective for
                                improving skin condition."""

    st.session_state.input_text = st.text_area("듣기평가 대본을 넣어 주세요. 음성지표에 따라 음성이 바뀝니다.(M:남성,W:여성)", st.session_state.input_text, key="input_area", height=st.session_state.input_text.count('\n') * 24)


    if col_btn1.button("음원\n생성",disabled=is_input_exist(st.session_state.input_text)):
        try:
            speech_file_path = Path("speech.mp3")
            input_text = st.session_state.input_text
            sentences = input_text.split('\n')
            tts = bytearray()

            # 초기 성별 기본값 설정
            current_voice = female_voice

            for sentence in sentences:
                sentence = sentence.lstrip()
                lang = which_eng_kor(sentence)

                if re.match(r'W:|W :', sentence):
                    current_voice = female_voice
                elif re.match(r'M:|M :', sentence):
                    current_voice = male_voice
                elif lang == 'ko':
                    current_voice = ko_option

                number, sentence = extract_question(sentence)
                if number:
                    if number[-1]=="번":
                        text_to_convert = f"{number[:-1]}번\n'.....'\n {sentence}"
                    else:
                        text_to_convert = f"{number}번\n'.....'\n {sentence}"
                    
                else:
                    text_to_convert = sentence

                if text_to_convert.strip():
                    response = client.audio.speech.create(
                        model="tts-1-hd",
                        voice=current_voice,
                        input=text_to_convert
                    )

                    for chunk in response.iter_bytes():
                        tts.extend(chunk)

                    tts.extend(b'\x00' * (st.session_state.interline * 16000 // 1000))  # Add interline interval

            with open(speech_file_path, 'wb') as audio_file:
                audio_file.write(tts)

            st.session_state.speech_file_path = str(speech_file_path)
            st.session_state.success_message = "Speech conversion successful!"
            st.session_state.en_warning_message = "고지 사항: 이 목소리는 인공지능(AI)으로 생성된 것이며, 실제 사람의 목소리가 아닙니다."

        except Exception as e:
            st.session_state.success_message = f"An error occurred: {e}"
    
    if 'speech_file_path' in st.session_state:
        success_message.success(st.session_state.success_message)
        warning_message.warning(st.session_state.en_warning_message,icon="🚨")
        audio_placeholder.audio(st.session_state.speech_file_path)
        
        with open(st.session_state.speech_file_path, "rb") as file:
            btn = col_btn3.download_button(
                label="MP3 다운로드",
                data=file,
                file_name="speech.mp3",
                mime="audio/mpeg"
            )

