# Video and Audio Synchronization Script

This script synchronizes video and audio files using `ffmpeg` and performs automatic synchronization using audio signal analysis. It can delay or advance the audio to match the video based on the specified parameters.

## Features

- Synchronize video and audio files with options to delay or advance the audio.
- Automatic synchronization using audio signal analysis.
- Extract and adjust audio tracks.
- Maintain existing metadata for audio and subtitles.
- Option to specify synchronization in seconds for precise control.
- Progress indicator for the synchronization process.

## Requirements

- Python 3.x
- `ffmpeg`
- `ffprobe`
- Python libraries: `numpy`, `librosa`, `scipy`, `tqdm`

## Installation

1. Install `ffmpeg` and `ffprobe`:
   - You can download from [ffmpeg.org](https://ffmpeg.org/download.html) and follow the installation instructions for your operating system.

2. Install the required Python libraries:
   ```sh
   pip install -r requierments.txt
   ```

## Usage

### Basic Usage

Synchronize video and audio with automatic synchronization:
```sh
python charly.py --main_file "<path_to_main_video>.mkv" --audio_file "<path_to_audio_file>.mkv" --use_auto_sync --subtitle_source main
```

### Specify Synchronization Seconds

Synchronize video and audio with a specified delay or advance in seconds:
```sh
python charly.py --main_file "<path_to_main_video>.mkv" --audio_file "<path_to_audio_file>.mkv" --seconds <number_of_seconds> --audio_delay <delay|advance> --subtitle_source main
```

### Parameters

- `--main_file` (required): The main file that will contain the final video, audio, and subtitles.
- `--audio_file` (required): The secondary file from which the additional audio will be extracted.
- `--audio_delay` (default: `delay`): Whether to delay (`'delay'`) or advance (`'advance'`) the audio to synchronize.
- `--subtitle_source` (default: `main`): The file from which to extract subtitles (`'main'` for main file and `'audio'` for audio file).
- `--output_file` (optional): Name of the output file.
- `--seconds` (optional): Seconds to use for advancing or delaying the audio.
- `--use_auto_sync` (flag): Use automatic audio synchronization based on audio signal analysis.

### Example Commands

#### Automatic Synchronization (Better option)
```sh
python charly.py --main_file "D:\\downloads\\[CR] VINLAND SAGA - S01E01 [1080p].mkv" --audio_file "D:\\downloads\\VINLAND SAGA_S01E01_Episodio 1.mkv" --use_auto_sync --subtitle_source main
```

#### Specify Synchronization Seconds
```sh
python charly.py --main_file "D:\\downloads\\[CR] VINLAND SAGA - S01E01 [1080p].mkv" --audio_file "D:\\downloads\\VINLAND SAGA_S01E01_Episodio 1.mkv" --seconds 16.2 --audio_delay advance --subtitle_source main
```

#### Use Time Difference Between Media Files
If `--seconds` is not provided, the script will use the difference in duration between the media files to determine the delay or advance.

Example:
```sh
python sync_media.py --main_file "D:\\downloads\\[CR] VINLAND SAGA - S01E01 [1080p].mkv" --audio_file "D:\\downloads\\VINLAND SAGA_S01E01_Episodio 1.mkv" --audio_delay advance --subtitle_source main
```

## Example Output
The script will output the synchronized video file at the specified location.

```sh
Output file saved as D:\downloads\Telegram Desktop\[CR] VINLAND SAGA - S01E01 [1080p]_edited.mkv
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements
- [FFmpeg](https://ffmpeg.org/)
- [librosa](https://librosa.org/)
- [numpy](https://numpy.org/)
- [scipy](https://scipy.org/)
- [tqdm](https://tqdm.github.io/)
```
