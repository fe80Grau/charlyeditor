import subprocess
import argparse
import os
import json
import numpy as np
import librosa
from scipy.signal import correlate
from tqdm import tqdm

def get_duration(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        duration = float(result.stdout.strip())
        return duration
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error running ffprobe for file {file_path}: {e.stderr}")
    except ValueError as e:
        raise RuntimeError(f"Error interpreting the duration of file {file_path}: {e}")

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
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error getting codec from file {file_path}: {e.stderr}")

def get_language_metadata(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'stream=index,codec_type:stream_tags=language', '-of', 'json', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        probe = json.loads(result.stdout)
        metadata = {'audio': 'und', 'subtitle': 'und'}
        for stream in probe['streams']:
            if 'tags' in stream and 'language' in stream['tags']:
                if stream['codec_type'] == 'audio':
                    metadata['audio'] = stream['tags']['language']
                elif stream['codec_type'] == 'subtitle':
                    metadata['subtitle'] = stream['tags']['language']

        return metadata
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error running ffprobe for file {file_path}: {e.stderr}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Error interpreting metadata from file {file_path}: {e}")

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
        print(f"Error extracting audio: {e.stderr}")
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

def extract_and_adjust_audio(audio_file, adjustment, audio_delay):
    audio_codec = get_audio_codec(audio_file)
    temp_audio = "temp_audio." + ("mka" if audio_codec == "eac3" else "aac")
    
    if audio_delay == 'advance':
        command = [
            'ffmpeg', '-y',
            '-i', audio_file,
            '-ss', str(adjustment),
            '-c', 'copy',
            temp_audio
        ]
    elif audio_delay == 'delay':
        command = [
            'ffmpeg', '-y',
            '-i', audio_file,
            '-af', f'adelay={int(adjustment * 1000)}|{int(adjustment * 1000)}',
            '-c', 'copy',
            temp_audio
        ]
    else:
        raise ValueError("audio_delay must be 'delay' or 'advance'")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error adjusting audio: {e.stderr}")
    
    return temp_audio

def main(main_file, audio_file, audio_delay, subtitle_source, output_file, seconds, use_auto_sync):
    main_file_duration = get_duration(main_file)
    audio_file_duration = get_duration(audio_file)

    print(f"Duration of main file in seconds: {main_file_duration}")
    print(f"Duration of audio file in seconds: {audio_file_duration}")

    if use_auto_sync:
        main_audio = extract_audio(main_file, 'main_temp_audio.wav')
        secondary_audio = extract_audio(audio_file, 'secondary_temp_audio.wav')
        auto_audio_delay, auto_adjustment = compare_audio_sync(main_audio, secondary_audio)
        audio_delay = auto_audio_delay
        audio_adjustment = auto_adjustment
        os.remove(main_audio)
        os.remove(secondary_audio)
        print(f"Automatic synchronization suggests: {audio_delay} by {audio_adjustment} seconds")
    else:
        if seconds is not None:
            audio_adjustment = seconds
        else:
            if audio_delay == 'advance':
                audio_adjustment = max(0, audio_file_duration - main_file_duration)
            elif audio_delay == 'delay':
                audio_adjustment = max(0, main_file_duration - audio_file_duration)

    print(f"Audio adjustment in seconds: {audio_adjustment}")
    
    temp_audio = extract_and_adjust_audio(audio_file, audio_adjustment, audio_delay)

    # Get language metadata
    main_metadata = get_language_metadata(main_file)
    audio_metadata = get_language_metadata(temp_audio)

    # Determine where to extract subtitles from
    subtitle_source_file = main_file if subtitle_source == "main" else audio_file
    subtitle_map = '0:s?' if subtitle_source == "main" else '1:s?'

    if not output_file:
        base, ext = os.path.splitext(main_file)
        output_file = f"{base}_edited{ext}"

    # Build the ffmpeg command
    command = [
        'ffmpeg', '-y',
        '-i', main_file,
        '-i', temp_audio,
        '-map', '0:v',
        '-map', '0:a',
        '-map', '1:a',
        '-map', subtitle_map,
        '-c:v', 'copy',
        '-c:a', 'copy',  # Copy audio as-is
        '-c:s', 'copy',
        '-metadata:s:a:0', f'language={main_metadata["audio"]}',
        '-metadata:s:a:1', f'language={audio_metadata["audio"]}',
        '-metadata:s:s', f'language={main_metadata["subtitle"] if subtitle_source == "main" else audio_metadata["subtitle"]}',
        output_file
    ]

    try:
        subprocess.run(command, check=True)
        print(f'Output file saved as {output_file}')
    except subprocess.CalledProcessError as e:
        print(f"Error running ffmpeg: {e.stderr}")

    # Remove temporary audio file
    if os.path.exists(temp_audio):
        os.remove(temp_audio)
        print(f'Temporary file {temp_audio} removed.')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronize video and audio using ffmpeg.")
    parser.add_argument("--main_file", required=True, help="The main file (which will contain the final video, audio, and subtitles)")
    parser.add_argument("--audio_file", required=True, help="The secondary file (from which the additional audio will be extracted)")
    parser.add_argument("--audio_delay", choices=['delay', 'advance'], default='delay', help="Whether to delay or advance the audio to synchronize")
    parser.add_argument("--subtitle_source", choices=['main', 'audio'], default='main', help="The file from which to extract subtitles ('main' for main_file and 'audio' for audio_file)")
    parser.add_argument("--output_file", help="Name of the output file (optional)")
    parser.add_argument("--seconds", type=float, help="Seconds to use for advancing or delaying the audio (optional)")
    parser.add_argument("--use_auto_sync", action='store_true', help="Use automatic audio synchronization")

    args = parser.parse_args()
    main(args.main_file, args.audio_file, args.audio_delay, args.subtitle_source, args.output_file, args.seconds, args.use_auto_sync)
