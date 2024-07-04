import streamlit as st
from pathlib import Path
from openai import OpenAI
import os
from dotenv import load_dotenv  # 이 줄을 추가


# .env 파일 로드
load_dotenv()

# 환경 변수에서 OpenAI API 키 가져오기
api_key = os.getenv('OPENAI_API_KEY')

# OpenAI API 키 설정
if not api_key:
    st.error("API key not found. Please set the OPENAI_API_KEY environment variable.")
else:
    client = OpenAI(api_key=api_key)

    # Streamlit 인터페이스 설정
    st.title("Text-to-Speech with OpenAI")

    # 입력 텍스트 박스

    text_input = st.text_area("Enter the text you want to convert to speech", "Today is a wonderful day to build something people love!")
    col_kvoice, col_voice, col_interval, col_buttons = st.columns([3,3,3,3])
    ko_option = col_kvoice.radio("Select a korean voice.", sorted(["nova", "shimmer", "echo", "onyx", "fable", "alloy"]))
    option = col_voice.radio("Select a basic voice.", sorted(["nova", "shimmer", "echo", "onyx", "fable", "alloy"]))
    interline = col_interval.number_input("대사 간 간격(ms)",min_value=30, max_value=2000)
    internum = col_interval.number_input("문제 간 간격(ms)",min_value=30, max_value=2000)

    st.write = option
    col_name, col_line = st.columns([2,8])
    if col_buttons.button("Preprocessing"):
        result = ''
        for line in text_input.split("\n"):
            if ":" in line:
                name, talk = line.split(":")
                col_name.markdown(name)
                col_line.markdown(talk)


    # 변환 버튼
    if col_buttons.button("Convert to Speech"):
        try:
            # 음성 파일 저장 경로 설정
            speech_file_path = Path("speech.mp3")

            # 텍스트를 음성으로 변환
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice=option,
                input=text_input
            )

            # 응답에서 음성 데이터를 파일로 저장
            with open(speech_file_path, 'wb') as audio_file:
                for chunk in response.iter_bytes():
                    audio_file.write(chunk)

            st.success("Speech conversion successful!")
            st.audio(str(speech_file_path))

        except Exception as e:
            st.error(f"An error occurred: {e}")



