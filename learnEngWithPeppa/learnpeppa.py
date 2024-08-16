import streamlit as st
import whisper
from moviepy.editor import VideoFileClip
import os
from openai import OpenAI
from datetime import timedelta
from streamlit_player import st_player

def seconds_to_hms(seconds):
    # Ensure the value is a float
    seconds = float(seconds)
    
    # Calculate hours, minutes, and seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Format the time components into HH:MM:SS
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

# Function to format seconds into hh:mm:ss (00:00:00) format without microseconds
def format_time(seconds):
    return str(timedelta(seconds=seconds)).split('.')[0]

def stt_local_whisper():
        model = whisper.load_model("base")
        result = model.transcribe("audio.mp3",task="translate", language="zh")
        return result

def stt_opeai_whisper():
    client = OpenAI()

    audio_file = open("audio.mp3", "rb")
    transcript = client.audio.transcriptions.create(
    file=audio_file,
    model="whisper-1",
    response_format="verbose_json",
    timestamp_granularities=["word"]
    )

    print(transcript.words)
    return transcript.words

# Function to separate sentences based on pause duration and get timestamps
def separate_sentences_with_timestamps(transcription, pause_threshold=0.1):
    sentences = []
    current_sentence = []
    start_time = None
    
    for i, item in enumerate(transcription):
        if not current_sentence:
            start_time = item['start']
        
        current_sentence.append(item['word'])
        
        # Check if there is a significant pause between the current word and the next
        if i < len(transcription) - 1:
            next_word_start = transcription[i + 1]['start']
            current_word_end = item['end']
            pause_duration = next_word_start - current_word_end
            
            if pause_duration >= pause_threshold:
                end_time = item['end']
                sentences.append({
                    'sentence': ' '.join(current_sentence),
                    'start': start_time,
                    'end': end_time
                })
                current_sentence = []

    # Add any remaining words as the last sentence
    if current_sentence:
        end_time = transcription[-1]['end']
        sentences.append({
            'sentence': ' '.join(current_sentence),
            'start': start_time,
            'end': end_time
        })
    
    return sentences

# read a file line by line
def read_file_line_by_line(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        return lines

# Function to handle checkbox selection
def select_option(selected):
    if st.session_state.selected_option != selected:
        st.session_state.selected_option = selected
        st.rerun()

# Set the layout for the page
st.set_page_config(layout="wide")

col1, col2 = st.columns(2)

# Initialize session state to track selected option
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = None

with col1:
    st.title("Video Player")
    if st.session_state.selected_option:
        start_time = st.session_state.selected_option.split(" - ")[0]
        h, m, s = map(int, start_time.split(":"))
        start_seconds = h * 3600 + m * 60 + s
        print(start_time, start_seconds)
        st.video("example.mp4", start_time= start_seconds, autoplay=True)

    else:
        print("set video first.")
        st.video("example.mp4")
    
    # Extract audio from local video
    if os.path.isfile('audio.mp3') == False:
        # Load the video
        video = VideoFileClip("example.mp4")
        # Extract the audio
        audio = video.audio
        # Write the audio to a file
        audio.write_audiofile("audio.mp3")

    # transcribe the audio to text with whisper
    if os.path.isfile('script_with_timestamp.txt') == False:
        # Use whisper model to transcribe
        print("Whisper - Start to transcribe")
        transcript = stt_opeai_whisper()
        print("Whisper - Transcribe Done.")

        # Separate the transcription into sentences with timestamps
        sentences = separate_sentences_with_timestamps(transcript)

        # Display the sentences in the required format with hh:mm:ss timestamps
        script_with_timestamp = ""
        for sentence_data in sentences:
            sentence = sentence_data['sentence']
            start = format_time(sentence_data['start'])
            end = format_time(sentence_data['end'])
            print(f"{start} - {end} : {sentence}")
            script_with_timestamp += f"{start} - {end} : {sentence}\n"

        # Save the script
        with open("script_with_timestamp.txt", 'w') as file:
            file.write(script_with_timestamp)

with col2:
    st.title("Video Script")
    with col2.container(height=770):
        script_list = []
        lines = read_file_line_by_line("script_with_timestamp.txt")
        for line in lines:
            script_list.append(line)

        # # Initialize session state to track selected option
        # if 'selected_option' not in st.session_state:
        #     st.session_state.selected_option = None

        # # Function to handle checkbox selection
        # def select_option(selected):
        #     st.session_state.selected_option = selected

        # Display the checkboxes
        for option in script_list:
            if st.checkbox(option, value=(st.session_state.selected_option == option)):
                select_option(option)
                print("selected on option.")
                

        # # Display the selected option
        # if st.session_state.selected_option:
        #     st.write(f"You selected: {st.session_state.selected_option}")
        #     # Split the sentence to get the start time
        #     start_time = st.session_state.selected_option.split(" - ")[0]
        #     st.audio("audio.mp3", start_time= start_time, autoplay=True)