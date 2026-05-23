"""
Claude Code Tmux Orchestrator
Uses Claude Code subscription via tmux instead of API rates.
"""

import subprocess
import time
import os
import re
from typing import Optional
from pathlib import Path


class ClaudeTmuxOrchestrator:
    """
    Orchestrate Claude Code running in a tmux session.
    This uses your Claude Code subscription instead of API rates.
    """

    SESSION_NAME = "claude_lili"
    OUTPUT_FILE = "/tmp/claude_lili_output.txt"
    MARKER_START = "<<<LILI_RESPONSE_START>>>"
    MARKER_END = "<<<LILI_RESPONSE_END>>>"

    def __init__(self):
        self.ready = False

    def _run_cmd(self, cmd: str, capture=True) -> Optional[str]:
        """Run a shell command."""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=capture, text=True, timeout=30
            )
            return result.stdout.strip() if capture else None
        except Exception as e:
            print(f"Command error: {e}")
            return None

    def is_session_running(self) -> bool:
        """Check if the tmux session exists."""
        result = self._run_cmd(f"tmux has-session -t {self.SESSION_NAME} 2>/dev/null && echo 'yes' || echo 'no'")
        return result == "yes"

    def start_session(self) -> bool:
        """Start Claude Code in a tmux session."""
        if self.is_session_running():
            print(f"Session {self.SESSION_NAME} already running")
            self.ready = True
            return True

        # Create new tmux session with Claude Code
        # Using -d to start detached
        cmd = f"tmux new-session -d -s {self.SESSION_NAME} 'claude --dangerously-skip-permissions'"
        self._run_cmd(cmd, capture=False)

        # Wait for Claude to initialize
        time.sleep(3)

        if self.is_session_running():
            print(f"Started Claude Code session: {self.SESSION_NAME}")
            self.ready = True
            return True

        print("Failed to start Claude Code session")
        return False

    def stop_session(self):
        """Stop the tmux session."""
        if self.is_session_running():
            self._run_cmd(f"tmux kill-session -t {self.SESSION_NAME}")
            self.ready = False
            print(f"Stopped session: {self.SESSION_NAME}")

    def send_message(self, message: str, timeout: int = 60) -> Optional[str]:
        """
        Send a message to Claude Code and get the response.
        """
        if not self.is_session_running():
            if not self.start_session():
                return None

        # Clear any previous output
        self._run_cmd(f"tmux send-keys -t {self.SESSION_NAME} C-c")
        time.sleep(0.5)

        # Wrap message with markers for extraction
        wrapped_message = f"""Please respond to this user question. Start your response with exactly "{self.MARKER_START}" and end with exactly "{self.MARKER_END}":

{message}"""

        # Escape special characters for tmux
        escaped_msg = wrapped_message.replace("'", "'\\''")

        # Send the message
        # Using tmux send-keys with the message
        self._run_cmd(f"tmux send-keys -t {self.SESSION_NAME} '{escaped_msg}' Enter")

        # Wait for response and capture
        response = self._wait_for_response(timeout)

        return response

    def _wait_for_response(self, timeout: int) -> Optional[str]:
        """Wait for Claude to respond and capture the output."""
        start_time = time.time()
        last_content = ""
        stable_count = 0

        while time.time() - start_time < timeout:
            # Capture pane content
            content = self._run_cmd(
                f"tmux capture-pane -t {self.SESSION_NAME} -p -S -500"
            )

            if content:
                # Check if response is complete (content stopped changing)
                if content == last_content:
                    stable_count += 1
                    if stable_count >= 3:  # Content stable for 3 checks
                        # Try to extract response between markers
                        response = self._extract_response(content)
                        if response:
                            return response
                        # If no markers, return the last portion
                        return self._extract_last_response(content)
                else:
                    stable_count = 0
                    last_content = content

            time.sleep(1)

        return None

    def _extract_response(self, content: str) -> Optional[str]:
        """Extract response between markers."""
        if self.MARKER_START in content and self.MARKER_END in content:
            start = content.find(self.MARKER_START) + len(self.MARKER_START)
            end = content.find(self.MARKER_END)
            if start < end:
                return content[start:end].strip()
        return None

    def _extract_last_response(self, content: str) -> str:
        """Extract the last response from pane content."""
        # Split by common Claude response patterns
        lines = content.split('\n')

        # Find the last substantial block of text
        # Skip empty lines and prompts
        response_lines = []
        in_response = False

        for line in reversed(lines):
            stripped = line.strip()

            # Skip empty lines at the end
            if not stripped and not response_lines:
                continue

            # Stop at user input indicators
            if stripped.startswith('❯') or stripped.startswith('>'):
                break

            response_lines.insert(0, line)

            # Stop if we have enough content
            if len(response_lines) > 50:
                break

        return '\n'.join(response_lines).strip()

    def get_status(self) -> dict:
        """Get orchestrator status."""
        running = self.is_session_running()
        return {
            "session_name": self.SESSION_NAME,
            "running": running,
            "ready": running,
            "provider": "Claude Code (Subscription)"
        }


# Global instance
claude_tmux = ClaudeTmuxOrchestrator()


# Quick test
if __name__ == "__main__":
    print("Testing Claude Tmux Orchestrator...")
    print(f"Status: {claude_tmux.get_status()}")

    if claude_tmux.start_session():
        print("Session started!")
        response = claude_tmux.send_message("What is 2+2? Answer briefly.")
        print(f"Response: {response}")
