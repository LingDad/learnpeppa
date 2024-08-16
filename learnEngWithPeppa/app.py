from flask import Flask, render_template, request, redirect, url_for
import os
from moviepy.editor import VideoFileClip
from openai import OpenAI
from datetime import timedelta

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads/'
AUDIO_FOLDER = 'static/audios/'
SCRIPT_FOLDER = 'static/script/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
app.config['SCRIPT_FOLDER'] = SCRIPT_FOLDER

def stt_opeai_whisper(audio_path):
    client = OpenAI()

    audio_file = open(audio_path, "rb")
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

# Function to format seconds into hh:mm:ss (00:00:00) format without microseconds
def format_time(seconds):
    return str(timedelta(seconds=seconds)).split('.')[0]

# Ensure the upload and audio folders exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(AUDIO_FOLDER):
    os.makedirs(AUDIO_FOLDER)

if not os.path.exists(SCRIPT_FOLDER):
    os.makedirs(SCRIPT_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def index():
    video_path = None
    file_name = None
    audio_path = None
    script_path = None

    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        
        file = request.files['file']
        
        if file.filename == '':
            return 'No selected file'
        
        if file:
            file_name = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
            file.save(filepath)
            video_path = filepath
            
            # Extract audio using moviepy
            audio_filename = os.path.splitext(file_name)[0] + '.mp3'
            audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)
            video_clip = VideoFileClip(filepath)
            video_clip.audio.write_audiofile(audio_path)

            # Do speech to text with openai whisper service
            script_filename = os.path.splitext(file_name)[0] + '.txt'
            script_path = os.path.join(app.config['SCRIPT_FOLDER'], script_filename)
            if os.path.exists(script_path) == False:
                transcript = stt_opeai_whisper(audio_path)

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
                with open(script_path, 'w') as file:
                    file.write(script_with_timestamp)
    
    return render_template('index.html', video_path=video_path, file_name=file_name, audio_path=audio_path)

@app.route('/last_video')
def last_video():
    # Add functionality for "Last" button here
    return redirect(url_for('index'))

@app.route('/next_video')
def next_video():
    # Add functionality for "Next" button here
    return redirect(url_for('index'))

@app.route('/dictation')
def dictation():
    # Add functionality for "Dictation" button here
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
