#!/usr/bin/env python3
"""
CanvasCLI - Command Line Interface for Canvas LMS

This is the main entry point for the CLI using prompt_toolkit and Rich.
"""

import shlex
import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import NestedCompleter, PathCompleter
from prompt_toolkit.styles import Style

from canvascli.cli.ui import RichStyler, RichStatusBar
from canvascli.cli.cmd_handler import CanvasCLICommandHandler
from canvascli.config import CANVAS_CONFIG


class REPLArgumentParser(argparse.ArgumentParser):
    """Custom ArgumentParser that raises exceptions instead of exiting"""

    def error(self, message):
        raise ValueError(message)

    def exit(self, status=0, message=None):
        if message:
            raise ValueError(message)
        raise ValueError("Exit")


# Global command registry
COMMANDS: Dict[str, Dict[str, Any]] = {}


def command(name: str, parser: Optional[REPLArgumentParser] = None):
    """Decorator to register a command"""
    def decorator(func):
        COMMANDS[name] = {"func": func, "parser": parser}
        return func
    return decorator


class CanvasCLIRich:
    """Main CLI class using Rich and prompt_toolkit"""

    def __init__(self):
        self.console = Console()
        self.history_file = os.path.expanduser('~/.canvas_cli_history')
        self.session = PromptSession(
            history=FileHistory(self.history_file),
        )
        self.command_handler = CanvasCLICommandHandler(self)
        self.status_bar = RichStatusBar()
        self.setup_completer()
        self.setup_prompt()
        self.setup_bottom_toolbar()

    def setup_completer(self):
        """Setup the auto-completion system"""
        cli_grammar = {
            "status": None,
            "exit": None,
            "quit": None,
            "ls": {
                "courses": {
                    "--name": None,
                    "-n": None,
                    "--code": None,
                    "-c": None,
                    "-i": None,
                    "--ignore-case": None,
                    "--refresh": None,
                },
                "folders": None,
            },
            "use": {
                "course": None,
            },
            "show": {
                "assignments": None,
                "students": None,
                "quizzes": None,
                "assignment": None,
                "quiz": None,
            },
            "download": {
                "students": {
                    "--file": PathCompleter(),
                    "-f": PathCompleter(),
                },
                "assignment": {
                    "grades": {
                        "--file": PathCompleter(),
                        "-f": PathCompleter(),
                    },
                    "submissions": {
                        "--dir": PathCompleter(),
                        "-d": PathCompleter(),
                    },
                },
                "quiz": {
                    "questions": {
                        "--file": PathCompleter(),
                        "-f": PathCompleter(),
                        "--markdown": None,
                        "-m": None,
                    },
                    "submissions": {
                        "--dir": PathCompleter(),
                        "-d": PathCompleter(),
                        "--markdown": None,
                        "-m": None,
                    },
                },
            },
            "upload": {
                "assignment": {
                    "grades": {
                        "--file": PathCompleter(),
                        "-f": PathCompleter(),
                        "--root-dir": PathCompleter(),
                        "-r": PathCompleter(),
                    },
                },
            },
            "create": {
                "assignment": {
                    "--points": None,
                    "-p": None,
                    "--due-date": None,
                    "-d": None,
                    "--description": None,
                    "--desc": None,
                    "--published": None,
                },
            },
            "delete": {
                "assignment": None,
            },
        }

        self.completer = NestedCompleter.from_nested_dict(cli_grammar)

    def setup_prompt(self):
        """Setup the prompt text with current course context"""
        pass  # Will be updated dynamically

    def get_prompt_text(self) -> str:
        """Generate the prompt text - now simplified since course is in status bar"""
        return "canvas> "

    def setup_bottom_toolbar(self):
        """Setup the bottom toolbar (status bar)"""
        self.bottom_toolbar = self._get_status_bar_text

    def _get_status_bar_text(self):
        """Generate the status bar text for display at bottom"""
        from prompt_toolkit.formatted_text import HTML

        if self.command_handler.selected_course:
            course = self.command_handler.selected_course
            course_name = course['name']
            if len(course_name) > 40:  # Truncate if too long for status bar
                course_name = course_name[:37] + "..."
            status_text = f"📘 {course_name} | {self.status_bar.connection_status} | {self.status_bar.last_operation}"
        else:
            status_text = f"❌ No course selected | {self.status_bar.connection_status} | {self.status_bar.last_operation}"

        # Add time
        from datetime import datetime
        time_text = datetime.now().strftime("%H:%M:%S")
        full_status = f"{status_text} | {time_text}"

        # Return as HTML formatted text (prompt_toolkit expects this format)
        return HTML(f'<style bg="#2e3440" fg="#d8dee9">{full_status}</style>')

    def display_intro(self):
        """Display the welcome banner"""
        intro_text = f"""
╔══════════════════════════════════════════════════════════════╗
║                  🎓 Canvas LMS Command Center                ║
╚══════════════════════════════════════════════════════════════╝

    Connected to: {CANVAS_CONFIG['base_url']}

    → Type 'help' for available commands
    → Use TAB for auto-completion and ↑↓ for history
    → Type 'status' to see current context

        """
        self.console.print(intro_text, style="cyan")

    def execute_command(self, input_text: str):
        """Execute a command from user input"""
        if not input_text.strip():
            return

        try:
            parts = shlex.split(input_text)
            cmd_name = parts[0]

            if cmd_name in ['exit', 'quit']:
                raise EOFError

            if cmd_name == 'help':
                self.show_help()
                return

            if cmd_name not in COMMANDS:
                RichStyler.error(f"Unknown command: {cmd_name}")
                return

            cmd_data = COMMANDS[cmd_name]
            if cmd_data["parser"]:
                try:
                    args = cmd_data["parser"].parse_args(parts[1:])
                    cmd_data["func"](self, args)
                except ValueError as e:
                    if str(e) != "Exit":
                        RichStyler.error(str(e))
            else:
                cmd_data["func"](self, None)

        except ValueError as e:
            if "quote" in str(e).lower():
                RichStyler.error("Quote error in command. Make sure quotes are properly closed.")

    def show_help(self):
        """Display help information with Rich markdown formatting"""
        from rich.markdown import Markdown

        help_text = """# 📚 CanvasLMS-CLI Help

## 🎯 General Commands
- `status`              Show current CLI context and status
- `help`                Show this help message
- `exit`, `quit`        Exit the CLI

## 📖 Course Management
- `ls courses`          List all accessible courses
- `use course <id>`     Select a course to work with
- `ls folders`          List folders in the current course

## 🔍 Resource Information
- `show assignments`    List assignments in current course
- `show students`       List students in current course
- `show quizzes`        List quizzes in current course
- `show assignment <id>` Show details for a specific assignment
- `show quiz <id>`      Show details for a specific quiz

## ⬇️  Download Data
- `download students`   Download students CSV for current course
- `download assignment grades <id>` Download grades for an assignment
- `download assignment submissions <id>` Download submissions for an assignment
- `download quiz questions <id>` Download quiz questions
- `download quiz submissions <id>` Download quiz submissions

## ⬆️  Upload Data
- `upload assignment grades <id> -f <file>` Upload grades from CSV

## ➕ Create/Delete Resources
- `create assignment <name>` Create a new assignment
- `delete assignment <id>`   Delete an assignment

## ⚙️ Command Options
- Use `--help` with any command for detailed options
- Use **TAB** for auto-completion
- Commands are case-sensitive

## 📄 CSV Format for Grade Upload
The CSV file should have these columns:
- `student_id` (required)
- `grade` (required)
- `comment` (optional)
- `markdown_file` (optional - will be converted to PDF)
- `pdf_file` (optional)

## 💡 Examples
```python
ls courses
use course 12345
show assignments
download assignment grades 67890 --file grades.csv
upload assignment grades 67890 --file updated_grades.csv
```
"""
        # Render with Rich Markdown for beautiful formatting
        markdown = Markdown(help_text)
        self.console.print(markdown)

    def update_prompt(self):
        """Update the prompt display (placeholder for compatibility)"""
        pass

    def poutput(self, msg: str = '', **kwargs):
        """Output a message to the console"""
        self.console.print(msg, **kwargs)

    def update_last_operation(self, operation: str):
        """Update the last operation status"""
        self.status_bar.update_last_operation(operation)

    def success(self, msg: str):
        """Display success message"""
        RichStyler.success(msg)

    def info(self, msg: str):
        """Display info message"""
        RichStyler.info(msg)

    def warning(self, msg: str):
        """Display warning message"""
        RichStyler.warning(msg)

    def perror(self, msg: str):
        """Display error message"""
        RichStyler.error(msg)

    @property
    def prompt(self):
        """Get current prompt text"""
        return self.get_prompt_text()

    @prompt.setter
    def prompt(self, value: str):
        """Set prompt text"""
        pass

    def run(self):
        """Main REPL loop"""
        self.display_intro()

        while True:
            try:
                # Get user input with auto-completion and bottom toolbar (status bar)
                user_input = self.session.prompt(
                    self.get_prompt_text(),
                    completer=self.completer,
                    complete_while_typing=True,
                    complete_in_thread=True,
                    bottom_toolbar=self.bottom_toolbar,
                )

                self.execute_command(user_input)

            except (KeyboardInterrupt, EOFError):
                RichStyler.info("\n👋 Goodbye!")
                break
            except Exception as e:
                # Catch any unexpected errors
                RichStyler.error(f"Unexpected error: {e}")
                import traceback
                self.console.print_exception(show_locals=True)


# Command Parser Definitions
# Status command
status_parser = REPLArgumentParser(prog="status", description="Show current CLI context and status")

@command("status", status_parser)
def do_status(cli: CanvasCLIRich, args):
    """Display current status and context information."""
    from canvascli.cli.ui import RichTable

    cli.console.print()
    cli.console.print(RichTable.format_header("Canvas LMS CLI - Current Status", width=70))
    cli.console.print()

    # Connection info
    cli.console.print(f"  • Canvas URL: {CANVAS_CONFIG['base_url']}")
    cli.console.print(f"  • Connection: {cli.status_bar.connection_status}")
    cli.console.print(f"  • Last Operation: {cli.status_bar.last_operation}")
    cli.console.print()

    # Course info
    if cli.command_handler.selected_course:
        course = cli.command_handler.selected_course
        cli.console.print(Text(f"  ● Selected Course: {course['name']}", style="green bold"))
        cli.console.print(f"    └─ ID: {course['id']}")
        cli.console.print(f"    └─ Code: {course.get('course_code', 'N/A')}")
        cli.console.print(f"    └─ Term: {course.get('term', {}).get('name', 'N/A')}")
    else:
        cli.console.print(Text("  ⚠ No course selected", style="yellow"))

    cli.console.print()
    cli.console.print(Text("Commands:", style="cyan"))
    cli.console.print("  • Type 'ls courses' to see available courses")
    cli.console.print("  • Type 'use course <id>' to select a course")
    cli.console.print("  • Type 'help' for all available commands")


# List command parsers
ls_parser = REPLArgumentParser(prog="ls", description="List Canvas resources")
ls_subparsers = ls_parser.add_subparsers(dest="entity", required=True)

# ls courses
sp_ls_courses = ls_subparsers.add_parser("courses", help="List all courses")
sp_ls_courses.add_argument("--name", "-n", help="Regex to filter by course name")
sp_ls_courses.add_argument("--code", "-c", help="Regex to filter by course code")
sp_ls_courses.add_argument("-i", "--ignore-case", action="store_true", help="Make the regex case-insensitive")
sp_ls_courses.add_argument("--refresh", action="store_true", help="Refresh courses from Canvas (ignore cache)")

# ls folders
sp_ls_folders = ls_subparsers.add_parser("folders", help="List folders in a course")
sp_ls_folders.add_argument("course_id", nargs="?", help="Course ID (optional; uses current course if omitted)")

@command("ls", ls_parser)
def do_ls(cli: CanvasCLIRich, args):
    """List courses or folders."""
    if args.entity == "courses":
        cli.command_handler.list_courses(args)
    elif args.entity == "folders":
        cli.command_handler.list_folders(args)


# Use command parsers
use_parser = REPLArgumentParser(prog="use", description="Select a resource to use")
use_subparsers = use_parser.add_subparsers(dest="entity", required=True)
sp_use_course = use_subparsers.add_parser("course", help="Select a course by ID")
sp_use_course.add_argument("course_id", help="Course ID to select")

@command("use", use_parser)
def do_use(cli: CanvasCLIRich, args):
    """Select current course (updates the prompt)."""
    if args.entity == "course":
        cli.command_handler.select_course(args.course_id)


# Show command parsers
show_parser = REPLArgumentParser(prog="show", description="Show course resources")
show_subparsers = show_parser.add_subparsers(dest="entity", required=True)
show_subparsers.add_parser("assignments", help="Show assignments in current course")
show_subparsers.add_parser("students", help="Show students in current course")
show_subparsers.add_parser("quizzes", help="Show quizzes in current course")
sp_show_assignment = show_subparsers.add_parser("assignment", help="Show details for a specific assignment")
sp_show_assignment.add_argument("assignment_id", help="Assignment ID to show details for")
sp_show_quiz = show_subparsers.add_parser("quiz", help="Show details for a specific quiz")
sp_show_quiz.add_argument("quiz_id", help="Quiz ID to show details for")

@command("show", show_parser)
def do_show(cli: CanvasCLIRich, args):
    """Show assignments or students of the current course."""
    if args.entity == "assignments":
        cli.command_handler.list_assignments()
    elif args.entity == "students":
        cli.command_handler.list_students()
    elif args.entity == "quizzes":
        cli.command_handler.list_quizzes()
    elif args.entity == "assignment":
        try:
            assignment_id = int(args.assignment_id)
            cli.command_handler.show_assignment_details(assignment_id)
        except Exception as e:
            RichStyler.error(f"Invalid assignment id {args.assignment_id}. It must be a number")
    elif args.entity == "quiz":
        try:
            quiz_id = int(args.quiz_id)
            cli.command_handler.show_quiz_details(quiz_id)
        except Exception as e:
            RichStyler.error(f"Invalid quiz id {args.quiz_id}. It must be a number")


# Download command parsers
download_parser = REPLArgumentParser(prog="download", description="Download resources as CSV")
dl_subparsers = download_parser.add_subparsers(dest="entity", required=True)
sp_dl_students = dl_subparsers.add_parser("students", help="Download students CSV for current course")
sp_dl_students.add_argument("--file", "-f", required=False, help="Output CSV file (default name is based on the course name)")

# Download course
sp_dl_course = dl_subparsers.add_parser("course", help="Download course-related data")
dl_course_sub = sp_dl_course.add_subparsers(dest="what", required=True)
sp_dl_course_grades = dl_course_sub.add_parser("grades", help="Download all grades for the current course")
sp_dl_course_grades.add_argument("--file", "-f", required=False, help="Output CSV file")

sp_dl_assignment = dl_subparsers.add_parser("assignment", help="Download assignment-related data")
dl_assign_sub = sp_dl_assignment.add_subparsers(dest="what", required=True)
sp_dl_assignment_grades = dl_assign_sub.add_parser("grades", help="Download grades for an assignment")
sp_dl_assignment_grades.add_argument("assignment_id", help="Assignment ID")
sp_dl_assignment_grades.add_argument("--file", "-f", required=False, help="Output CSV file (default name is based on the course and assignment name)")
sp_dl_assignment_submissions = dl_assign_sub.add_parser("submissions", help="Download assignment submissions with file attachments")
sp_dl_assignment_submissions.add_argument("assignment_id", help="Assignment ID")
sp_dl_assignment_submissions.add_argument("--dir", "-d", required=False, help="Output directory (default: current directory)")
sp_dl_quiz = dl_subparsers.add_parser("quiz", help="Download quiz-related data")
dl_quiz_sub = sp_dl_quiz.add_subparsers(dest="what", required=True)
sp_dl_quiz_questions = dl_quiz_sub.add_parser("questions", help="Download quiz questions as JSON or Markdown")
sp_dl_quiz_questions.add_argument("quiz_id", help="Quiz ID")
sp_dl_quiz_questions.add_argument("--file", "-f", required=False, help="Output file (default name is based on the quiz title)")
sp_dl_quiz_questions.add_argument("--markdown", "-m", action="store_true", help="Export as Markdown instead of JSON")
sp_dl_quiz_submissions = dl_quiz_sub.add_parser("submissions", help="Download quiz submissions as JSON or Markdown files")
sp_dl_quiz_submissions.add_argument("quiz_id", help="Quiz ID")
sp_dl_quiz_submissions.add_argument("--dir", "-d", required=False, help="Output directory (default: current directory)")
sp_dl_quiz_submissions.add_argument("--markdown", "-m", action="store_true", help="Export as Markdown instead of JSON")

@command("download", download_parser)
def do_download(cli: CanvasCLIRich, args):
    """Download students or assignment grades as CSV."""
    if args.entity == "students":
        cli.command_handler.download_students_csv(args.file)
    elif args.entity == "course" and args.what == "grades":
        cli.command_handler.download_course_grades_csv(args.file)
    elif args.entity == "assignment" and args.what == "grades":
        try:
            assignment_id = int(args.assignment_id)
            cli.command_handler.download_assignment_grades_csv(assignment_id, args.file)
        except Exception as e:
            RichStyler.error(f"Invalid assignment id {args.assignment_id}. It must be a number")
    elif args.entity == "assignment" and args.what == "submissions":
        try:
            assignment_id = int(args.assignment_id)
            cli.command_handler.download_assignment_submissions(assignment_id, args.dir)
        except Exception as e:
            RichStyler.error(f"Invalid assignment id {args.assignment_id}. It must be a number")
    elif args.entity == "quiz" and args.what == "questions":
        try:
            quiz_id = int(args.quiz_id)
            cli.command_handler.download_quiz_questions(quiz_id, args.file, args.markdown)
        except Exception as e:
            RichStyler.error(f"Invalid quiz id {args.quiz_id}. It must be a number")
    elif args.entity == "quiz" and args.what == "submissions":
        try:
            quiz_id = int(args.quiz_id)
            cli.command_handler.download_quiz_submissions(quiz_id, args.dir, args.markdown)
        except Exception as e:
            RichStyler.error(f"Error downloading quiz submissions: {e}")


# Upload command parsers
upload_parser = REPLArgumentParser(prog="upload", description="Upload resources from CSV")
ul_subparsers = upload_parser.add_subparsers(dest="entity", required=True)
sp_ul_assignment = ul_subparsers.add_parser("assignment", help="Upload assignment-related data")
ul_assign_sub = sp_ul_assignment.add_subparsers(dest="what", required=True)
sp_ul_assignment_grades = ul_assign_sub.add_parser("grades", help="Upload grades for an assignment")
sp_ul_assignment_grades.add_argument("assignment_id", help="Assignment ID")
sp_ul_assignment_grades.add_argument("--file", "-f", required=True, help="Input CSV file")
sp_ul_assignment_grades.add_argument("--root-dir", "-r", required=False, help="Root directory to resolve relative file paths in the CSV (defaults to the CSV file's parent directory)")

@command("upload", upload_parser)
def do_upload(cli: CanvasCLIRich, args):
    """Upload assignment grades from CSV."""
    if args.entity == "assignment" and args.what == "grades":
        try:
            assignment_id = int(args.assignment_id)
            cli.command_handler.upload_assignment_grades_csv(assignment_id, args.file, args.root_dir)
            RichStyler.success(f"Successfully uploaded grades for assignment {assignment_id}")
            cli.status_bar.update_last_operation(f"Uploaded grades for assignment {assignment_id}")
        except Exception as e:
            RichStyler.error(f"Invalid assignment id {args.assignment_id}. It must be a number")


# Create command parsers
create_parser = REPLArgumentParser(prog="create", description="Create Canvas resources")
create_subparsers = create_parser.add_subparsers(dest="entity", required=True)
sp_create_assignment = create_subparsers.add_parser("assignment", help="Create a new assignment")
sp_create_assignment.add_argument("name", help="Assignment name")
sp_create_assignment.add_argument("--points", "-p", type=float, help="Points possible")
sp_create_assignment.add_argument("--due-date", "-d", help="Due date (ISO format: YYYY-MM-DDTHH:MM:SSZ, e.g., 2024-12-31T23:59:59Z)")
sp_create_assignment.add_argument("--description", "--desc", help="Assignment description")
sp_create_assignment.add_argument("--published", action="store_true", help="Publish immediately")

@command("create", create_parser)
def do_create(cli: CanvasCLIRich, args):
    """Create assignments or other resources."""
    if args.entity == "assignment":
        try:
            cli.command_handler.create_assignment(args)
            RichStyler.success(f"Assignment '{args.name}' created successfully")
            cli.status_bar.update_last_operation(f"Created assignment {args.name}")
        except Exception as e:
            RichStyler.error(f"Failed to create assignment: {e}")


# Delete command parsers
delete_parser = REPLArgumentParser(prog="delete", description="Delete Canvas resources")
delete_subparsers = delete_parser.add_subparsers(dest="entity", required=True)
sp_delete_assignment = delete_subparsers.add_parser("assignment", help="Delete an assignment")
sp_delete_assignment.add_argument("assignment_id", help="Assignment ID to delete")

@command("delete", delete_parser)
def do_delete(cli: CanvasCLIRich, args):
    """Delete assignments or other resources."""
    if args.entity == "assignment":
        try:
            assignment_id = int(args.assignment_id)
            course_name = cli.command_handler.selected_course['name'] if cli.command_handler.selected_course else "Unknown course"
            cli.command_handler.delete_assignment(assignment_id)
            RichStyler.success(f"Assignment {assignment_id} deleted from {course_name}")
            cli.status_bar.update_last_operation(f"Deleted assignment {assignment_id}")
        except Exception as e:
            RichStyler.error(f"Invalid assignment id {args.assignment_id}. It must be a number")


def main():
    """Entry point for the Rich-based CLI"""
    try:
        app = CanvasCLIRich()
        app.run()
    except Exception as e:
        console = Console()
        console.print(f"[red]Failed to start CLI: {e}[/red]")
        import traceback
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
