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
    match = re.match(r'^\s*(\d+)\s*\.?\s*번?\s*(.*)', text)
    if match:
        number = match.group(1).strip()
        question = match.group(2).strip()
        return number, question
    return None, text.lstrip()


def num_to_korean(n):
    digit = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
    unit  = ["", "십", "백", "천"]
    n = int(n)
    if n == 0:
        return "영"
    result = ""
    str_n = str(n)
    length = len(str_n)
    for i, ch in enumerate(str_n):
        num = int(ch)
        u = unit[length - i - 1]
        if num == 0:
            continue
        # 만약 자릿수가 십·백·천이고 값이 1이면 '일' 생략
        if num == 1 and u != "":
            result += u
        else:
            result += digit[num] + u
    return result


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

def extract_speaker(text):
    m_match = re.match(r'^\s*M\s*:?\s*(.*)', text)
    if m_match:
        return "male", m_match.group(1).strip()
    w_match = re.match(r'^\s*W\s*:?\s*(.*)', text)
    if w_match:
        return "female", w_match.group(1).strip()
    return None, text

def extract_tone(text):
    # 문장 맨 앞 [지시어] 를 뽑아내고 본문에서 제거
    m = re.match(r'^\s*\[([^\]]+)\]\s*(.*)', text)
    if m:
        return m.group(1).strip(), m.group(2)
    return None, text


load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    # Streamlit Community Cloud secrets are exposed through st.secrets.
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        api_key = None

if not api_key:
    st.error("OpenAI API 키를 찾지 못했습니다. OPENAI_API_KEY 환경 변수 또는 Streamlit Secrets에 설정하세요.")
else:
    client = OpenAI(api_key=api_key)

    st.markdown(
        '''
        <h1>듣기평가 음원 만들기: En Listen
        <abbr
            title="v1.6 업데이트:
    1) 성별·문제번호 지표 없는 줄도 직전 목소리 유지
    2) 한국어 숫자 읽기를 자연스럽게 개선
    3) 추가 음성 옵션(ash, ballad, coral, sage, verse) 지원
    4) 문장별 톤 지시([Excited], [Calmly] 등) 적용 기능 추가
    5) 음원 생성 속도 향상"
            style="cursor: help; text-decoration: none; border-bottom: 1px dotted #888;"
        >v1.6</abbr>
        </h1>
        ''',
        unsafe_allow_html=True
    )

    col_speed, col_subheader = st.columns([5, 7])
    speed_rate = col_speed.slider("음성 속도(배)", 0.55, 1.85, 1.0, 0.05)
    col_subheader.markdown('<p style="font-size:10pt; color: #6b6c70;text-align: right;">제작: 교사 박현수, 버그 및 개선 문의: <a href="mailto:hanzch84@gmail.com">hanzch84@gmail.com</a></p>', unsafe_allow_html=True)
    col_subheader.markdown('<p style="font-size:14pt; color: #6b6c70;text-align: right;"><a href="https://www.openai.fm">음성 옵션 미리듣기(openai TTS api overview page)</a></p>', unsafe_allow_html=True)
    col_voice, col_interval = st.columns([10, 3])
    ko_option = col_voice.radio("한국어 음성",
        ['alloy', 'fable', 'nova', 'shimmer', 'echo', 'onyx', 'ash', 'ballad', 'coral', 'sage', 'verse'],
        key="korean_option", index=2, horizontal=True,help="한국어 음성을 선택하세요.")
    female_voice = col_voice.radio("여성 음성",['alloy', 'fable', 'nova', 'shimmer', 'coral', 'sage', 'order', 'random'],
        key="female_option", horizontal=True, help="여성 음성을 선택하세요. random은 무작위, order는 순차.")
    male_voice = col_voice.radio("남성 음성", ['echo', 'onyx', 'ash', 'ballad', 'verse', 'order', 'random'],
        key="male_option", horizontal=True, help="남성 음성을 선택하세요. random은 무작위, order는 순차.")
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
        st.session_state.input_text = """13. 다음을 듣고, 남자가 하는 말의 목적으로 가장 적절한 것을 고르시오.
M: Hello, Maplewood High School students.
This is your school librarian, Mr. Johnson. 

W: Number One.
[Speak in a monotone, robotic, and unnatural tone]testing and tasting the app.

W: Number Three.
[Speak in an extreamly angry tone]toasting and twisting the app.

W: Number Five.
[Excited and enthusiastic like breakng news]  tossing and trusting the app.

29번 다음 대화를 듣고, 여자의 의견으로 가장 적절한 것을 고르시오.
[Theatrical]   M: Hi, Sweetie.
[Suspenseful]  W: Could you keep the orange peels for me?
[Curious]      M: Why? What are you going to do with them?
[Soft whisper] W: I’m planning to use them to make a natural cleaner."""

    st.code("""'대본 입력란'의 예시를 지우고 듣기평가 대본을 입력하세요.(Ctrl+Enter)
앞에 숫자와 '번'또는 '.'을 쓰면 문제번호를 인식합니다.
앞에 음성지표(M:남성,W:여성)를 넣으면 해당 성별 음성으로 바뀝니다.
각 행의 첫 머리 대괄호[]속에 지시문을 적으면 말투를 바꿀 수 있습니다.
'random'은 문제마다 해당 성별의 음성을 무작위로 선택합니다.
'order'는 문제마다 해당 성별의 음성을 순서대로 바꿔 줍니다.
문장, 문제 간격을 조절할 수 있습니다. (각색된 예시 대본 원본 출처:EBS)""", language="haskell")
    st.session_state.input_text = st.text_area("대본 입력란", st.session_state.input_text, key="input_area", height=max(st.session_state.input_text.count('\n') * 26 + 10, 400))

    if col_interval.button("🔊 음원 생성하기", disabled=is_input_exist(st.session_state.input_text),):
        print("Generating audio...")
        # Do not leave a previous file visible if this attempt fails.
        st.session_state.pop("speech_file_path", None)

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
            current_voice = ko_option
            for sentence in sentences:
                # 앞뒤 공백 제거
                sentence = sentence.lstrip()
                # 언어 판별
                lang = which_eng_kor(sentence)

                # ✅ 톤 지시 추출 ([Excited], [Calmly] 등)
                tone_hint, sentence = extract_tone(sentence)

                # ✅ 성별 힌트 추출 (M:, W: 제거)
                gender_hint, sentence = extract_speaker(sentence)

                # ✅ 문제 번호 추출 (번호·번 제거)
                number, sentence = extract_question(sentence)

                # ✅ 문제 번호 읽기
                if number and number != current_number:
                    current_number = number
                    if female_voice in ["random", "order"]:
                        st.session_state.female_sequence += 1
                    if male_voice in ["random", "order"]:
                        st.session_state.male_sequence += 1

                    if not is_first_question:
                        tts += internum_silence
                    is_first_question = False

                if number:
                    korean_number = num_to_korean(number) + "번 문제입니다."
                    text_to_convert = f"{korean_number} {sentence}"
                else:
                    text_to_convert = sentence

                # ✅ 성별 지표가 있을 때만 목소리 변경
                # ——— 음성 지표가 있을 때만 목소리 변경 ———
                if gender_hint == "female":
                    current_voice = get_voice(female_voice, st.session_state.female_sequence, "female")
                elif gender_hint == "male":
                    current_voice = get_voice(male_voice, st.session_state.male_sequence, "male")

                # ——— 번호만 있는 줄이라면 시퀀스만 증가 (목소리는 그대로) ———
                elif number and number != current_number:
                    if female_voice in ["random", "order"]:
                        st.session_state.female_sequence += 1
                    if male_voice   in ["random", "order"]:
                        st.session_state.male_sequence   += 1

                # ——— 그 외(지표도 번호도 없으면) current_voice 유지 ———
                else:
                    # current_voice 를 변경하지 않음
                    pass

                # ——— 안전장치: 혹시 None 이면 기본 한국어 음성 사용 ———
                if current_voice is None:
                    current_voice = ko_option

                if text_to_convert.strip():
                    # 스트리밍 API 사용
                    with client.audio.speech.with_streaming_response.create(
                        model="gpt-4o-mini-tts",           # 최신 속도 지원 모델
                        voice=current_voice,
                        input=text_to_convert,
                        speed=speed_rate,
                        instructions=tone_hint or "Speak clearly and calmly like a teacher, with a steady pace, natural pronunciation, emphasis on key phrases."

                    ) as response:
                        audio_bytes = BytesIO()
                        # 바이트 청크를 받아서 버퍼에 쓴 뒤
                        for chunk in response.iter_bytes():
                            audio_bytes.write(chunk)
                        # MP3 로 디코딩
                        audio_chunk = AudioSegment.from_file(BytesIO(audio_bytes.getvalue()), format="mp3")
                        tts += audio_chunk

                    # 문장 사이 무음
                    tts += interline_silence

            tts.export(speech_file_path, format="mp3")
            st.session_state.speech_file_path = str(speech_file_path)
            st.session_state.success_message = "음성 변환이 성공적으로 완료되었습니다!"
            st.session_state.en_warning_message = "고지 사항: 이 목소리는 인공지능(AI)으로 생성된 것이며, 실제 사람의 목소리가 아닙니다."
            print("Audio file saved successfully.")

        except Exception as e:
            # The old behavior only printed failures to the server log and showed
            # balloons, leaving the user with no explanation or download.
            print(f"An error occurred: {type(e).__name__}: {e}")
            st.error(f"음원 생성에 실패했습니다 ({type(e).__name__}): {e}")
            if type(e).__name__ == "AuthenticationError":
                st.info("API 키가 만료·폐기되었거나 권한이 없습니다. 사용 가능한 개인/프로젝트 키를 Streamlit Secrets의 OPENAI_API_KEY에 등록하세요.")
            elif type(e).__name__ == "RateLimitError":
                st.info("API 사용 한도, 결제 잔액 또는 요청 속도 제한을 확인하세요.")
            elif type(e).__name__ == "APIConnectionError":
                st.info("OpenAI API에 연결하지 못했습니다. 배포 환경의 네트워크 상태를 확인하고 다시 시도하세요.")
        else:
            st.balloons()
        finally:
            overlay_container.empty()

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
