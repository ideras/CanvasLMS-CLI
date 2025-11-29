#!/usr/bin/env python3
import argparse
import os
from cmd2 import Cmd, Cmd2ArgumentParser, with_argparser
from canvas_cli_cmd_handler import CanvasCLICommandHandler
from canvas_cli_ui import CLIStyler, StatusBar
from config import CANVAS_CONFIG
from datetime import datetime

class CanvasCLI(Cmd):
    """Enhanced Interactive Canvas CLI management with UI improvements"""

    base_url = CANVAS_CONFIG['base_url']

    intro = f"""
╔══════════════════════════════════════════════════════════════╗
║                  🎓 Canvas LMS Command Center                ║
╚══════════════════════════════════════════════════════════════╝

    Connected to: {base_url}

    → Type 'help' for available commands
    → Use TAB for auto-completion and ↑↓ for history
    → Type 'status' to see current context

"""

    def __init__(self, *args, **kwargs):
        # Enable persistent history
        history_file = os.path.expanduser('~/.canvas_cli_history')
        kwargs['persistent_history_file'] = history_file
        kwargs['persistent_history_length'] = 1000

        super().__init__(*args, **kwargs)

        self.canvas_cli_cmd_hdlr = CanvasCLICommandHandler(self)
        self.status_bar = StatusBar(self)

        # Set up prompt styling
        self.update_prompt()

    def update_prompt(self):
        """Update CLI prompt based on current context"""
        if self.canvas_cli_cmd_hdlr.selected_course:
            course_name = self.canvas_cli_cmd_hdlr.selected_course['name'].lower().replace(' ', '_')
            course_name_prompt = course_name[:20] + "..." if len(course_name) > 20 else course_name
            self.prompt = CLIStyler.success(f"canvas/{course_name_prompt}> ")
        else:
            self.prompt = CLIStyler.info("canvas> ")

    def poutput(self, msg: str = '', *, end: str = '\n') -> None:
        """Override to improve output formatting"""
        super().poutput(msg, end=end)

    def perror(self, msg: str, *, end: str = '\n', apply_style: bool = True) -> None:
        """Override error messages with styling"""
        if apply_style:
            super().perror(CLIStyler.error(msg), end=end, apply_style=False)
        else:
            super().perror(msg, end=end, apply_style=False)

    def success(self, msg: str):
        """Custom method for success messages"""
        self.poutput(CLIStyler.success(msg))
        self.status_bar.update_last_operation(msg)

    def info(self, msg: str):
        """Custom method for info messages"""
        self.poutput(CLIStyler.info(msg))

    def warning(self, msg: str):
        """Custom method for warning messages"""
        self.poutput(CLIStyler.warning(msg))

    def update_last_operation(self, operation: str):
        """Update the last operation timestamp"""
        self.status_bar.update_last_operation(operation)

    def show_status_header(self):
        """Show formatted status header"""
        status_text = self.status_bar.get_status_text(self.canvas_cli_cmd_hdlr.selected_course)
        self.poutput(f"\n{status_text}\n")

    # ---------------------------
    # status command
    # ---------------------------
    status_parser = Cmd2ArgumentParser(prog="status", description="Show current CLI context and status")

    @with_argparser(status_parser)
    def do_status(self, args: argparse.Namespace):
        """Display current status and context information."""

        self.info("=" * 70)
        self.info("              Canvas LMS CLI - Current Status")
        self.info("=" * 70)
        self.poutput("")

        # Connection info
        self.poutput(f"  • Canvas URL: {CANVAS_CONFIG['base_url']}")
        self.poutput(f"  • Connection: {self.status_bar.connection_status}")
        self.poutput(f"  • Last Operation: {self.status_bar.last_operation}")
        self.poutput("")

        # Course info
        if self.canvas_cli_cmd_hdlr.selected_course:
            course = self.canvas_cli_cmd_hdlr.selected_course
            self.success(f"  ● Selected Course: {course['name']}")
            self.poutput(f"    └─ ID: {course['id']}")
            self.poutput(f"    └─ Code: {course.get('course_code', 'N/A')}")
            self.poutput(f"    └─ Term: {course.get('term', {}).get('name', 'N/A')}")
        else:
            self.warning("  ⚠ No course selected")

        self.poutput("")
        self.info("Commands:")
        self.poutput("  • Type 'ls courses' to see available courses")
        self.poutput("  • Type 'use course <id>' to select a course")
        self.poutput("  • Type 'help' for all available commands")

    # ---------------------------
    # ls command with subcommands
    # ---------------------------
    ls_parser = Cmd2ArgumentParser(prog="ls", description="List Canvas resources")
    ls_subparsers = ls_parser.add_subparsers(dest="entity", required=True)

    sp_ls_courses = ls_subparsers.add_parser("courses", help="List all courses")
    sp_ls_courses.add_argument("--name", "-n", help="Regex to filter by course name")
    sp_ls_courses.add_argument("--code", "-c", help="Regex to filter by course code")
    sp_ls_courses.add_argument("-i", "--ignore-case", action="store_true", help="Make the regex case-insensitive")
    sp_ls_courses.add_argument("--refresh", action="store_true", help="Refresh courses from Canvas (ignore cache)")

    sp_ls_folders = ls_subparsers.add_parser("folders", help="List folders in a course")
    sp_ls_folders.add_argument("course_id", nargs="?", help="Course ID (optional; uses current course if omitted)")

    @with_argparser(ls_parser)
    def do_ls(self, args: argparse.Namespace):
        """List courses or folders."""
        if args.entity == "courses":
            self.canvas_cli_cmd_hdlr.list_courses(args)
        elif args.entity == "folders":
            self.canvas_cli_cmd_hdlr.list_folders(args)

    # ---------------------------
    # use command: select course
    # ---------------------------
    use_parser = Cmd2ArgumentParser(prog="use", description="Select a resource to use")
    use_subparsers = use_parser.add_subparsers(dest="entity", required=True)
    sp_use_course = use_subparsers.add_parser("course", help="Select a course by ID")
    sp_use_course.add_argument("course_id", help="Course ID to select")

    @with_argparser(use_parser)
    def do_use(self, args: argparse.Namespace):
        """Select current course (updates the prompt)."""
        if args.entity == "course":
            self.canvas_cli_cmd_hdlr.select_course(args.course_id)
            self.update_prompt()
            self.success(f"Selected course: {self.canvas_cli_cmd_hdlr.selected_course['name']}")

    # ---------------------------
    # show command with subcommands
    # ---------------------------
    show_parser = Cmd2ArgumentParser(prog="show", description="Show course resources")
    show_subparsers = show_parser.add_subparsers(dest="entity", required=True)
    show_subparsers.add_parser("assignments", help="Show assignments in current course")
    show_subparsers.add_parser("students", help="Show students in current course")
    show_subparsers.add_parser("quizzes", help="Show quizzes in current course")
    sp_show_assignment = show_subparsers.add_parser("assignment", help="Show details for a specific assignment")
    sp_show_assignment.add_argument("assignment_id", help="Assignment ID to show details for")
    sp_show_quiz = show_subparsers.add_parser("quiz", help="Show details for a specific quiz")
    sp_show_quiz.add_argument("quiz_id", help="Quiz ID to show details for")

    @with_argparser(show_parser)
    def do_show(self, args: argparse.Namespace):
        """Show assignments or students of the current course."""
        if args.entity == "assignments":
            self.canvas_cli_cmd_hdlr.list_assignments()
        elif args.entity == "students":
            self.canvas_cli_cmd_hdlr.list_students()
        elif args.entity == "quizzes":
            self.canvas_cli_cmd_hdlr.list_quizzes()
        elif args.entity == "assignment":
            try:
                assignment_id = int(args.assignment_id)
                self.canvas_cli_cmd_hdlr.show_assignment_details(assignment_id)
            except Exception as e:
                self.perror(f"Invalid assignment id {args.assignment_id}. It must be a number")
        elif args.entity == "quiz":
            try:
                quiz_id = int(args.quiz_id)
                self.canvas_cli_cmd_hdlr.show_quiz_details(quiz_id)
            except Exception as e:
                self.perror(f"Invalid quiz id {args.quiz_id}. It must be a number")

    # ---------------------------
    # download command with subcommands (nested)
    # ---------------------------
    download_parser = Cmd2ArgumentParser(prog="download", description="Download resources as CSV")
    dl_subparsers = download_parser.add_subparsers(dest="entity", required=True)

    sp_dl_students = dl_subparsers.add_parser("students", help="Download students CSV for current course")
    sp_dl_students.add_argument("--file", "-f", required=False, help="Output CSV file (default name is based on the course name)")

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

    @with_argparser(download_parser)
    def do_download(self, args: argparse.Namespace):
        """Download students or assignment grades as CSV."""
        if args.entity == "students":
            self.canvas_cli_cmd_hdlr.download_students_csv(args.file)
        elif args.entity == "assignment" and args.what == "grades":
            try:
                assignment_id = int(args.assignment_id)
                self.canvas_cli_cmd_hdlr.download_assignment_grades_csv(assignment_id, args.file)
            except Exception as e:
                self.perror(f"Invalid assigment id {args.assignment_id}. It must be a number")
        elif args.entity == "assignment" and args.what == "submissions":
            try:
                assignment_id = int(args.assignment_id)
                self.canvas_cli_cmd_hdlr.download_assignment_submissions(assignment_id, args.dir)
            except Exception as e:
                self.perror(f"Invalid assigment id {args.assignment_id}. It must be a number")
        elif args.entity == "quiz" and args.what == "questions":
            try:
                quiz_id = int(args.quiz_id)
                self.canvas_cli_cmd_hdlr.download_quiz_questions(quiz_id, args.file, args.markdown)
            except Exception as e:
                self.perror(f"Invalid quiz id {args.quiz_id}. It must be a number")
        elif args.entity == "quiz" and args.what == "submissions":
            try:
                quiz_id = int(args.quiz_id)
                self.canvas_cli_cmd_hdlr.download_quiz_submissions(quiz_id, args.file, args.markdown)
            except Exception as e:
                self.perror(f"Invalid quiz id {args.quiz_id}. It must be a number")

    # ---------------------------
    # upload command with subcommands (nested)
    # ---------------------------
    upload_parser = Cmd2ArgumentParser(prog="upload", description="Upload resources from CSV")
    ul_subparsers = upload_parser.add_subparsers(dest="entity", required=True)

    sp_ul_assignment = ul_subparsers.add_parser("assignment", help="Upload assignment-related data")
    ul_assign_sub = sp_ul_assignment.add_subparsers(dest="what", required=True)
    sp_ul_assignment_grades = ul_assign_sub.add_parser("grades", help="Upload grades for an assignment")
    sp_ul_assignment_grades.add_argument("assignment_id", help="Assignment ID")
    sp_ul_assignment_grades.add_argument("--file", "-f", required=True, help="Input CSV file")
    sp_ul_assignment_grades.add_argument("--root-dir", "-r", required=False, help="Root directory to resolve relative file paths in the CSV (defaults to the CSV file's parent directory)")

    @with_argparser(upload_parser)
    def do_upload(self, args: argparse.Namespace):
        """Upload assignment grades from CSV."""
        if args.entity == "assignment" and args.what == "grades":
            try:
                assignment_id = int(args.assignment_id)
                self.canvas_cli_cmd_hdlr.upload_assignment_grades_csv(assignment_id, args.file, args.root_dir)
                self.success(f"Successfully uploaded grades for assignment {assignment_id}")
                self.status_bar.update_last_operation(f"Uploaded grades for assignment {assignment_id}")
            except Exception as e:
                self.perror(f"Invalid assigment id {args.assignment_id}. It must be a number")

    # ---------------------------
    # create command with subcommands
    # ---------------------------
    create_parser = Cmd2ArgumentParser(prog="create", description="Create Canvas resources")
    create_subparsers = create_parser.add_subparsers(dest="entity", required=True)

    sp_create_assignment = create_subparsers.add_parser("assignment", help="Create a new assignment")
    sp_create_assignment.add_argument("name", help="Assignment name")
    sp_create_assignment.add_argument("--points", "-p", type=float, help="Points possible")
    sp_create_assignment.add_argument("--due-date", "-d", help="Due date (ISO format: YYYY-MM-DDTHH:MM:SSZ, e.g., 2024-12-31T23:59:59Z)")
    sp_create_assignment.add_argument("--description", "--desc", help="Assignment description")
    sp_create_assignment.add_argument("--published", action="store_true", help="Publish immediately")

    @with_argparser(create_parser)
    def do_create(self, args: argparse.Namespace):
        """Create assignments or other resources."""
        if args.entity == "assignment":
            try:
                self.canvas_cli_cmd_hdlr.create_assignment(args)
                self.success(f"Assignment '{args.name}' created successfully")
                self.status_bar.update_last_operation(f"Created assignment {args.name}")
            except Exception as e:
                self.perror(f"Failed to create assignment: {e}")

    # ---------------------------
    # delete command with subcommands
    # ---------------------------
    delete_parser = Cmd2ArgumentParser(prog="delete", description="Delete Canvas resources")
    delete_subparsers = delete_parser.add_subparsers(dest="entity", required=True)

    sp_delete_assignment = delete_subparsers.add_parser("assignment", help="Delete an assignment")
    sp_delete_assignment.add_argument("assignment_id", help="Assignment ID to delete")

    @with_argparser(delete_parser)
    def do_delete(self, args: argparse.Namespace):
        """Delete assignments or other resources."""
        if args.entity == "assignment":
            try:
                assignment_id = int(args.assignment_id)
                course_name = self.canvas_cli_cmd_hdlr.selected_course['name'] if self.canvas_cli_cmd_hdlr.selected_course else "Unknown course"
                self.canvas_cli_cmd_hdlr.delete_assignment(assignment_id)
                self.success(f"Assignment {assignment_id} deleted from {course_name}")
                self.status_bar.update_last_operation(f"Deleted assignment {assignment_id}")
            except Exception as e:
                self.perror(f"Invalid assignment id {args.assignment_id}. It must be a number")

    # ---------------------------
    # exit / quit
    # ---------------------------
    def do_exit(self, _):
        """Exit the CLI."""
        self.info("👋 Goodbye!")
        return True

    def do_quit(self, _):
        """Exit the CLI."""
        self.info("👋 Goodbye!")
        return True


if __name__ == "__main__":
    app = CanvasCLI()
    app.cmdloop()