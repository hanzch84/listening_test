import streamlit as st
from pathlib import Path
from openai import OpenAI
import os

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

    # 변환 버튼
    if st.button("Convert to Speech"):
        try:
            # 음성 파일 저장 경로 설정
            speech_file_path = Path("speech.mp3")

            # 텍스트를 음성으로 변환
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice="alloy",
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