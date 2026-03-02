#!/usr/bin/env python3
"""Rich-based UI Enhancement utilities for Canvas CLI"""

from datetime import datetime
from typing import Optional, List, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.align import Align

class RichStyler:
    """Helper class for styling CLI output using Rich"""

    console = Console()

    @staticmethod
    def success(msg: str) -> None:
        """Display success message with green color and checkmark"""
        RichStyler.console.print(f"✅ {msg}", style="green")

    @staticmethod
    def error(msg: str) -> None:
        """Display error message with red color and X mark"""
        RichStyler.console.print(f"✗ Error: {msg}", style="red bold")

    @staticmethod
    def info(msg: str) -> None:
        """Display info message with cyan color"""
        RichStyler.console.print(msg, style="cyan")

    @staticmethod
    def warning(msg: str) -> None:
        """Display warning message with yellow color and warning sign"""
        RichStyler.console.print(f"⚠ Warning: {msg}", style="yellow")

    @staticmethod
    def highlight(msg: str) -> Text:
        """Return highlighted text (white, bold)"""
        return Text(msg, style="white bold")

    @staticmethod
    def course_current(msg: str) -> Text:
        """Return formatted text for current course (green, bold)"""
        return Text(f"● {msg}", style="green bold")

    @staticmethod
    def boxed_text_single(text: str, width: int | None = None) -> Panel:
        """Draw text in a box using single lines"""
        if width is None:
            width = len(text) + 4

        total_len = max(len(text) + 4, width)
        header_text = text[:total_len]
        lspace_count = (total_len - len(header_text)) // 2 - 1
        rspace_count = total_len - len(header_text) - lspace_count - 1

        box_content = f"{' ' * lspace_count}{header_text}{' ' * rspace_count}"
        return Panel(
            Align.center(box_content, vertical="middle"),
            border_style="single",
            width=total_len + 2
        )

    @staticmethod
    def boxed_text_double(text: str, width: int | None = None) -> Panel:
        """Draw text in a box using double lines"""
        if width is None:
            width = len(text) + 4

        total_len = max(len(text) + 4, width)
        header_text = text[:total_len]
        lspace_count = (total_len - len(header_text)) // 2 - 1
        rspace_count = total_len - len(header_text) - lspace_count - 1

        box_content = f"{' ' * lspace_count}{header_text}{' ' * rspace_count}"
        return Panel(
            Align.center(box_content, vertical="middle"),
            border_style="double",
            width=total_len + 2
        )


class RichStatusBar:
    """Status bar manager for the CLI using Rich"""

    def __init__(self):
        self.last_operation = "Just started"
        self.connection_status = "Connected"

    def update_last_operation(self, operation: str) -> None:
        """Update the last operation timestamp"""
        self.last_operation = f"{operation} at {datetime.now().strftime('%H:%M:%S')}"

    def update_connection_status(self, status: str) -> None:
        """Update connection status"""
        self.connection_status = status

    def get_status_text(self, selected_course: Optional[dict] = None) -> Text:
        """Generate status bar text as Rich Text"""
        if selected_course:
            course_name = selected_course.get("name", "Unknown")
            if len(course_name) > 30:
                course_name = course_name[:27] + "..."
            course_text = f"📘 {course_name}"
            course_style = Text(course_text, style="blue")
        else:
            course_text = "❌ No course"
            course_style = Text(course_text, style="red")

        time_text = datetime.now().strftime("%H:%M:%S")

        # Combine all parts
        status_parts = [
            course_style,
            Text(f" | {self.connection_status}"),
            Text(f" | {self.last_operation}"),
            Text(f" | {time_text}", style="dim")
        ]

        return Text.assemble(*status_parts)

    def display(self, selected_course: Optional[dict] = None) -> None:
        """Display the status bar"""
        RichStyler.console.print(self.get_status_text(selected_course))


class RichTable:
    """Enhanced table formatter using Rich"""

    @staticmethod
    def format_header(title: str, width: int = 80) -> Panel:
        """Format a table header with title"""
        return Panel(
            Align.center(f"📚 {title}"),
            border_style="blue",
            width=width
        )

    @staticmethod
    def create_table(title: str = "", columns: List[str] = None,
                     rows: List[List[Any]] = None,
                     highlight_current: bool = False,
                     current_row_idx: int = -1) -> Table:
        """Create and populate a Rich table"""
        table = Table(title=f"📋 {title}" if title else None, expand=True)

        if columns:
            for i, col in enumerate(columns):
                # First column is typically ID, make it narrower
                if i == 0:
                    table.add_column(col, style="dim", width=10)
                else:
                    table.add_column(col, overflow="fold")

        if rows:
            for idx, row in enumerate(rows):
                style = None
                if highlight_current and idx == current_row_idx:
                    style = "green bold"

                formatted_row = []
                for i, cell in enumerate(row):
                    cell_str = str(cell)
                    # Truncate if too long
                    if len(cell_str) > 50 and i > 0:  # Don't truncate IDs
                        cell_str = cell_str[:47] + "..."
                    formatted_row.append(cell_str)

                table.add_row(*formatted_row, style=style)

        return table

    @staticmethod
    def display_table(table: Table) -> None:
        """Display a Rich table"""
        RichStyler.console.print(table)


class RichProgress:
    """Progress bar utilities using Rich"""

    def __init__(self):
        from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            RichStyler.console,
        )

    def __enter__(self):
        self.progress.__enter__()
        return self

    def __exit__(self, *args):
        self.progress.__exit__(*args)

    def add_task(self, description: str, total: int = 100):
        """Add a new progress task"""
        return self.progress.add_task(description, total=total)

    def update(self, task_id, advance: int = 1):
        """Update progress for a task"""
        self.progress.update(task_id, advance=advance)


if __name__ == "__main__":
    # Demo of Rich UI components
    print("=== Rich UI Components Demo ===\n")

    # Basic styling
    RichStyler.success("This is a success message")
    RichStyler.error("This is an error message")
    RichStyler.info("This is an info message")
    RichStyler.warning("This is a warning message")

    print()  # Blank line

    # Status bar
    status_bar = RichStatusBar()
    status_bar.update_connection_status("Connected to Canvas")
    status_bar.update_last_operation("Loaded courses")
    status_bar.display({"name": "Introduction to Computer Science"})

    print()  # Blank line

    # Boxed text
    RichStyler.console.print(RichStyler.boxed_text_single("Single Line Box"))
    RichStyler.console.print()
    RichStyler.console.print(RichStyler.boxed_text_double("Double Line Box"))

    print()  # Blank line

    # Table
    table = RichTable.create_table(
        title="Sample Course List",
        columns=["ID", "Course Name", "Code", "Term"],
        rows=[
            ["12345", "Introduction to Programming", "CS101", "Fall 2024"],
            ["67890", "Advanced Algorithms", "CS501", "Fall 2024"],
            ["11111", "This is a very long course name that will be truncated", "CS999", "Spring 2025"]
        ],
        highlight_current=True,
        current_row_idx=1
    )
    RichTable.display_table(table)
