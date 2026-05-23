"""
Claude Code Tmux Orchestrator
Uses Claude Code subscription via tmux instead of API rates.

Approach:
1. Claude Code runs in a tmux session
2. We send messages via tmux send-keys
3. Claude writes responses to a file
4. We read the response from the file
"""

import subprocess
import time
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


class ClaudeTmuxOrchestrator:
    """
    Orchestrate Claude Code running in a tmux session.
    Uses your Claude Code subscription instead of API rates.
    """

    SESSION_NAME = "lili_claude"
    RESPONSE_FILE = Path("/tmp/lili_claude_response.txt")
    READY_FILE = Path("/tmp/lili_claude_ready.txt")
    TMUX_PATH = "/opt/homebrew/bin/tmux"  # Full path for subprocess

    def __init__(self):
        self.ready = False
        # Clean up old files
        self._cleanup_files()

    def _cleanup_files(self):
        """Remove old response files."""
        for f in [self.RESPONSE_FILE, self.READY_FILE]:
            if f.exists():
                f.unlink()

    def _run_cmd(self, cmd: str, capture=True, timeout=30) -> Optional[str]:
        """Run a shell command."""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=capture, text=True, timeout=timeout
            )
            return result.stdout.strip() if capture else None
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            print(f"Command error: {e}")
            return None

    def is_session_running(self) -> bool:
        """Check if the tmux session exists."""
        result = self._run_cmd(f"{self.TMUX_PATH} has-session -t {self.SESSION_NAME} 2>/dev/null && echo 'yes' || echo 'no'")
        return result == "yes"

    def start_session(self) -> bool:
        """Start Claude Code in a tmux session."""
        if self.is_session_running():
            print(f"[Lili] Session {self.SESSION_NAME} already running")
            self.ready = True
            return True

        print(f"[Lili] Starting Claude Code session: {self.SESSION_NAME}")

        # Create tmux session with Claude Code
        cmd = f"{self.TMUX_PATH} new-session -d -s {self.SESSION_NAME} 'claude --dangerously-skip-permissions'"
        self._run_cmd(cmd, capture=False)

        # Wait for permission dialog to appear
        time.sleep(3)

        if not self.is_session_running():
            print("[Lili] Failed to create tmux session")
            return False

        # Accept the bypass permissions dialog
        # Navigate to "Yes, I accept" (option 2) and press Enter
        print("[Lili] Accepting bypass permissions dialog...")
        self._run_cmd(f"{self.TMUX_PATH} send-keys -t {self.SESSION_NAME} Down", capture=False)
        time.sleep(0.3)
        self._run_cmd(f"{self.TMUX_PATH} send-keys -t {self.SESSION_NAME} Enter", capture=False)

        # Wait for Claude to fully initialize
        time.sleep(5)

        if self.is_session_running():
            self.ready = True
            print(f"[Lili] Claude Code session ready")
            return True

        print("[Lili] Session closed unexpectedly")
        return False

    def _send_init_instructions(self):
        """Send initial instructions to Claude about how to respond."""
        init_msg = """From now on, when I ask you questions, please write your complete response to the file /tmp/lili_claude_response.txt using the Write tool. After writing, create an empty file at /tmp/lili_claude_ready.txt to signal you're done. Keep responses concise but helpful. Acknowledge with 'Ready'."""

        self._send_keys(init_msg)
        time.sleep(5)  # Wait for Claude to process

    def _send_keys(self, text: str, submit: bool = True):
        """Send text to the tmux session."""
        # For multiline text, we need to send it carefully
        # First escape single quotes
        escaped = text.replace("'", "'\\''")
        # Replace newlines with spaces for single-line input
        escaped = escaped.replace('\n', ' ')

        # Send the text
        cmd = f"{self.TMUX_PATH} send-keys -t {self.SESSION_NAME} -- '{escaped}'"
        self._run_cmd(cmd, capture=False)

        # Submit with Enter if requested
        if submit:
            time.sleep(0.2)
            self._run_cmd(f"{self.TMUX_PATH} send-keys -t {self.SESSION_NAME} Enter", capture=False)

    def stop_session(self):
        """Stop the tmux session."""
        if self.is_session_running():
            self._run_cmd(f"{self.TMUX_PATH} kill-session -t {self.SESSION_NAME}")
            self.ready = False
            self._cleanup_files()
            print(f"[Lili] Stopped session: {self.SESSION_NAME}")

    def send_message(self, message: str, timeout: int = 90) -> Optional[str]:
        """Send a message to Claude Code and get the response."""
        if not self.is_session_running():
            if not self.start_session():
                return "Sorry, I couldn't start the AI session. Please try again."

        # Clean up previous response
        self._cleanup_files()

        # Send the message with instructions to write response to file
        prompt = f"""Please answer this question and write your COMPLETE response to /tmp/lili_claude_response.txt, then touch /tmp/lili_claude_ready.txt when done:

{message}"""

        self._send_keys(prompt)

        # Wait for response
        response = self._wait_for_response(timeout)

        if response:
            return response

        # Fallback: try to capture from pane
        return self._capture_from_pane()

    def _wait_for_response(self, timeout: int) -> Optional[str]:
        """Wait for Claude to write response to file."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if ready signal exists
            if self.READY_FILE.exists():
                # Read the response
                if self.RESPONSE_FILE.exists():
                    try:
                        response = self.RESPONSE_FILE.read_text().strip()
                        if response:
                            return response
                    except:
                        pass

            # Also check if response file has content (in case ready file wasn't created)
            if self.RESPONSE_FILE.exists():
                try:
                    content = self.RESPONSE_FILE.read_text().strip()
                    if content and len(content) > 50:  # Substantial response
                        # Wait a bit more to ensure it's complete
                        time.sleep(2)
                        return self.RESPONSE_FILE.read_text().strip()
                except:
                    pass

            time.sleep(1)

        return None

    def _capture_from_pane(self) -> Optional[str]:
        """Fallback: capture response from tmux pane."""
        content = self._run_cmd(
            f"{self.TMUX_PATH} capture-pane -t {self.SESSION_NAME} -p -S -100"
        )

        if not content:
            return None

        # Try to extract the last response
        lines = content.split('\n')
        response_lines = []
        capture = False

        for line in lines:
            # Skip empty lines and prompts
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('❯') or stripped.startswith('>'):
                capture = False
                continue
            if 'Please answer' in line or 'write your COMPLETE' in line:
                capture = True
                response_lines = []
                continue
            if capture:
                response_lines.append(line)

        if response_lines:
            return '\n'.join(response_lines[-30:])  # Last 30 lines

        return "I processed your request but couldn't capture the response. Please try again."

    def get_status(self) -> dict:
        """Get orchestrator status."""
        running = self.is_session_running()
        return {
            "session_name": self.SESSION_NAME,
            "running": running,
            "ready": self.ready and running,
            "provider": "Claude Code (Subscription)",
            "response_file": str(self.RESPONSE_FILE)
        }


# Global instance
claude_tmux = ClaudeTmuxOrchestrator()


if __name__ == "__main__":
    print("Testing Claude Tmux Orchestrator...")
    print(f"Status: {claude_tmux.get_status()}")

    if claude_tmux.start_session():
        print("\nSending test message...")
        response = claude_tmux.send_message("What is 2+2? Answer in one sentence.")
        print(f"\nResponse: {response}")

        print("\nSending finance question...")
        response = claude_tmux.send_message("What's a good P/E ratio for growth stocks?")
        print(f"\nResponse: {response}")
