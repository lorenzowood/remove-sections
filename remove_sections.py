#!/usr/bin/env python3
"""
Remove sections from a video file without re-encoding.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional


def parse_timestamp(ts: str) -> Optional[float]:
    """Convert timestamp to seconds. Returns None if empty string."""
    if not ts or ts == '':
        return None

    # Just seconds (decimal)
    if ':' not in ts:
        return float(ts)

    # M:SS.S or H:MM:SS.S format
    parts = ts.split(':')
    if len(parts) == 2:  # M:SS.S
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    elif len(parts) == 3:  # H:MM:SS.S
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    else:
        raise ValueError(f"Invalid timestamp format: {ts}")


def parse_section(section: str) -> Tuple[Optional[float], Optional[float]]:
    """Parse a section range like '5:18.5-7:00.7' or '-0:10' or '15:22-'"""
    if '-' not in section:
        raise ValueError(f"Invalid section format (missing '-'): {section}")

    parts = section.split('-', 1)
    start_str = parts[0]
    end_str = parts[1] if len(parts) > 1 else ''

    start = parse_timestamp(start_str)
    end = parse_timestamp(end_str)

    return (start, end)


def coalesce_sections(sections: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Merge overlapping sections."""
    if not sections:
        return []

    # Sort by start time
    sections = sorted(sections)

    merged = [sections[0]]
    for current_start, current_end in sections[1:]:
        last_start, last_end = merged[-1]

        # If current section overlaps or is adjacent to last section
        if current_start <= last_end:
            # Merge them
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # Add as new section
            merged.append((current_start, current_end))

    return merged


def parse_sections_file(filepath: str) -> List[Tuple[Optional[float], Optional[float]]]:
    """Parse sections from a file.

    File format:
    - One section per line (START-END format)
    - Lines starting with # are comments
    - Blank lines (or whitespace-only) are ignored
    - Invalid lines raise ValueError
    """
    sections = []
    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            # Strip whitespace
            line = line.strip()

            # Skip blank lines
            if not line:
                continue

            # Skip comments
            if line.startswith('#'):
                continue

            # Try to parse as section
            try:
                section = parse_section(line)
                sections.append(section)
            except ValueError as e:
                raise ValueError(f"Error in {filepath} line {line_num}: {e}")

    return sections


def get_video_duration(input_file: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        input_file
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get video duration: {result.stderr}")
    return float(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(
        description='Remove sections from a video file without re-encoding'
    )
    parser.add_argument('input', help='Input video file')
    parser.add_argument('sections', nargs='*', help='Sections to remove (format: START-END)')
    parser.add_argument('-f', '--file', help='File containing sections to remove (one per line)')
    parser.add_argument('--preserve-intermediate-files', action='store_true',
                        help='Keep intermediate files')
    parser.add_argument('--strict', action='store_true',
                        help='Error if sections fall outside video duration')

    args = parser.parse_args()

    # Must have either sections or file
    if not args.sections and not args.file:
        parser.error("Must provide either sections or -f/--file")

    # Check if last argument is an output file (doesn't contain '-')
    output_file = None
    sections_args = args.sections if args.sections else []
    if sections_args and '-' not in sections_args[-1]:
        output_file = sections_args[-1]
        sections_args = sections_args[:-1]

    # Parse sections from command line
    sections = []
    for section_str in sections_args:
        start, end = parse_section(section_str)
        sections.append((start, end))

    # Parse sections from file if provided
    if args.file:
        file_sections = parse_sections_file(args.file)
        sections.extend(file_sections)

    # Get video duration
    duration = get_video_duration(args.input)

    # Resolve None values (start of file = 0, end of file = duration)
    resolved_sections = []
    for start, end in sections:
        start = start if start is not None else 0.0
        end = end if end is not None else duration

        # Validate in strict mode
        if args.strict:
            if start < 0 or end > duration:
                sys.stderr.write(f"Error: Section {start}-{end} falls outside video duration (0-{duration})\n")
                sys.exit(1)

        # Clip to video duration
        start = max(0, min(start, duration))
        end = max(0, min(end, duration))

        # Only add if valid range
        if start < end:
            resolved_sections.append((start, end))

    # Coalesce overlapping sections
    sections_to_remove = coalesce_sections(resolved_sections)

    # Calculate segments to keep
    segments_to_keep = []
    last_end = 0.0
    for start, end in sections_to_remove:
        if last_end < start:
            segments_to_keep.append((last_end, start))
        last_end = end

    # Add final segment if needed
    if last_end < duration:
        segments_to_keep.append((last_end, duration))

    # If no segments to keep, error
    if not segments_to_keep:
        sys.stderr.write("Error: All video content would be removed\n")
        sys.exit(1)

    # Generate output filename if not provided
    if output_file is None:
        input_path = Path(args.input)
        output_file = f"{input_path.stem}-sections-removed{input_path.suffix}"

    # Extract segments
    intermediate_files = []
    for i, (start, duration_seg) in enumerate(segments_to_keep):
        duration_val = duration_seg - start
        part_file = f"part{i:03d}.mkv"
        intermediate_files.append(part_file)

        cmd = [
            'ffmpeg',
            '-i', args.input,
            '-ss', str(start),
            '-t', str(duration_val),
            '-c', 'copy',
            '-y',
            part_file
        ]

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            sys.stderr.write(f"Error extracting segment {i}: {result.stderr.decode()}\n")
            sys.exit(1)

    # Create concat file
    concat_file = 'concat_list.txt'
    with open(concat_file, 'w') as f:
        for part_file in intermediate_files:
            f.write(f"file '{part_file}'\n")

    # Concatenate segments
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',
        '-y',
        output_file
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        sys.stderr.write(f"Error concatenating segments: {result.stderr.decode()}\n")
        sys.exit(1)

    # Clean up intermediate files
    if not args.preserve_intermediate_files:
        for part_file in intermediate_files:
            os.remove(part_file)
        os.remove(concat_file)

    print(f"Created {output_file}")


if __name__ == '__main__':
    main()
