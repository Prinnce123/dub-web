from flask import Flask, request, jsonify, Response, render_template
import yt_dlp as youtube_dl
import os
from googletrans import Translator
from gtts import gTTS
import moviepy.editor as mp
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)  # Enable debug logging

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-video', methods=['POST'])
def process_video():
    data = request.json
    video_url = data.get('videoURL')
    target_language = data.get('language')

    if not video_url or not target_language:
        return jsonify({'success': False, 'error': 'Missing videoURL or language'}), 400

    try:
        # Step 1: Download the video from YouTube
        ydl_opts = {'format': 'best', 'outtmpl': '%(title)s.%(ext)s'}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            if info_dict is None:
                raise ValueError("Failed to extract video information. The URL might be incorrect or restricted.")
            video_title = info_dict.get('title', 'video')
            video_filename = video_title + ".mp4"
            logging.info(f"Video downloaded: {video_filename}")

        # Step 2: Extract the audio from the video
        video_clip = mp.VideoFileClip(video_filename)
        audio_filename = "audio.wav"
        video_clip.audio.write_audiofile(audio_filename)

        # Step 3: Transcribe the audio (dummy text used here)
        transcribed_text = "This is a sample transcription for testing purposes."
        logging.info(f"Transcribed text: {transcribed_text}")

        # Step 4: Translate the transcribed text
        translator = Translator()
        translated_text = translator.translate(transcribed_text, dest=target_language).text
        logging.info(f"Translated text: {translated_text}")

        # Step 5: Convert translated text to speech
        tts = gTTS(translated_text, lang=target_language)
        tts_audio_filename = "translated_audio.mp3"
        tts.save(tts_audio_filename)

        # Step 6: Combine the translated audio with the original video
        new_audio = mp.AudioFileClip(tts_audio_filename)
        final_video = video_clip.set_audio(new_audio)
        final_output_filename = f"dubbed_{video_title}.mp4"
        final_video.write_videofile(final_output_filename)

        # Step 7: Stream the video
        def generate():
            with open(final_output_filename, "rb") as video:
                chunk = video.read(1024 * 1024)  # Stream in chunks
                while chunk:
                    yield chunk
                    chunk = video.read(1024 * 1024)

        return jsonify({'success': True, 'streamURL': f'/stream/{final_output_filename}'})

    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/stream/<filename>')
def stream_video(filename):
    video_path = os.path.join(os.getcwd(), filename)
    return Response(generate_video_stream(video_path), mimetype='video/mp4')

def generate_video_stream(video_path):
    with open(video_path, 'rb') as video_file:
        chunk = video_file.read(1024 * 1024)  # Stream the video in chunks of 1MB
        while chunk:
            yield chunk
            chunk = video_file.read(1024 * 1024)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
