#!/usr/bin/env python3
import argparse
from cmd2 import Cmd, Cmd2ArgumentParser, with_argparser
from canvas_cli_cmd_handler import CanvasCLICommandHandler
from config import CANVAS_CONFIG

class CanvasCLI(Cmd):
    """Interactive Canvas CLI management"""

    intro = """
🎓 Canvas LMS - Command Line Interface
==========================================
Connected to: """ + CANVAS_CONFIG['base_url'] + """

Type 'help' for available commands
Type 'ls courses' to see your courses
Type 'ls folders <course_id>' to see the folders in a course
Type 'use course <course_id>' to select a course
Type 'exit' to quit

Pro tip: Use TAB for auto-completion!
"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.canvas_cli_cmd_hdlr = CanvasCLICommandHandler(self)

    # ---------------------------
    # ls command with subcommands
    # ---------------------------
    ls_parser = Cmd2ArgumentParser(prog="ls", description="List Canvas resources")
    ls_subparsers = ls_parser.add_subparsers(dest="entity", required=True)

    sp_ls_courses = ls_subparsers.add_parser("courses", help="List all courses")

    sp_ls_courses.add_argument(
        "--name", "-n",
        help="Regex to filter by course name"
    )
    sp_ls_courses.add_argument(
        "--code", "-c",
        help="Regex to filter by course code"
    )
    sp_ls_courses.add_argument(
        "-i", "--ignore-case",
        action="store_true",
        help="Make the regex case-insensitive"
    )
    sp_ls_courses.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh courses from Canvas (ignore cache)"
    )

    sp_ls_folders = ls_subparsers.add_parser("folders", help="List folders in a course")
    sp_ls_folders.add_argument(
        "course_id",
        nargs="?",
        help="Course ID (optional; uses current course if omitted)"
    )

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

    # ---------------------------
    # show command with subcommands
    # ---------------------------
    show_parser = Cmd2ArgumentParser(prog="show", description="Show course resources")
    show_subparsers = show_parser.add_subparsers(dest="entity", required=True)

    show_subparsers.add_parser("assignments", help="Show assignments in current course")
    show_subparsers.add_parser("students", help="Show students in current course")

    sp_show_assignment = show_subparsers.add_parser("assignment", help="Show details for a specific assignment")
    sp_show_assignment.add_argument("assignment_id", help="Assignment ID to show details for")

    @with_argparser(show_parser)
    def do_show(self, args: argparse.Namespace):
        """Show assignments or students of the current course."""

        if args.entity == "assignments":
            self.canvas_cli_cmd_hdlr.list_assignments();
        elif args.entity == "students":
            self.canvas_cli_cmd_hdlr.list_students();
        elif args.entity == "assignment":
            try:
                assignment_id = int(args.assignment_id)
                self.canvas_cli_cmd_hdlr.show_assignment_details(assignment_id)
            except Exception as e:
                self.perror(f"Invalid assignment id {args.assignment_id}. It must be a number")

    # ---------------------------
    # download command with subcommands (nested)
    # ---------------------------
    download_parser = Cmd2ArgumentParser(prog="download", description="Download resources as CSV")
    dl_subparsers = download_parser.add_subparsers(dest="entity", required=True)

    # download students [--file FILE]
    sp_dl_students = dl_subparsers.add_parser("students", help="Download students CSV for current course")
    sp_dl_students.add_argument("--file", "-f", required=False, help="Output CSV file (default name is based on the course name)")

    # download assignment grades <assignment_id> --file FILE
    sp_dl_assignment = dl_subparsers.add_parser("assignment", help="Download assignment-related data")
    dl_assign_sub = sp_dl_assignment.add_subparsers(dest="what", required=True)

    sp_dl_assignment_grades = dl_assign_sub.add_parser("grades", help="Download grades for an assignment")
    sp_dl_assignment_grades.add_argument("assignment_id", help="Assignment ID")
    sp_dl_assignment_grades.add_argument("--file", "-f", required=False, help="Output CSV file (default name is based on the course and assignment name)")

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

    # ---------------------------
    # upload command with subcommands (nested)
    # ---------------------------
    upload_parser = Cmd2ArgumentParser(prog="upload", description="Upload resources from CSV")
    ul_subparsers = upload_parser.add_subparsers(dest="entity", required=True)

    # upload assignment grades <assignment_id> --file FILE
    sp_ul_assignment = ul_subparsers.add_parser("assignment", help="Upload assignment-related data")
    ul_assign_sub = sp_ul_assignment.add_subparsers(dest="what", required=True)

    sp_ul_assignment_grades = ul_assign_sub.add_parser("grades", help="Upload grades for an assignment")
    sp_ul_assignment_grades.add_argument("assignment_id", help="Assignment ID")
    sp_ul_assignment_grades.add_argument("--file", "-f", required=True, help="Input CSV file")
    sp_ul_assignment_grades.add_argument(
        "--root-dir", "-r",
        required=False,
        help="Root directory to resolve relative file paths in the CSV (defaults to the CSV file's parent directory)"
    )

    @with_argparser(upload_parser)
    def do_upload(self, args: argparse.Namespace):
        """Upload assignment grades from CSV."""
        if args.entity == "assignment" and args.what == "grades":
            try:
                assignment_id = int(args.assignment_id)
                self.canvas_cli_cmd_hdlr.upload_assignment_grades_csv(assignment_id, args.file, args.root_dir)
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
            self.canvas_cli_cmd_hdlr.create_assignment(args)

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
                self.canvas_cli_cmd_hdlr.delete_assignment(assignment_id)
            except Exception as e:
                self.perror(f"Invalid assignment id {args.assignment_id}. It must be a number")

    # ---------------------------
    # exit / quit
    # ---------------------------
    def do_exit(self, _):
        """Exit the CLI."""
        return True

    def do_quit(self, _):
        """Exit the CLI."""
        return True


if __name__ == "__main__":
    app = CanvasCLI()
    app.cmdloop()
