#!/usr/bin/env python3
"""UI Enhancement utilities for Canvas CLI"""

from cmd2 import ansi
from datetime import datetime
import textwrap

class CLIStyler:
    """Helper class for styling CLI output"""

    @staticmethod
    def success(msg: str) -> str:
        return ansi.style(f"✅ {msg}", fg=ansi.Fg.GREEN)

    @staticmethod
    def error(msg: str) -> str:
        return ansi.style(f"✗ Error: {msg}", fg=ansi.Fg.RED)

    @staticmethod
    def info(msg: str) -> str:
        return ansi.style(f"{msg}", fg=ansi.Fg.CYAN)

    @staticmethod
    def warning(msg: str) -> str:
        return ansi.style(f"⚠ Warning: {msg}", fg=ansi.Fg.YELLOW)

    @staticmethod
    def highlight(msg: str) -> str:
        return ansi.style(msg, fg=ansi.Fg.BRIGHT_WHITE, bold=True)

    @staticmethod
    def course_current(msg: str) -> str:
        return ansi.style(f"● {msg}", fg=ansi.Fg.GREEN, bold=True)
    
    @staticmethod
    def boxed_text_single(text: str, width: int | None = None) -> str:
        """Draw text in a box using single lines"""

        if width is None:
            width = len(text) + 4

        total_len = max(len(text) + 4, width)

        header_text = f"{text[:total_len]}"
        lspace_count = (total_len - len(header_text)) // 2 - 1
        rspace_count = total_len - len(header_text) - lspace_count - 1

        b_text = f"""
            ┌{'─' * total_len}┐
            │{' ' * lspace_count}{header_text}{' ' * rspace_count}│
            └{'─' * total_len}┘
            """
        
        return textwrap.dedent(b_text)

    @staticmethod
    def boxed_text_double(text: str, width: int | None = None) -> str:
        """Draw text in a box using double lines"""

        if width is None:
            width = len(text) + 4

        total_len = max(len(text) + 4, width)

        header_text = f"{text[:total_len]}"
        lspace_count = (total_len - len(header_text)) // 2 - 1
        rspace_count = total_len - len(header_text) - lspace_count - 1

        b_text = f"""
            ╔{'═' * total_len}╗
            ║{' ' * lspace_count}{header_text}{' ' * rspace_count}║
            ╚{'═' * total_len}╝
            """

        return textwrap.dedent(b_text)

class StatusBar:
    """Status bar manager for the CLI"""

    def __init__(self, cli):
        self.cli = cli
        self.last_operation = 'Just started'
        self.connection_status = 'Connected'

    def update_last_operation(self, operation: str):
        """Update the last operation timestamp"""
        self.last_operation = f"{operation} at {datetime.now().strftime('%H:%M:%S')}"

    def update_connection_status(self, status: str):
        """Update connection status"""
        self.connection_status = status

    def get_status_text(self, selected_course=None):
        """Generate status bar text"""
        if selected_course:
            course_name = selected_course['name']
            if len(course_name) > 30:
                course_name = course_name[:27] + "..."
            course_text = f"📘 {course_name}"
        else:
            course_text = "❌ No course"

        time_text = datetime.now().strftime('%H:%M:%S')

        # Simple status line
        status_line = f"{course_text} | {self.connection_status} | {self.last_operation} | {time_text}"
        return status_line

class TableFormatter:
    """Helper for formatting tables in CLI output"""

    @staticmethod
    def format_header(title: str, width: int = 80):
        separator = '═' * width
        return f"{ansi.style(separator, fg=ansi.Fg.BLUE)}\n{ansi.style(f'📚 {title}', fg=ansi.Fg.BRIGHT_WHITE, bold=True)}\n{ansi.style(separator, fg=ansi.Fg.BLUE)}"

    @staticmethod
    def format_row(*columns, widths=None, current: bool = False):
        if widths is None:
            widths = [len(col) for col in columns]

        formatted_cols = []
        for col, width in zip(columns, widths):
            col_str = str(col)
            if len(col_str) > width - 1:
                col_str = col_str[:width-4] + '...'
            formatted_cols.append(f"{col_str:<{width}}")

        row = ' '.join(formatted_cols)
        if current:
            return ansi.style(f"● {row}", fg=ansi.Fg.GREEN)
        return f"  {row}"

    @staticmethod
    def format_table_divider(width: int = 80):
        return ansi.style(f"{'─' * width}", fg=ansi.Fg.BRIGHT_BLACK)