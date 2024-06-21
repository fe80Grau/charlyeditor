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
    temp_audio = f"temp_audio.{codec}"
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
            '-c:a', 'eac3',  # Use EAC3 codec as required by muxer
            temp_audio
        ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error adjusting audio: {e.stderr}")

    # Write metadata to a temporary text file
    metadata_text = f"""[CHAPTER]
    TIMEBASE=1/1000
    START=0
    END={target_duration * 1000}
    title={metadata['title']}
    language={metadata['language']}"""

    with open("metadata.txt", "w", encoding="utf-8") as file:
        file.write(metadata_text)

    # Apply metadata to the adjusted audio using the text file
    command_metadata = [
        'ffmpeg', '-y',
        '-i', temp_audio,
        '-i', 'metadata.txt',
        '-map_metadata', '1',
        '-c', 'copy',
        final_audio
    ]

    try:
        subprocess.run(command_metadata, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error applying metadata to adjusted audio: {e.stderr}")
    finally:
        os.remove(temp_audio)
        os.remove("metadata.txt")  # Clean up the temporary file
    
    return final_audio

def main(main_file, audio_file, audio_delay, output_file, seconds, use_auto_sync):
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
        output_file = f"{base}_edited{ext}"

    # Properly quoting paths to handle spaces or special characters
    main_file_quoted = f'"{main_file}"'
    adjusted_audio_quoted = f'"{adjusted_audio}"'
    output_file_quoted = f'"{output_file}"'

    # Build ffmpeg command for combining video and adjusted audio, ensuring proper quoting and encoding
    command = [
        'ffmpeg', '-y',
        '-i', main_file_quoted,
        '-i', adjusted_audio_quoted,
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-map', '0:v',
        '-map', '0:a',
        '-map', '1:a',
        '-metadata:s:a:1', f'language={audio_metadata.get("language", "und")}',
        '-metadata:s:a:1', f'title={audio_metadata.get("title", "untitled")}',
        output_file_quoted
    ]

    try:
        subprocess.run(' '.join(command), check=True, shell=True)
        print(f'Output file saved as {output_file}')
    except subprocess.CalledProcessError as e:
        print(f"Error running ffmpeg: {e.stderr}")

    # Remove temporary audio file
    if os.path.exists(adjusted_audio):
        os.remove(adjusted_audio)
        print(f'Temporary file {adjusted_audio} removed.')
