# remove-sections

A command-line tool to remove sections from video files without re-encoding. Perfect for clipping ads out of recorded TV shows or removing unwanted segments from any video.

## Features

- **No re-encoding**: Uses ffmpeg's stream copy to maintain original quality
- **Flexible timestamp formats**: Support for seconds (`90.5`), minutes:seconds (`5:18.5`), or hours:minutes:seconds (`1:05:30`)
- **Multiple sections**: Remove multiple segments in a single command
- **File input**: Read sections from a file with `-f` flag
- **Smart merging**: Automatically coalesces overlapping sections
- **Partial ranges**: Omit start (`-0:10`) or end (`15:22-`) timestamps
- **Strict mode**: Optional validation for out-of-bounds sections
- **Any format**: Works with any video format supported by ffmpeg (MKV, MP4, AVI, MOV, etc.)

## Installation

```bash
pip install remove-sections
```

Or install from source:

```bash
git clone https://github.com/lorenzowood/remove-sections.git
cd remove-sections
pip install -e .
```

## Requirements

- Python 3.11+
- ffmpeg (must be installed and available in PATH)

## Usage

```bash
remove-sections <input_file> <section1> [section2 ...] [output_file] [options]
```

### Basic Examples

Remove a single section (5:18.5 to 7:00.7):
```bash
remove-sections programme.mkv 5:18.5-7:00.7
# Creates: programme-sections-removed.mkv
```

Remove multiple sections:
```bash
remove-sections programme.mkv 5:18.5-7:00.7 12:11.2-13:15
```

Specify output filename:
```bash
remove-sections input.mp4 1:30-2:45 output.mp4
```

Remove from start:
```bash
remove-sections programme.mkv -0:10
# or
remove-sections programme.mkv 0:00-0:10
```

Remove to end:
```bash
remove-sections programme.mkv 15:22-
```

### Using a Sections File

Create a text file with one section per line:

**sections.txt:**
```
# Remove ads
5:18.5-7:00.7
12:11.2-13:15

# Remove outro
45:30-
```

Then use it with the `-f` flag:
```bash
remove-sections programme.mkv -f sections.txt
# Creates: programme-sections-removed.mkv
```

Specify output filename:
```bash
remove-sections input.mp4 -f sections.txt output.mp4
```

Combine file sections with command-line sections:
```bash
remove-sections input.mp4 -f sections.txt 10:00-11:00 output.mp4
```

**File format:**
- One section per line (START-END format)
- Lines starting with `#` are comments
- Blank lines are ignored
- Invalid lines will cause an error

### Timestamp Formats

All of these formats are supported:

- Seconds only: `90.5`, `120`
- Minutes:seconds: `5:18.5`, `1:30`
- Hours:minutes:seconds: `1:05:30`, `0:05:18.5`

### Options

- `-f`, `--file <filename>`: Read sections from a file (one section per line)
- `--strict`: Error if any section falls outside the video duration (default: clips to video length)
- `--preserve-intermediate-files`: Keep intermediate part files after processing

### Examples with Options

Strict mode (fails if timestamps are invalid):
```bash
remove-sections video.mkv 5:00-6:00 --strict
```

Keep intermediate files for inspection:
```bash
remove-sections video.mkv 1:00-2:00 3:00-4:00 --preserve-intermediate-files
```

### Important Notes

- **All timestamps are relative to the original file**: The order of sections doesn't matter
- **Overlapping sections merge automatically**: `4:00-5:00 4:57-6:00` becomes `4:00-6:00`
- **Default behavior clips to video length**: Removing `4:54-8:20` from a 5-minute video removes `4:54-5:00`
- **No changes = copy**: If all sections fall outside the video, output equals input

## How It Works

The tool:
1. Parses the sections to remove and merges any overlaps
2. Calculates the segments to keep (inverse of removed sections)
3. Extracts each segment using ffmpeg with stream copy (`-c copy`)
4. Concatenates the segments using ffmpeg's concat demuxer
5. Cleans up intermediate files (unless `--preserve-intermediate-files` is set)

## Development

Run tests:
```bash
pytest test_remove_sections.py -v
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or pull request on GitHub.

## Author

Lorenzo Wood
