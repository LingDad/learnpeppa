from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from moviepy.editor import VideoFileClip
from openai import OpenAI
from datetime import timedelta
import markdown

app = Flask(__name__)

# Set a secret key for session management
app.secret_key = os.urandom(24)  # This generates a random 24-byte key

UPLOAD_FOLDER = 'static/uploads/'
AUDIO_FOLDER = 'static/audios/'
SCRIPT_FOLDER = 'static/script/'
LEARNING_MATERIAL_FOLDER = 'static/learning_material/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
app.config['SCRIPT_FOLDER'] = SCRIPT_FOLDER
app.config['LEARNING_MATERIAL_FOLDER'] = LEARNING_MATERIAL_FOLDER

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

def parse_script_file(file_path):
    """Parse the script file and return a list of sentences with their timestamps."""
    script = []
    with open(file_path, 'r') as f:
        for line in f:
            times, sentence = line.split(' : ')
            start_time, end_time = map(float, times.split(' - '))
            script.append({
                'start_time': start_time,
                'end_time': end_time,
                'sentence': sentence.strip()
            })
    return script

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
    learning_material_path = None

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
            session['file_name'] = file_name

            if not os.path.exists(app.config['LEARNING_MATERIAL_FOLDER']):
                os.makedirs(app.config['LEARNING_MATERIAL_FOLDER'])
            
            
            # Extract audio using moviepy
            audio_filename = os.path.splitext(file_name)[0] + '.mp3'
            audio_path = os.path.join(app.config['AUDIO_FOLDER'], audio_filename)
            video_clip = VideoFileClip(filepath)
            video_clip.audio.write_audiofile(audio_path)

            # Do speech to text with openai whisper service
            script_filename = os.path.splitext(file_name)[0] + '.txt'
            script_path = os.path.join(app.config['SCRIPT_FOLDER'], script_filename)
            session['script_path'] = script_path
            if os.path.exists(script_path) == False:
                transcript = stt_opeai_whisper(audio_path)

                # Separate the transcription into sentences with timestamps
                sentences = separate_sentences_with_timestamps(transcript)

                # Display the sentences in the required format with hh:mm:ss timestamps
                script_with_timestamp = ""
                for sentence_data in sentences:
                    sentence = sentence_data['sentence']
                    # start = format_time(sentence_data['start'])
                    # end = format_time(sentence_data['end'])
                    start = sentence_data['start']
                    end = sentence_data['end']
                    print(f"{start} - {end} : {sentence}")
                    script_with_timestamp += f"{start} - {end} : {sentence}\n"

                # Save the script
                with open(script_path, 'w') as file:
                    file.write(script_with_timestamp)
    
    return render_template('index.html', video_path=video_path, file_name=file_name, audio_path=audio_path)

@app.route('/save_api_key', methods=['POST'])
def save_api_key():
    data = request.json
    api_key = data.get('api_key')
    # Here you would typically save the API key securely
    # For example, you might store it in an environment variable or a secure database
    # For this example, we'll just print it (don't do this in production!)
    print(f"Received API key: {api_key}")
    return jsonify({"message": "API key saved successfully"})

@app.route('/save_timestamp', methods=['POST'])
def save_timestamp():
    data = request.json
    timestamp = data.get('timestamp')
    # Store the timestamp in the session
    session['timestamp'] = timestamp
    print(f"Received and saved timestamp: {timestamp}")

    return jsonify({'status': 'success', 'timestamp': timestamp})

@app.route('/last_sentence')
def last_sentence():
    # Retrieve the timestamp from the session
    timestamp = session.get('timestamp')
    
    if not timestamp:
        return redirect(url_for('index'))

    # Convert the timestamp to a float (in seconds)
    timestamp = float(timestamp)
    script_path = session.get('script_path')
    script = parse_script_file(script_path)

    # Find the last sentence before the current timestamp
    last_sentence_info = None
    for entry in script:
        if entry['start_time'] <= timestamp < entry['end_time']:
            last_sentence_info = entry
            break

    if last_sentence_info:
        last_sentence = last_sentence_info['sentence']
        start_time = last_sentence_info['start_time']
        print(f"Last sentence: '{last_sentence}' starting at {start_time} seconds")
    else:
        # If no exact match found, find the closest previous sentence
        last_sentence_info = max([entry for entry in script if entry['start_time'] <= timestamp], key=lambda x: x['start_time'], default=None)
        if last_sentence_info:
            last_sentence = last_sentence_info['sentence']
            start_time = last_sentence_info['start_time']
            print(f"Closest last sentence: '{last_sentence}' starting at {start_time} seconds")
        else:
            # Default to the first sentence if no match is found
            last_sentence_info = script[0]
            last_sentence = last_sentence_info['sentence']
            start_time = last_sentence_info['start_time']

    # Pass the timestamp and sentence back to the client
    return jsonify({'timestamp': start_time, 'sentence': last_sentence})

@app.route('/generate_learning_material')
def generate_learning_material():
    # Add functionality for "Generate Learning Material" button here
    # generate learning material based on script via openai api
    file_name = session.get('file_name')
    learning_material_filename = os.path.splitext(file_name)[0] + '.md'
    learning_material_path = os.path.join(app.config['LEARNING_MATERIAL_FOLDER'], learning_material_filename)
    if not os.path.exists(learning_material_path):
        script = []
        with open(session.get('script_path'), 'r') as file:
            script = file.read()  
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
            {"role": "system", "content": "You are a english teacher. You are given a script of a video and you need to generate learning material based on the script, output including key words, key phrases, key sentences, and grammar points. please use markdown format to output and for sublist markdown please use four spaces."},
            {"role": "user", "content": "Generate learning material based on the following script: " + script}
        ]
        )
        learning_material = response.choices[0].message.content
        with open(learning_material_path, 'w') as file:
            file.write(learning_material)
    else:
        with open(learning_material_path, 'r') as file:
            learning_material = file.read()
    markdown_learning_material = markdown.markdown(learning_material, extensions=['fenced_code', 'codehilite', 'tables', 'toc', 'sane_lists', 'smarty', 'fenced_code'])
    return jsonify({'status': 'success', 'learning_material': markdown_learning_material})

@app.route('/dictation')
def dictation():
    # Add functionality for "Dictation" button here
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
