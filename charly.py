import subprocess
import argparse
import os
import json
import numpy as np
import librosa
from scipy.signal import correlate

def get_duration(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        duration = float(json.loads(result.stdout)['format']['duration'])
        return duration
    except (subprocess.CalledProcessError, ValueError, KeyError) as e:
        raise RuntimeError(f"Error running ffprobe for file {file_path}: {e}")

def get_audio_codec(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        codec_name = result.stdout.strip()
        return codec_name
    except (subprocess.CalledProcessError, ValueError) as e:
        raise RuntimeError(f"Error getting codec from file {file_path}: {e.stderr}")

def get_audio_metadata(file_path):
    metadata = {'language': 'und', 'title': 'untitled'}
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_type:stream_tags=language,title', '-of', 'json', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding='utf-8'
        )
        probe = json.loads(result.stdout)
        streams = probe.get('streams', [])
        for stream in streams:
            if stream['codec_type'] == 'audio':
                tags = stream.get('tags', {})
                metadata['language'] = tags.get('language', 'und')
                metadata['title'] = tags.get('title', 'untitled')
        return metadata
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        print(f"Error retrieving metadata for file {file_path}: {e}")
        return metadata

def extract_audio(file_path, output_temp_audio):
    command = [
        'ffmpeg', '-y',
        '-i', file_path,
        '-q:a', '0',
        '-map', 'a',
        output_temp_audio
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error extracting audio: {e.stderr}")
    return output_temp_audio

def compare_audio_sync(main_audio, secondary_audio, target_sr=22050):
    y1, sr1 = librosa.load(main_audio, sr=target_sr)
    y2, sr2 = librosa.load(secondary_audio, sr=target_sr)

    y1 = librosa.util.normalize(y1)
    y2 = librosa.util.normalize(y2)

    correlation = correlate(y1, y2, mode='full')
    delay = (np.argmax(correlation) - len(y2)) / target_sr  # delay in seconds

    if delay > 0:
        return 'delay', delay
    else:
        return 'advance', abs(delay)

def adjust_audio(audio_file, adjustment, audio_delay, target_duration, codec, metadata):
    temp_audio = f"temp_audio.wav"  # Save as WAV to avoid codec issues
    final_audio = f"final_temp_audio.{codec}"
    command = []

    if audio_delay == 'advance':
        command = [
            'ffmpeg', '-y',
            '-i', audio_file,
            '-ss', str(adjustment),
            '-t', str(target_duration),  # Ensure target duration matches the main file
            '-c', 'copy',
            temp_audio
        ]
    elif audio_delay == 'delay':
        command = [
            'ffmpeg', '-y',
            '-i', audio_file,
            '-af', f'adelay={int(adjustment * 1000)}|{int(adjustment * 1000)},apad=whole_dur={target_duration}',
            '-c:a', 'pcm_s16le',  # Save as WAV to avoid codec issues
            temp_audio
        ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error adjusting audio: {e.stderr}")

    # Transcode back to original codec
    command_transcode = [
        'ffmpeg', '-y',
        '-i', temp_audio,
        '-c:a', codec,
        '-metadata', f"title={metadata['title']}",
        '-metadata', f"language={metadata['language']}",
        final_audio
    ]

    try:
        subprocess.run(command_transcode, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error transcoding audio: {e.stderr}")
    finally:
        os.remove(temp_audio)
    
    return final_audio

def main(main_file, audio_file, audio_delay, output_file, seconds, use_auto_sync):
    if not os.path.isfile(main_file):
        raise FileNotFoundError(f"The main file does not exist: {main_file}")
    if not os.path.isfile(audio_file):
        raise FileNotFoundError(f"The audio file does not exist: {audio_file}")

    main_file_duration = get_duration(main_file)
    audio_file_duration = get_duration(audio_file)

    print(f"Duration of main file in seconds: {main_file_duration}")
    print(f"Duration of audio file in seconds: {audio_file_duration}")

    main_metadata = get_audio_metadata(main_file)
    audio_metadata = get_audio_metadata(audio_file)
    print(f"Extracted main audio metadata: {main_metadata}")
    print(f"Extracted additional audio metadata: {audio_metadata}")

    if use_auto_sync:
        main_audio = extract_audio(main_file, 'main_temp_audio.wav')
        secondary_audio = extract_audio(audio_file, 'secondary_temp_audio.wav')
        audio_delay, audio_adjustment = compare_audio_sync(main_audio, secondary_audio)
        os.remove(main_audio)
        os.remove(secondary_audio)
        print(f"Automatic synchronization suggests: {audio_delay} by {audio_adjustment} seconds")
    else:
        audio_adjustment = seconds if seconds is not None else 0
        print(f"Manual synchronization with user-provided delay/advance: {audio_delay} by {audio_adjustment} seconds")

    # Use main_file duration to trim audio correctly
    if not use_auto_sync and audio_adjustment == 0:
        audio_adjustment = audio_file_duration - main_file_duration

        print(f"Non-auto sync adjustment: {audio_delay} by {audio_adjustment} seconds")

    print(f"Audio adjustment in seconds: {audio_adjustment}")

    codec = get_audio_codec(audio_file)
    adjusted_audio = adjust_audio(audio_file, audio_adjustment, audio_delay, main_file_duration, codec, audio_metadata)

    if not output_file:
        base, ext = os.path.splitext(main_file)
        output_file = f"{base}_joined{ext}"


    # Find the number of audio streams in the output file
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'json', main_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        audio_streams = json.loads(result.stdout).get('streams', [])
        last_audio_index = audio_streams[-1]['index'] if audio_streams else 0
    except Exception as e:
        print(f"Error retrieving audio streams: {e}")
        return

    # Build ffmpeg command for combining video and adjusted audio
    command = [
        'ffmpeg', '-y',
        '-i', main_file,
        '-i', adjusted_audio,
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-map', '0:v',
        '-map', '0:a',  # Copy the original audio
        '-map', '1:a',  # Add the adjusted audio
        '-map', '0:s',  # Map all subtitle streams from the main file
        '-metadata:s:a:' + str(last_audio_index), f'language={audio_metadata.get("language", "und")}',
        '-metadata:s:a:' + str(last_audio_index), f'title={audio_metadata.get("title", "untitled")}',
        output_file
    ]

    # Execute ffmpeg command
    try:
        process = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        print(process.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running ffmpeg: {e.stderr}")
        return

    # Remove temporary audio file
    if os.path.exists(adjusted_audio):
        os.remove(adjusted_audio)
        print(f'Temporary file {adjusted_audio} removed.')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronize video and audio using ffmpeg.")
    parser.add_argument("--main_file", required=True, help="The main file (which will contain the final video, audio, and subtitles)")
    parser.add_argument("--audio_file", required=True, help="The secondary file (from which the additional audio will be extracted)")
    parser.add_argument("--audio_delay", choices=['delay', 'advance'], default='delay', help="Whether to delay or advance the audio to synchronize")
    parser.add_argument("--output_file", help="Name of the output file (optional)")
    parser.add_argument("--seconds", type=float, help="Seconds to use for advancing or delaying the audio (optional)")
    parser.add_argument("--use_auto_sync", action='store_true', help="Use automatic audio synchronization")

    args = parser.parse_args()
    main(args.main_file, args.audio_file, args.audio_delay, args.output_file, args.seconds, args.use_auto_sync)
