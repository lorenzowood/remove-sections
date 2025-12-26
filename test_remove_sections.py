#!/usr/bin/env python3
"""
Tests for remove-sections script.
"""

import pytest
import sys
import os
import tempfile

# Import functions from remove-sections
sys.path.insert(0, os.path.dirname(__file__))
from remove_sections import parse_timestamp, parse_section, coalesce_sections, parse_sections_file


class TestParseTimestamp:
    """Test timestamp parsing."""

    def test_seconds_only(self):
        assert parse_timestamp("90.5") == 90.5
        assert parse_timestamp("0") == 0.0
        assert parse_timestamp("120") == 120.0

    def test_minutes_seconds(self):
        assert parse_timestamp("5:18.5") == 318.5
        assert parse_timestamp("1:30") == 90.0
        assert parse_timestamp("0:10") == 10.0

    def test_hours_minutes_seconds(self):
        assert parse_timestamp("1:05:30") == 3930.0
        assert parse_timestamp("0:05:18.5") == 318.5
        assert parse_timestamp("2:00:00") == 7200.0

    def test_empty_string(self):
        assert parse_timestamp("") is None
        assert parse_timestamp(None) is None


class TestParseSection:
    """Test section range parsing."""

    def test_full_range(self):
        assert parse_section("5:18.5-7:00.7") == (318.5, 420.7)
        assert parse_section("0:00-0:10") == (0.0, 10.0)

    def test_omitted_start(self):
        assert parse_section("-0:10") == (None, 10.0)
        assert parse_section("-120") == (None, 120.0)

    def test_omitted_end(self):
        assert parse_section("15:22-") == (922.0, None)
        assert parse_section("90.5-") == (90.5, None)

    def test_seconds_only_range(self):
        assert parse_section("10-20") == (10.0, 20.0)
        assert parse_section("5.5-10.7") == (5.5, 10.7)


class TestCoalesceSections:
    """Test section coalescing/merging."""

    def test_no_overlap(self):
        sections = [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]
        result = coalesce_sections(sections)
        assert result == [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]

    def test_overlapping(self):
        sections = [(10.0, 25.0), (20.0, 35.0)]
        result = coalesce_sections(sections)
        assert result == [(10.0, 35.0)]

    def test_multiple_overlaps(self):
        sections = [(10.0, 20.0), (15.0, 25.0), (22.0, 30.0)]
        result = coalesce_sections(sections)
        assert result == [(10.0, 30.0)]

    def test_adjacent_sections(self):
        sections = [(10.0, 20.0), (20.0, 30.0)]
        result = coalesce_sections(sections)
        assert result == [(10.0, 30.0)]

    def test_unsorted_input(self):
        sections = [(30.0, 40.0), (10.0, 20.0), (15.0, 25.0)]
        result = coalesce_sections(sections)
        assert result == [(10.0, 25.0), (30.0, 40.0)]

    def test_contained_section(self):
        sections = [(10.0, 50.0), (20.0, 30.0)]
        result = coalesce_sections(sections)
        assert result == [(10.0, 50.0)]

    def test_empty_list(self):
        assert coalesce_sections([]) == []

    def test_single_section(self):
        assert coalesce_sections([(10.0, 20.0)]) == [(10.0, 20.0)]


class TestSegmentCalculation:
    """Test calculation of segments to keep."""

    def test_single_removal_middle(self):
        """Remove 10-20 from a 60 second video -> keep [0-10, 20-60]"""
        duration = 60.0
        sections_to_remove = [(10.0, 20.0)]

        segments_to_keep = []
        last_end = 0.0
        for start, end in sections_to_remove:
            if last_end < start:
                segments_to_keep.append((last_end, start))
            last_end = end
        if last_end < duration:
            segments_to_keep.append((last_end, duration))

        assert segments_to_keep == [(0.0, 10.0), (20.0, 60.0)]

    def test_multiple_removals(self):
        """Remove 10-20 and 30-40 from a 60 second video -> keep [0-10, 20-30, 40-60]"""
        duration = 60.0
        sections_to_remove = [(10.0, 20.0), (30.0, 40.0)]

        segments_to_keep = []
        last_end = 0.0
        for start, end in sections_to_remove:
            if last_end < start:
                segments_to_keep.append((last_end, start))
            last_end = end
        if last_end < duration:
            segments_to_keep.append((last_end, duration))

        assert segments_to_keep == [(0.0, 10.0), (20.0, 30.0), (40.0, 60.0)]

    def test_removal_from_start(self):
        """Remove 0-10 from a 60 second video -> keep [10-60]"""
        duration = 60.0
        sections_to_remove = [(0.0, 10.0)]

        segments_to_keep = []
        last_end = 0.0
        for start, end in sections_to_remove:
            if last_end < start:
                segments_to_keep.append((last_end, start))
            last_end = end
        if last_end < duration:
            segments_to_keep.append((last_end, duration))

        assert segments_to_keep == [(10.0, 60.0)]

    def test_removal_to_end(self):
        """Remove 50-60 from a 60 second video -> keep [0-50]"""
        duration = 60.0
        sections_to_remove = [(50.0, 60.0)]

        segments_to_keep = []
        last_end = 0.0
        for start, end in sections_to_remove:
            if last_end < start:
                segments_to_keep.append((last_end, start))
            last_end = end
        if last_end < duration:
            segments_to_keep.append((last_end, duration))

        assert segments_to_keep == [(0.0, 50.0)]


class TestParseSectionsFile:
    """Test parsing sections from a file."""

    def test_simple_file(self):
        """Test parsing a simple file with sections."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("5:18.5-7:00.7\n")
            f.write("12:11.2-13:15\n")
            f.name_to_delete = f.name

        try:
            sections = parse_sections_file(f.name_to_delete)
            assert sections == [(318.5, 420.7), (731.2, 795.0)]
        finally:
            os.unlink(f.name_to_delete)

    def test_file_with_comments(self):
        """Test parsing a file with comments."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("# Remove ads\n")
            f.write("5:18.5-7:00.7\n")
            f.write("# Remove outro\n")
            f.write("45:30-\n")
            f.name_to_delete = f.name

        try:
            sections = parse_sections_file(f.name_to_delete)
            assert sections == [(318.5, 420.7), (2730.0, None)]
        finally:
            os.unlink(f.name_to_delete)

    def test_file_with_blank_lines(self):
        """Test parsing a file with blank lines."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("5:18.5-7:00.7\n")
            f.write("\n")
            f.write("   \n")
            f.write("12:11.2-13:15\n")
            f.name_to_delete = f.name

        try:
            sections = parse_sections_file(f.name_to_delete)
            assert sections == [(318.5, 420.7), (731.2, 795.0)]
        finally:
            os.unlink(f.name_to_delete)

    def test_file_with_mixed_content(self):
        """Test parsing a file with comments, blank lines, and sections."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("# Remove ads\n")
            f.write("5:18.5-7:00.7\n")
            f.write("\n")
            f.write("# Another ad\n")
            f.write("12:11.2-13:15\n")
            f.write("   \n")
            f.write("-0:10\n")
            f.write("# Remove outro\n")
            f.write("45:30-\n")
            f.name_to_delete = f.name

        try:
            sections = parse_sections_file(f.name_to_delete)
            assert sections == [(318.5, 420.7), (731.2, 795.0), (None, 10.0), (2730.0, None)]
        finally:
            os.unlink(f.name_to_delete)

    def test_file_with_invalid_line(self):
        """Test that invalid lines raise an error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("5:18.5-7:00.7\n")
            f.write("invalid line here\n")
            f.write("12:11.2-13:15\n")
            f.name_to_delete = f.name

        try:
            with pytest.raises(ValueError, match=r"Error in .* line 2"):
                parse_sections_file(f.name_to_delete)
        finally:
            os.unlink(f.name_to_delete)

    def test_empty_file(self):
        """Test parsing an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.name_to_delete = f.name

        try:
            sections = parse_sections_file(f.name_to_delete)
            assert sections == []
        finally:
            os.unlink(f.name_to_delete)

    def test_file_only_comments(self):
        """Test parsing a file with only comments."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("# Comment 1\n")
            f.write("# Comment 2\n")
            f.name_to_delete = f.name

        try:
            sections = parse_sections_file(f.name_to_delete)
            assert sections == []
        finally:
            os.unlink(f.name_to_delete)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
