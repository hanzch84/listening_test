import streamlit as st
from pathlib import Path
from openai import OpenAI
import os
from dotenv import load_dotenv
from gtts import gTTS
from collections import Counter
import re
import wave

def which_eng_kor(input_s):
    count = Counter(input_s)
    k_count = sum(count[c] for c in count if ord('가') <= ord(c) <= ord('힣'))
    e_count = sum(count[c] for c in count if 'a' <= c.lower() <= 'z')
    return "ko" if k_count > e_count else "en"

def extract_question(text):
    match = re.match(r'(\d{1,2}\.?)\s*(.*)', text)
    if match:
        number = match.group(1).strip()
        question = match.group(2).strip()
        return number, question
    else:
        return None, text

def append_audio_file(final_wf, input_file):
    with wave.open(input_file, 'rb') as wf:
        if final_wf.getnchannels() == 0:
            final_wf.setnchannels(wf.getnchannels())
            final_wf.setsampwidth(wf.getsampwidth())
            final_wf.setframerate(wf.getframerate())
        while True:
            data = wf.readframes(1024)
            if not data:
                break
            final_wf.writeframes(data)

# .env 파일 로드
load_dotenv()

# 환경 변수에서 OpenAI API 키 가져오기
api_key = os.getenv('OPENAI_API_KEY')

# OpenAI API 키 설정
if not api_key:
    st.error("API key not found. Please set the OPENAI_API_KEY environment variable.")
else:
    client = OpenAI(api_key=api_key)

    st.title("Text-to-Speech with OpenAI and gTTS")

    col_kvoice, col_voice, col_interval, col_buttons = st.columns([3, 3, 3, 3])
    ko_option = col_kvoice.radio("Select a Korean voice.", sorted(["nova", "shimmer", "echo", "onyx", "fable", "alloy"]))
    option = col_voice.radio("Select a basic voice.", sorted(["nova", "shimmer", "echo", "onyx", "fable", "alloy"]))
    interline = col_interval.number_input("대사 간 간격(ms)", min_value=30, max_value=2000)
    internum = col_interval.number_input("문제 간 간격(ms)", min_value=30, max_value=2000)

    col_lang, col_name, col_line = st.columns([1, 2, 8])
    
    if 'input_text' not in st.session_state:
        st.session_state.input_text = """1. 다음을 듣고, 남자가 하는 말의 목적으로 가장 적절한 것을 고르시오.
                                M: Hello, Lockwood High School students. This is your school librarian,
                                Mr. Wilkins. I’m sure you’re aware that our school library is hosting a
                                bookmark design competition. I encourage students of all grades to
                                participate in the competition. The winning designs will be made into
                                bookmarks, which will be distributed to library visitors. We’re also giving
                                out a variety of other prizes. So don’t let this great opportunity slip away.
                                Since the registration period for the bookmark design competition ends this
                                Friday, make sure you visit our school library to submit your application.
                                Come and participate to display your creativity and talents.

                                2. 대화를 듣고, 여자의 의견으로 가장 적절한 것을 고르시오.
                                M: Honey, do you want some apples with breakfast?
                                W: Sounds great. Can you save the apple peels for me?
                                M: Why? What do you want them for?
                                W: I’m going to use them to make a face pack. Apple peels are effective for
                                improving skin condition.
                                M: Where did you hear about that?
                                W: I recently read an article about their benefits for our skin.
                                M: Interesting. What’s in them?
                                W: It said apple peels are rich in vitamins and minerals, so they moisturize our
                                skin and enhance skin glow.
                                M: That’s good to know.
                                W: Also, they remove oil from our skin and have a cooling effect.
                                M: Wow! Then I shouldn’t throw them away.
                                W: Right. Apple peels can help improve our skin condition.
                                M: I see. I’ll save them for you."""

    text_input = st.text_area("Enter the text you want to convert to speech", st.session_state.input_text, key="input_area", height=st.session_state.input_text.count('\n') * 24)

    if col_buttons.button("Preprocessing"):
        for line in st.session_state.input_text.split("\n"):
            if ":" in line:
                name, talk = line.split(":", 1)
            elif which_eng_kor(line) == "ko":
                name, talk = extract_question(line)
                if not name:
                    name, talk = "", line
            else:
                name, talk = "", line

            col_lang.markdown(which_eng_kor(line))
            col_name.markdown(name.strip())
            col_line.markdown(talk.strip())

    if col_buttons.button("Convert to Speech"):
        try:
            final_output = "final_speech.wav"
            with wave.open(final_output, 'wb') as final_wf:
                for line in st.session_state.input_text.split("\n"):
                    if line.strip() == "":
                        continue

                    if which_eng_kor(line) == "ko":
                        tts = gTTS(line, lang='ko')
                        temp_file = f"temp.wav"
                        tts.save(temp_file)
                    else:
                        response = client.audio.speech.create(
                            model="tts-1-hd",
                            voice=option,
                            input=line
                        )
                        temp_file = f"temp.wav"
                        with open(temp_file, 'wb') as audio_file:
                            for chunk in response.iter_bytes():
                                audio_file.write(chunk)
                    
                    append_audio_file(final_wf, temp_file)
                    os.remove(temp_file)

            st.success("Speech conversion successful!")
            st.audio(final_output)

        except Exception as e:
            st.error(f"An error occurred: {e}")
