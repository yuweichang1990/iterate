#!/usr/bin/env python
"""
Tests for the tag extraction logic used in stop-hook.sh.

The stop hook extracts <explore-next> and <explore-done> tags from
the last assistant message. This test validates the Python regex logic
that performs the extraction, including edge cases.
"""

import json
import re
import unittest


def extract_tags(text, sep="\x1f"):
    """
    Replicate the exact Python logic from stop-hook.sh for testing.
    Returns (done, next_t) tuple.
    """
    done = next_t = ""
    done_match = re.search(r"<explore-done>(.*?)</explore-done>", text, re.DOTALL)
    if done_match:
        done = re.sub(r"\s+", " ", done_match.group(1).strip())
    next_match = re.search(r"<explore-next>(.*?)</explore-next>", text, re.DOTALL)
    if next_match:
        next_t = re.sub(r"\s+", " ", next_match.group(1).strip())
    return done, next_t


def simulate_bash_read(output_str, sep="\x1f"):
    """
    Simulate `IFS="$SEP" read -r EXPLORE_DONE NEXT_SUBTOPIC <<< "$TAGS"`

    With non-whitespace IFS, bash read splits correctly even when first field is empty.
    With tab IFS, bash read would strip leading tabs (the original bug).
    """
    parts = output_str.split(sep, 1)
    explore_done = parts[0] if len(parts) > 0 else ""
    next_subtopic = parts[1] if len(parts) > 1 else ""
    return explore_done, next_subtopic


class TestTagExtraction(unittest.TestCase):
    """Test the core tag extraction regex."""

    def test_explore_next_only(self):
        text = "Some analysis here.\n<explore-next>Add per-node timing</explore-next>"
        done, next_t = extract_tags(text)
        self.assertEqual(done, "")
        self.assertEqual(next_t, "Add per-node timing")

    def test_explore_done_only(self):
        text = "All done.\n<explore-done>Core task complete. No further improvements.</explore-done>"
        done, next_t = extract_tags(text)
        self.assertEqual(done, "Core task complete. No further improvements.")
        self.assertEqual(next_t, "")

    def test_both_tags(self):
        text = "<explore-done>Finished</explore-done>\n<explore-next>Next step</explore-next>"
        done, next_t = extract_tags(text)
        self.assertEqual(done, "Finished")
        self.assertEqual(next_t, "Next step")

    def test_no_tags(self):
        text = "Just some regular text with no tags."
        done, next_t = extract_tags(text)
        self.assertEqual(done, "")
        self.assertEqual(next_t, "")

    def test_multiline_content(self):
        text = "<explore-next>Research\n  deeper aspects\n  of the topic</explore-next>"
        done, next_t = extract_tags(text)
        self.assertEqual(next_t, "Research deeper aspects of the topic")

    def test_whitespace_normalization(self):
        text = "<explore-next>  lots   of    spaces  </explore-next>"
        done, next_t = extract_tags(text)
        self.assertEqual(next_t, "lots of spaces")

    def test_tags_in_long_response(self):
        text = "# Analysis\n\nLong discussion...\n" * 50
        text += "\n<explore-next>Memory safety patterns</explore-next>\n"
        done, next_t = extract_tags(text)
        self.assertEqual(next_t, "Memory safety patterns")


class TestUnitSeparatorProtocol(unittest.TestCase):
    """
    Test the full pipeline: extract_tags → format with separator → bash read simulation.
    This validates the fix for developer_guide.md Problem 4 (IFS tab bug).
    """

    def test_next_only_with_unit_sep(self):
        """The exact scenario that triggered the original bug."""
        text = "<explore-next>Add per-node timing</explore-next>"
        done, next_t = extract_tags(text)
        output = done + "\x1f" + next_t

        explore_done, next_subtopic = simulate_bash_read(output)
        self.assertEqual(explore_done, "")
        self.assertEqual(next_subtopic, "Add per-node timing")

    def test_next_only_with_tab_shows_bug(self):
        """Demonstrate the original bug with tab separator."""
        text = "<explore-next>Add per-node timing</explore-next>"
        done, next_t = extract_tags(text)
        output = done + "\t" + next_t  # Tab separator (the buggy version)

        # With tab, bash read strips leading tab, so first field gets the value
        # This simulates what bash actually does:
        # When IFS is whitespace, leading IFS chars are stripped
        parts = output.lstrip("\t").split("\t", 1)
        explore_done_buggy = parts[0]
        # BUG: "Add per-node timing" ends up in explore_done instead of next_subtopic!
        self.assertEqual(explore_done_buggy, "Add per-node timing")

    def test_done_only_with_unit_sep(self):
        text = "<explore-done>Task complete</explore-done>"
        done, next_t = extract_tags(text)
        output = done + "\x1f" + next_t

        explore_done, next_subtopic = simulate_bash_read(output)
        self.assertEqual(explore_done, "Task complete")
        self.assertEqual(next_subtopic, "")

    def test_both_tags_with_unit_sep(self):
        text = "<explore-done>Done</explore-done><explore-next>Enhance</explore-next>"
        done, next_t = extract_tags(text)
        output = done + "\x1f" + next_t

        explore_done, next_subtopic = simulate_bash_read(output)
        self.assertEqual(explore_done, "Done")
        self.assertEqual(next_subtopic, "Enhance")

    def test_empty_both_fields(self):
        text = "No tags here"
        done, next_t = extract_tags(text)
        output = done + "\x1f" + next_t

        explore_done, next_subtopic = simulate_bash_read(output)
        self.assertEqual(explore_done, "")
        self.assertEqual(next_subtopic, "")


class TestTranscriptParsing(unittest.TestCase):
    """Test parsing assistant messages from transcript JSONL."""

    def _make_transcript_line(self, text):
        return json.dumps({
            "role": "assistant",
            "message": {
                "content": [{"type": "text", "text": text}]
            }
        })

    def test_extract_from_jsonl(self):
        """Simulate the full pipeline: JSONL → extract text → extract tags."""
        line = self._make_transcript_line(
            "Analysis complete.\n<explore-next>Investigate error handling</explore-next>"
        )
        data = json.loads(line)
        content = data.get("message", {}).get("content", [])
        text = "\n".join(item["text"] for item in content if item.get("type") == "text")
        done, next_t = extract_tags(text)
        self.assertEqual(next_t, "Investigate error handling")

    def test_multi_content_blocks(self):
        line = json.dumps({
            "role": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Part 1 of response."},
                    {"type": "tool_use", "name": "Read"},
                    {"type": "text", "text": "Part 2.\n<explore-next>Next topic</explore-next>"},
                ]
            }
        })
        data = json.loads(line)
        content = data.get("message", {}).get("content", [])
        text = "\n".join(item["text"] for item in content if item.get("type") == "text")
        done, next_t = extract_tags(text)
        self.assertEqual(next_t, "Next topic")


if __name__ == "__main__":
    unittest.main()
