#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
from typing import Dict, Optional

from markdownify import markdownify

from canvascli.cli.ui import RichStyler
from canvascli.api.client import CanvasClient
from canvascli.grades.uploader import CanvasGradesUploader
from canvascli.config import APP_CONFIG, CANVAS_CONFIG


class CanvasCLICommandHandler:
    def __init__(self, cli):
        self.cli = cli
        self.canvas_client = CanvasClient(
            CANVAS_CONFIG["base_url"], CANVAS_CONFIG["token"]
        )

        self.selected_course: Optional[Dict] = None

    def require_course(self) -> Optional[Dict]:
        if not self.selected_course:
            self.cli.perror("No course selected. Use: use course <course_id>")
            return None

        return self.selected_course

    def select_course(self, course_id: str):
        """Switch to a specific course context using course number or Canvas ID"""

        all_courses = self.canvas_client.get_all_courses()

        if not all_courses:
            self.cli.perror("No courses available.")
            return

        try:
            course_id_number = int(course_id)

            self.selected_course = next(
                (course for course in all_courses if course["id"] == course_id_number),
                None,
            )

            if not self.selected_course:
                self.cli.perror(
                    f"Course with Canvas ID {course_id} not found in your accessible courses"
                )
                self.cli.poutput(
                    "💡 Use 'ls courses' to see available courses and their IDs"
                )
                return

            self.update_prompt()
            self.cli.success(f"Selected course: {self.selected_course['name']}")
            self.cli.update_last_operation(
                f"Selected course {self.selected_course['name']}"
            )

        except ValueError:
            self.cli.perror(f"Invalid course identifier: {course_id}")
            return

    def update_prompt(self):
        """Update CLI prompt based on current context"""

        if self.selected_course:
            course_name = self.selected_course["name"].lower().replace(" ", "_")
            course_name_prompt = (
                course_name[:20] + "..." if len(course_name) > 20 else course_name
            )

            self.cli.prompt = f"canvas/{course_name_prompt}> "
        else:
            self.cli.prompt = "canvas> "

    def list_courses(self, args: argparse.Namespace) -> None:
        """List all the active courses with optional regex filters."""

        try:
            courses = self.canvas_client.get_all_courses(
                force_refresh=getattr(args, "refresh", False)
            )
        except Exception as e:
            self.cli.poutput(str(e))
            return

        flags = re.IGNORECASE if getattr(args, "ignore_case", False) else 0

        try:
            name_rx = (
                re.compile(args.name, flags) if getattr(args, "name", None) else None
            )
            code_rx = (
                re.compile(args.code, flags) if getattr(args, "code", None) else None
            )
        except re.error as rex:
            self.cli.perror(f"Invalid regex: {rex}")
            return

        def match(course: dict) -> bool:
            if name_rx and not name_rx.search(course.get("name") or ""):
                return False
            if code_rx and not code_rx.search(course.get("course_code") or ""):
                return False
            return True

        filtered = [c for c in courses if match(c)]
        total = len(courses)
        count = len(filtered)

        # Update last operation
        self.cli.update_last_operation(f"Listed {count} courses")

        # Header
        header_text = "📚 Available Courses"
        if name_rx or code_rx:
            header_text += " (filtered)"

        self.cli.poutput(f"[bold white]{'═' * 70}[/bold white]")
        self.cli.poutput(f"[bold white]{header_text}[/bold white]")
        self.cli.poutput(f"[bold white]{'═' * 70}[/bold white]")
        self.cli.poutput("")

        # Table header
        header = f"{'ID':<10} {'Course Code':<20} {'Term':<20} {'Course Name':<40}"
        self.cli.poutput(f"[bold white]{header}[/bold white]")
        self.cli.poutput(f"[dim]{'─' * 110}[/dim]")

        # Course rows
        for i, course in enumerate(filtered, 1):
            course_id = str(course.get("id", "N/A"))
            name = course.get("name", "N/A")
            code = course.get("course_code", "N/A")
            term = course.get("term", {}).get("name", "N/A")

            # Truncate long fields
            name = name[:37] + "..." if len(name) > 40 else name
            code = code[:17] + "..." if len(code) > 20 else code
            term = term[:17] + "..." if len(term) > 20 else term

            # Selected course highlighting
            is_current = self.selected_course and course.get(
                "id"
            ) == self.selected_course.get("id")
            if is_current:
                row = f"[green bold]● {course_id:<8} {code:<20} {term:<20} {name:<40}[/green bold]"
                self.cli.poutput(row)
            else:
                row = f"  {course_id:<8} {code:<20} {term:<20} {name:<40}"
                self.cli.poutput(row)

        if not filtered:
            self.cli.poutput("\n   No courses matched your filter.")

        self.cli.poutput("")
        self.cli.info("💡 Use 'use course <canvas_id>' to select a course")
        if filtered:
            self.cli.poutput(f"    Example: 'use course {filtered[0]['id']}'")

    def list_folders(self, args: argparse.Namespace) -> None:
        """List folders for a specific course."""

        course_id = getattr(args, "course_id", None)

        if not course_id:
            course = self.require_course()

            if not course:
                return

            course_id = course["id"]

        try:
            all_folders = self.canvas_client.get_folders_for_course(course_id)

            hdr = f"Available Folders for course {course_id}"
            self.cli.poutput(f"\n{hdr}\n" + "=" * len(hdr))

            for i, folder in enumerate(all_folders, 1):
                self.cli.poutput(
                    f'{i:2d}. "{folder.get("full_name")}" (ID: {folder.get("id")}, Name: "{folder.get("name")}")'
                )

            if not all_folders:
                self.cli.poutput("No folders available in the course.")
            else:
                self.cli.poutput(f"Total folders available: {len(all_folders)}")

        except Exception as e:
            self.cli.poutput(str(e))

    def list_assignments(self) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course["id"]

            all_assignments = self.canvas_client.get_assignments_for_course(course_id)

            assignment_groups = self.canvas_client.canvas_re.make_request(
                f"/courses/{course_id}/assignment_groups"
            )
            group_map = {group["id"]: group["name"] for group in assignment_groups}

            # Header with Rich formatting
            self.cli.poutput(f"[bold cyan]{'═' * 80}[/bold cyan]")
            self.cli.poutput(f"[bold white]📋 Assignments for: {course['name']}[/bold white]")
            self.cli.poutput(f"[dim]Course ID: {course_id}[/dim]")
            self.cli.poutput(f"[bold cyan]{'═' * 80}[/bold cyan]")
            self.cli.poutput("")

            if not all_assignments:
                self.cli.poutput(f"[yellow]⚠ No assignments found in this course[/yellow]")
                return

            # Create a Rich table for assignments
            from canvascli.cli.ui import RichTable
            from rich.console import Console
            from rich.text import Text

            # Prepare table data
            table_data = []
            for assignment in all_assignments:
                # ID column (make it stand out)
                assign_id = str(assignment['id'])

                # Name column (truncate if too long)
                name = assignment.get('name', 'Unnamed Assignment')
                if len(name) > 40:
                    name = name[:37] + '...'

                # Due date column
                if assignment.get('due_at'):
                    due_date = assignment['due_at'][:10]  # YYYY-MM-DD
                else:
                    due_date = Text("No due date", style="dim")

                # Points column
                points = assignment.get('points_possible', 0)
                if not points:
                    points = Text("—", style="dim")

                # Group column
                group_id = assignment.get('assignment_group_id')
                group_name = group_map.get(group_id, 'No group') if group_id else 'No group'
                if len(group_name) > 20:
                    group_name = group_name[:17] + '...'

                # Published status
                published = assignment.get('published', False)
                status = Text("✓", style="green") if published else Text("✗", style="red")

                table_data.append([assign_id, name, due_date, points, group_name, status])

            # Sort by due date (if available)
            def sort_key(row):
                due = row[2]
                if isinstance(due, Text):
                    return "9999-99-99"  # Put "No due date" at the end
                return due

            table_data.sort(key=sort_key)

            # Create and display table
            table = RichTable.create_table(
                title="",
                columns=["ID", "Assignment Name", "Due Date", "Points", "Group", "Published"],
                rows=table_data
            )
            table.show_header = True
            table.header_style = "bold cyan"
            table.border_style = "dim"
            table.expand = True

            # Use Rich directly to print the table
            console = Console()
            console.print(table)

            self.cli.poutput("")
            self.cli.poutput(f"[bold green]✓[/bold green] Total assignments: [bold]{len(all_assignments)}[/bold]")

            # Show tip about using assignment ID
            if all_assignments:
                self.cli.poutput("")
                self.cli.poutput(f"[dim]Tip: Use 'show assignment [ID]' to see details[/dim]")
                self.cli.poutput(f"[dim]       Use 'download assignment grades [ID] --file grades.csv' to download grades[/dim]")

            self.cli.update_last_operation(f"Listed {len(all_assignments)} assignments")

        except Exception as e:
            self.cli.perror(f"Failed to list assignments: {e}")

    def show_assignment_details(self, assignment_id: int) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course["id"]
            all_assignments = self.canvas_client.get_assignments_for_course(course_id)

            assignment = next(
                (a for a in all_assignments if a["id"] == assignment_id), None
            )

            if not assignment:
                self.cli.perror(
                    f"Cannot find assignment with ID: {assignment_id} in course '{course['name']}'"
                )
                return

            assignment_groups = self.canvas_client.canvas_re.make_request(
                f"/courses/{course_id}/assignment_groups"
            )
            group_map = {group["id"]: group["name"] for group in assignment_groups}

            # Main header with Rich formatting - include name and ID in header
            self.cli.poutput("")
            self.cli.poutput(f"[bold cyan]{'═' * 80}[/bold cyan]")
            self.cli.poutput(f"[bold white]📋 Assignment Details: {assignment['name']}[/bold white] [dim](ID: {assignment['id']})[/dim]")
            self.cli.poutput(f"[bold cyan]{'═' * 80}[/bold cyan]")
            self.cli.poutput("")

            # Description section (if exists)
            description = assignment.get("description")
            if description:
                self.cli.poutput("[bold white]Description:[/bold white]")
                # Convert HTML to Markdown if needed
                try:
                    from rich.markup import escape
                    desc_text = markdownify(description)
                    # Limit length for display
                    if len(desc_text) > 500:
                        desc_text = desc_text[:497] + "..."
                    self.cli.poutput(f"{escape(desc_text)}")
                except:
                    # If markdownify fails, just show plain text
                    self.cli.poutput(f"{description[:500]}")
                self.cli.poutput("")

            # Create a Rich table for assignment details
            from canvascli.cli.ui import RichTable
            from rich.text import Text

            table_data = []

            # Basic info
            group_id = assignment.get("assignment_group_id")
            group_name = group_map.get(group_id, "No group") if group_id else "No group"
            table_data.append(["📁 Group", group_name])
            table_data.append(["🎯 Points", str(assignment.get("points_possible", "N/A"))])

            # Dates
            due_date = assignment.get("due_at")
            if due_date:
                table_data.append(["📅 Due Date", f"{due_date[:10]} {due_date[11:16]} UTC"])
            else:
                table_data.append(["📅 Due Date", Text("No due date", style="dim")])

            lock_at = assignment.get("lock_at")
            if lock_at:
                table_data.append(["🔒 Lock Date", f"{lock_at[:10]} {lock_at[11:16]} UTC"])

            unlock_at = assignment.get("unlock_at")
            if unlock_at:
                table_data.append(["🔓 Unlock Date", f"{unlock_at[:10]} {unlock_at[11:16]} UTC"])

            # Submission settings
            submission_types = assignment.get("submission_types", [])
            if submission_types:
                table_data.append(["📤 Submission Types", ", ".join(submission_types)])

            allowed_attempts = assignment.get("allowed_attempts")
            if allowed_attempts and allowed_attempts > 0:
                table_data.append(["🔄 Allowed Attempts", str(allowed_attempts)])
            elif allowed_attempts == -1:
                table_data.append(["🔄 Allowed Attempts", "Unlimited"])

            # Status
            published = assignment.get('published', False)
            status_text = Text("✓ Yes", style="green") if published else Text("✗ No", style="yellow")
            table_data.append(["📊 Published", status_text])

            table_data.append(["🏷️ Status", assignment.get('workflow_state', 'Unknown').title()])

            has_submissions = assignment.get("has_submitted_submissions", False)
            submissions_text = Text("✓ Yes", style="green") if has_submissions else Text("✗ No", style="dim")
            table_data.append(["📨 Has Submissions", submissions_text])

            needs_grading = assignment.get("needs_grading_count", 0)
            if needs_grading > 0:
                table_data.append(["📝 Needs Grading", Text(str(needs_grading), style="yellow bold")])

            # URL
            table_data.append(["🌐 Canvas URL", assignment.get('html_url', 'N/A')])

            # Create and display table
            table = RichTable.create_table(
                title="",
                columns=["Property", "Value"],
                rows=table_data
            )
            table.show_header = False
            table.border_style = "dim"
            table.expand = False

            # Make the first column wider for better readability
            if table.columns:
                table.columns[0].width = 25  # Property column width
                table.columns[0].justify = "right"

            # Use Rich directly to print the table
            from rich.console import Console
            console = Console()
            console.print(table)

            self.cli.poutput("")
            self.cli.update_last_operation(f"Viewed assignment {assignment['name']}")

        except Exception as e:
            self.cli.perror(f"Failed to show assignment details: {e}")

    def list_students(self) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course["id"]
            all_students = self.canvas_client.get_students_for_course(course_id)

            # Header with Rich formatting
            self.cli.poutput(f"[bold cyan]{'═' * 80}[/bold cyan]")
            self.cli.poutput(f"[bold white]👥 Students in: {course['name']}[/bold white]")
            self.cli.poutput(f"[dim]Course ID: {course_id}[/dim]")
            self.cli.poutput(f"[bold cyan]{'═' * 80}[/bold cyan]")
            self.cli.poutput("")

            if not all_students:
                self.cli.poutput(f"[yellow]⚠ No students enrolled in this course[/yellow]")
                return

            # Create a Rich table for students
            from canvascli.cli.ui import RichTable
            from rich.text import Text

            # Prepare table data
            table_data = []
            for student in all_students:
                student_id = str(student['id'])

                name = student.get('name', 'No name')
                if len(name) > 35:
                    name = name[:32] + '...'

                email = student.get('email', 'No email')
                if len(email) > 30:
                    email = email[:27] + '...'

                table_data.append([student_id, name, email])

            # Sort by name
            table_data.sort(key=lambda x: x[1].lower())

            # Create and display table
            table = RichTable.create_table(
                title="",
                columns=["Canvas ID", "Name", "Email"],
                rows=table_data
            )
            table.show_header = True
            table.header_style = "bold cyan"
            table.border_style = "dim"
            table.expand = True

            # Use Rich directly to print the table
            from rich.console import Console
            console = Console()
            console.print(table)

            self.cli.poutput("")
            self.cli.poutput(f"[bold green]✓[/bold green] Total students: [bold]{len(all_students)}[/bold]")
            self.cli.poutput("")
            self.cli.poutput(f"[dim]Tip: Use 'download students --file students.csv' to export to CSV[/dim]")

            self.cli.update_last_operation(f"Listed {len(all_students)} students")

        except Exception as e:
            self.cli.perror(f"Failed to list students: {e}")

    def download_students_csv(self, filepath: Optional[str]) -> None:
        """Export student list with IDs to CSV"""

        course = self.require_course()

        if not course:
            return

        try:
            course_id = course["id"]
            course_name = course["name"]

            all_students = self.canvas_client.get_students_for_course(course_id)

            if not all_students:
                self.cli.poutput("No students found in this course")
                return

            if not filepath:
                safe_course_name = "".join(
                    c for c in course_name if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                filename = (
                    f"students_{course_id}_{safe_course_name.replace(' ', '_')}.csv"
                )
            else:
                filename = filepath

            with open(
                filename, "w", newline="", encoding=APP_CONFIG["default_encoding"]
            ) as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["canvas_id", "name", "email", "sis_user_id"])

                for student in all_students:
                    writer.writerow(
                        [
                            student["id"],
                            student.get("name", ""),
                            student.get("email", ""),
                            student.get("sis_user_id", ""),
                        ]
                    )

            self.cli.poutput(f"Student list exported to: {filename}")
            self.cli.poutput(f"Total students: {len(all_students)}")
        except Exception as e:
            self.cli.perror(f"Failed to export student list: {e}")

    def download_assignment_grades_csv(
        self, assignment_id: int, output_file: Optional[str]
    ) -> None:
        """Export course assignments to CSV"""

        course = self.require_course()

        if not course:
            return

        course_id = course["id"]

        try:
            all_assignments = self.canvas_client.get_assignments_for_course(course_id)

            assignment = next(
                (a for a in all_assignments if a["id"] == assignment_id), None
            )

            if not assignment:
                self.cli.poutput(
                    f"Cannot find assignment with ID: {assignment_id} in course '{course['name']}'"
                )
                return

            self.cli.poutput(f"\nGrade Download Summary:")
            self.cli.poutput(f"   Course: {course['name']}")
            self.cli.poutput(f"   Assignment: {assignment['name']}")

            students = self.canvas_client.get_students_for_course(course_id)
            submissions = self.canvas_client.get_submissions_for_assignment(
                course_id, assignment_id
            )

            student_map = {student["id"]: student for student in students}

            if not output_file:
                safe_assignment_name = "".join(
                    c for c in assignment["name"] if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                output_file = (
                    f"grades_{course_id}_{safe_assignment_name.replace(' ', '_')}.csv"
                )

            grade_data = []
            for submission in submissions:
                user_id = submission.get("user_id")
                if user_id in student_map:
                    student = student_map[user_id]
                    grade_data.append(
                        {
                            "canvas_id": user_id,
                            "name": student.get("name", ""),
                            "email": student.get("email", ""),
                            "grade": submission.get("score", ""),
                            "submitted_at": submission.get("submitted_at", ""),
                            "workflow_state": submission.get("workflow_state", ""),
                            "late": submission.get("late", False),
                        }
                    )

            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "canvas_id",
                    "name",
                    "email",
                    "grade",
                    "submitted_at",
                    "workflow_state",
                    "late",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(grade_data)

            print(f"Downloaded {len(grade_data)} grades to: {output_file}")
            return output_file

        except Exception as e:
            print(f"Failed to download grades: {e}")

    def download_course_grades_csv(self, output_file: Optional[str]) -> None:
        """Export all course student grades to CSV"""

        course = self.require_course()
        if not course:
            return

        course_id = course["id"]

        try:
            self.cli.poutput(f"\nCourse Grade Download Summary:")
            self.cli.poutput(f"   Course: {course['name']}")

            self.cli.poutput("   Fetching students and assignments...", end="")
            students = self.canvas_client.get_students_for_course(course_id)
            assignments = self.canvas_client.get_assignments_for_course(course_id)
            self.cli.poutput(" Done.")

            if not output_file:
                safe_course_name = "".join(
                    c for c in course["name"] if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                output_file = f"course_grades_{course_id}_{safe_course_name.replace(' ', '_')}.csv"

            # Build student map: canvas_id -> { info..., grades: {} }
            grade_data = {}
            for student in students:
                s_id = student["id"]
                grade_data[s_id] = {
                    "canvas_id": s_id,
                    "name": student.get("name", ""),
                    "sis_user_id": student.get("sis_user_id", ""),
                    "grades": {}
                }

            # Sort assignments by name or position
            assignments.sort(key=lambda x: (x.get('position', 0), x.get('name', '')))

            # Iterate over assignments and fetch submissions
            total_assignments = len(assignments)
            for idx, assignment in enumerate(assignments):
                a_id = assignment["id"]
                a_name = assignment["name"]
                
                self.cli.poutput(f"   Fetching grades for '{a_name}' ({idx + 1}/{total_assignments})...", end="\r")
                
                submissions = self.canvas_client.get_submissions_for_assignment(course_id, a_id)
                
                for sub in submissions:
                    user_id = sub.get("user_id")
                    if user_id in grade_data:
                        score = sub.get("score")
                        grade_data[user_id]["grades"][a_name] = score if score is not None else ""

            self.cli.poutput(f"   Fetching grades for all assignments... Done.        ")

            # Calculate Final Score (Simple sum or weighted? usually provided by enrollments, but let's stick to assignment cols)
            # We can also fetch enrollments to get the "computed" final score from Canvas
            enrollments = self.canvas_client.get_enrollments_for_course(course_id)
            for enrollment in enrollments:
                 user_id = enrollment.get("user_id")
                 if user_id in grade_data:
                     grades = enrollment.get("grades", {})
                     grade_data[user_id]["current_score"] = grades.get("current_score", "")
                     grade_data[user_id]["final_score"] = grades.get("final_score", "")
                     grade_data[user_id]["final_grade"] = grades.get("final_grade", "")

            # Prepare CSV headers
            fieldnames = ["canvas_id", "name", "sis_user_id"]
            assignment_names = [a["name"] for a in assignments]
            fieldnames.extend(assignment_names)
            fieldnames.extend(["current_score", "final_score", "final_grade"])

            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for student_id in grade_data:
                    student_record = grade_data[student_id]
                    row = {
                        "canvas_id": student_record["canvas_id"],
                        "name": student_record["name"],
                        "sis_user_id": student_record["sis_user_id"],
                        "current_score": student_record.get("current_score", ""),
                        "final_score": student_record.get("final_score", ""),
                        "final_grade": student_record.get("final_grade", ""),
                    }
                    # Add assignment grades
                    for a_name in assignment_names:
                        row[a_name] = student_record["grades"].get(a_name, "")
                    
                    writer.writerow(row)

            self.cli.poutput(f"Downloaded grades for {len(grade_data)} students to: {output_file}")
            return output_file

        except Exception as e:
            self.cli.perror(f"Failed to download course grades: {e}")

    def upload_assignment_grades_csv(
        self, assignment_id: int, csv_filepath: str, root_dir: Optional[str]
    ) -> None:
        """Upload course assignment grades from a file in CSV format"""

        course = self.require_course()

        if not course:
            return

        course_id = course["id"]

        try:
            canvas_grades_uploader = CanvasGradesUploader(
                self.cli, self.canvas_client, csv_filepath, root_dir
            )

            all_assignments = self.canvas_client.get_assignments_for_course(course_id)

            assignment = next(
                (a for a in all_assignments if a["id"] == assignment_id), None
            )

            if not assignment:
                self.cli.poutput(
                    f"Cannot find assignment with ID: {assignment_id} in course '{course['name']}'"
                )
                return

            canvas_grades_uploader.upload_grades(
                course_id, assignment_id, assignment["name"]
            )
        except Exception as e:
            self.cli.poutput(f"Error uploading grades to Canvas: {e}")

    def create_assignment(self, args: argparse.Namespace) -> None:
        course = self.require_course()
        if not course:
            return

        assignment_data = {"name": args.name}
        if args.points:
            assignment_data["points_possible"] = args.points
        if args.due_date:
            assignment_data["due_at"] = args.due_date
        if args.description:
            assignment_data["description"] = args.description
        if args.published:
            assignment_data["published"] = True

        try:
            new_assignment = self.canvas_client.create_assignment(
                course["id"], {"assignment": assignment_data}
            )
            self.cli.poutput(
                f"✅ Assignment created: {new_assignment['name']} (ID: {new_assignment['id']})"
            )
        except Exception as e:
            self.cli.perror(f"Failed to create assignment: {e}")

    def delete_assignment(self, assignment_id: int) -> None:
        course = self.require_course()
        if not course:
            return

        try:
            all_assignments = self.canvas_client.get_assignments_for_course(
                course["id"]
            )
            assignment = next(
                (a for a in all_assignments if a["id"] == assignment_id), None
            )

            if not assignment:
                self.cli.poutput(
                    f"Cannot find assignment with ID: {assignment_id} in course '{course['name']}'"
                )
                return

            self.cli.poutput(
                f"⚙️ Deleting assignment: {assignment['name']} (ID: {assignment_id}) …"
            )
            deleted_assignment = self.canvas_client.delete_assignment(
                course["id"], assignment_id
            )
            self.cli.poutput(f"✅ Assignment deleted.")
        except Exception as e:
            self.cli.perror(f"Failed to delete assignment: {e}")

    def list_quizzes(self) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course["id"]
            all_quizzes = self.canvas_client.get_quizzes_for_course(course_id)

            assignment_groups = self.canvas_client.canvas_re.make_request(
                f"/courses/{course_id}/assignment_groups"
            )
            group_map = {group["id"]: group["name"] for group in assignment_groups}

            # Header with Rich formatting
            self.cli.poutput(f"[bold cyan]{'═' * 80}[/bold cyan]")
            self.cli.poutput(f"[bold white]📝 Quizzes in: {course['name']}[/bold white]")
            self.cli.poutput(f"[dim]Course ID: {course_id}[/dim]")
            self.cli.poutput(f"[bold cyan]{'═' * 80}[/bold cyan]")
            self.cli.poutput("")

            if not all_quizzes:
                self.cli.poutput(f"[yellow]⚠ No quizzes found in this course[/yellow]")
                return

            # Create a Rich table for quizzes
            from canvascli.cli.ui import RichTable
            from rich.text import Text

            # Prepare table data
            table_data = []
            for quiz in all_quizzes:
                # Quiz ID
                quiz_id = str(quiz['id'])

                # Title (truncate if too long)
                title = quiz.get('title', 'Untitled Quiz')
                if len(title) > 35:
                    title = title[:32] + '...'

                # Due date
                if quiz.get('due_at'):
                    due_date = quiz['due_at'][:10]  # YYYY-MM-DD
                else:
                    due_date = Text("No due date", style="dim")

                # Points
                points = quiz.get('points_possible', 0)
                if not points:
                    points = Text("—", style="dim")

                # Question count
                question_count = str(quiz.get('question_count', 0))

                # Group
                group_id = quiz.get('assignment_group_id')
                group_name = group_map.get(group_id, 'No group') if group_id else 'No group'
                if len(group_name) > 20:
                    group_name = group_name[:17] + '...'

                # Published status with colors
                published = quiz.get('published', False)
                status = Text("✓ Published", style="green") if published else Text("✗ Draft", style="yellow")

                table_data.append([quiz_id, title, due_date, points, question_count, group_name, status])

            # Sort by due date
            def sort_key(row):
                due = row[2]
                if isinstance(due, Text):
                    return "9999-99-99"  # Put "No due date" at the end
                return due

            table_data.sort(key=sort_key)

            # Create and display table
            table = RichTable.create_table(
                title="",
                columns=["ID", "Quiz Title", "Due Date", "Points", "Questions", "Group", "Status"],
                rows=table_data
            )
            table.show_header = True
            table.header_style = "bold cyan"
            table.border_style = "dim"
            table.expand = True

            # Use Rich directly to print the table
            from rich.console import Console
            console = Console()
            console.print(table)

            self.cli.poutput("")
            self.cli.poutput(f"[bold green]✓[/bold green] Total quizzes: [bold]{len(all_quizzes)}[/bold]")

            # Show tip about using quiz ID
            if all_quizzes:
                self.cli.poutput("")
                self.cli.poutput(f"[dim]Tip: Use 'show quiz [ID]' to see details and questions[/dim]")
                self.cli.poutput(f"[dim]       Use 'download quiz questions [ID]' to export questions[/dim]")

            self.cli.update_last_operation(f"Listed {len(all_quizzes)} quizzes")

        except Exception as e:
            self.cli.perror(f"Failed to list quizzes: {e}")

    def show_quiz_details(self, quiz_id: int) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course["id"]
            all_quizzes = self.canvas_client.get_quizzes_for_course(course_id)

            quiz = next((q for q in all_quizzes if q["id"] == quiz_id), None)

            if not quiz:
                self.cli.perror(
                    f"Cannot find quiz with ID: {quiz_id} in course '{course['name']}'"
                )
                return

            assignment_groups = self.canvas_client.canvas_re.make_request(
                f"/courses/{course_id}/assignment_groups"
            )
            group_map = {group["id"]: group["name"] for group in assignment_groups}

            # Main header with Rich formatting - include title, ID, and type in header
            self.cli.poutput("")
            self.cli.poutput(f"[bold cyan]{'═' * 80}[/bold cyan]")
            self.cli.poutput(f"[bold white]📝 Quiz Details: {quiz['title']}[/bold white] [dim](ID: {quiz['id']}, Type: {quiz.get('quiz_type', 'N/A')})[/dim]")
            self.cli.poutput(f"[bold cyan]{'═' * 80}[/bold cyan]")
            self.cli.poutput("")

            # Description section (convert HTML to Markdown)
            description = quiz.get("description")
            if description:
                self.cli.poutput("[bold white]Description:[/bold white]")
                try:
                    from rich.panel import Panel
                    from rich.markup import escape
                    # Convert HTML to Markdown
                    desc_markdown = markdownify(description)
                    # Limit for display
                    if len(desc_markdown) > 1000:
                        desc_markdown = desc_markdown[:997] + "..."

                    # Create a panel for the description
                    desc_panel = Panel(
                        escape(desc_markdown),
                        border_style="dim",
                        title="[dim]Description[/dim]",
                        expand=False
                    )
                    from rich.console import Console
                    console = Console()
                    console.print(desc_panel)
                except Exception as e:
                    # If conversion fails, show plain text
                    self.cli.poutput(f"{description[:500]}")
                self.cli.poutput("")

            # Create a Rich table for quiz details
            from canvascli.cli.ui import RichTable
            from rich.text import Text

            table_data = []

            # Group
            group_id = quiz.get("assignment_group_id")
            group_name = group_map.get(group_id, "No group") if group_id else "No group"
            table_data.append(["📁 Group", group_name])

            # Points and questions
            table_data.append(["🎯 Points", str(quiz.get("points_possible", "N/A"))])
            question_count = quiz.get("question_count", 0)
            table_data.append(["❓ Questions", str(question_count)])

            # Time limit
            time_limit = quiz.get("time_limit")
            if time_limit:
                table_data.append(["⏱️ Time Limit", f"{time_limit} minutes"])

            # Dates
            due_date = quiz.get("due_at")
            if due_date:
                table_data.append(["📅 Due Date", f"{due_date[:10]} {due_date[11:16]} UTC"])
            else:
                table_data.append(["📅 Due Date", Text("No due date", style="dim")])

            lock_at = quiz.get("lock_at")
            if lock_at:
                table_data.append(["🔒 Lock Date", f"{lock_at[:10]} {lock_at[11:16]} UTC"])

            unlock_at = quiz.get("unlock_at")
            if unlock_at:
                table_data.append(["🔓 Unlock Date", f"{unlock_at[:10]} {unlock_at[11:16]} UTC"])

            # Quiz settings
            allowed_attempts = quiz.get("allowed_attempts")
            if allowed_attempts and allowed_attempts > 0:
                table_data.append(["🔄 Allowed Attempts", str(allowed_attempts)])
            elif allowed_attempts == -1:
                table_data.append(["🔄 Allowed Attempts", "Unlimited"])

            shuffle_answers = quiz.get('shuffle_answers', False)
            shuffle_text = Text("✓ Yes", style="green") if shuffle_answers else Text("✗ No", style="dim")
            table_data.append(["🔀 Shuffle Answers", shuffle_text])

            show_correct = quiz.get('show_correct_answers', False) if quiz.get('show_correct_answers') is not None else True
            correct_text = Text("✓ Yes", style="green") if show_correct else Text("✗ No", style="dim")
            table_data.append(["✅ Show Correct Answers", correct_text])

            one_at_a_time = quiz.get('one_question_at_a_time', False)
            one_time_text = Text("✓ Yes", style="yellow") if one_at_a_time else Text("✗ No", style="dim")
            table_data.append(["📄 One Question at a Time", one_time_text])

            cant_go_back = quiz.get('cant_go_back', False)
            cant_back_text = Text("✓ Yes", style="red") if cant_go_back else Text("✗ No", style="dim")
            table_data.append(["⏮️ Can't Go Back", cant_back_text])

            # Access code
            access_code = quiz.get("access_code")
            if access_code:
                table_data.append(["🔑 Access Code", Text(access_code, style="yellow")])

            # Scoring and results
            table_data.append(["📊 Scoring Policy", quiz.get('scoring_policy', 'N/A').title()])

            hide_results = quiz.get('hide_results', 'N/A')
            table_data.append(["👁️ Hide Results", str(hide_results).title()])

            # Status
            published = quiz.get('published', False)
            status_text = Text("✓ Published", style="green") if published else Text("✗ Draft", style="yellow")
            table_data.append(["📤 Status", status_text])

            table_data.append(["🏷️ Workflow State", quiz.get('workflow_state', 'Unknown').title()])

            # Lock status
            locked = quiz.get("locked_for_user", False)
            if locked:
                locked_text = Text("✓ Yes", style="red")
                table_data.append(["🔒 Locked for User", locked_text])
                if quiz.get("lock_explanation"):
                    table_data.append(["ℹ️ Lock Reason", quiz.get("lock_explanation")])
            else:
                locked_text = Text("✗ No", style="green")
                table_data.append(["🔒 Locked for User", locked_text])

            # URL
            table_data.append(["🌐 Canvas URL", quiz.get('html_url', 'N/A')])

            # Create and display table
            table = RichTable.create_table(
                title="",
                columns=["Property", "Value"],
                rows=table_data
            )
            table.show_header = False
            table.border_style = "dim"
            table.expand = False

            # Make the first column wider for better readability
            if table.columns:
                table.columns[0].width = 25  # Property column width
                table.columns[0].justify = "right"

            # Use Rich directly to print the table
            from rich.console import Console
            console = Console()
            console.print(table)

            self.cli.poutput("")
            self.cli.update_last_operation(f"Viewed quiz {quiz['title']}")

        except Exception as e:
            self.cli.perror(f"Failed to show quiz details: {e}")

    def download_quiz_questions(
        self, quiz_id: int, output_file: Optional[str], markdown: bool = False
    ) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course["id"]
            course_name = course["name"]

            all_quizzes = self.canvas_client.get_quizzes_for_course(course_id)
            quiz = next((q for q in all_quizzes if q["id"] == quiz_id), None)

            if not quiz:
                self.cli.poutput(
                    f"Cannot find quiz with ID: {quiz_id} in course '{course['name']}'"
                )
                return

            questions = self.canvas_client.get_quiz_questions(course_id, quiz_id)

            if not questions:
                self.cli.poutput(f"No questions found for quiz '{quiz['title']}'")
                return

            if not output_file:
                safe_quiz_title = "".join(
                    c for c in quiz["title"] if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                ext = "md" if markdown else "json"
                filename = f"quiz_{quiz_id}_{safe_quiz_title.replace(' ', '_')}_questions.{ext}"
            else:
                filename = output_file

            if markdown:
                from markdownify import markdownify

                md_content = f"# {quiz.get('title', 'Quiz')}\n\n"

                md_content += "**Quiz Details**\n\n"
                md_content += f"- **ID:** {quiz.get('id')}\n"
                md_content += f"- **Type:** {quiz.get('quiz_type', 'N/A')}\n"
                md_content += f"- **Points:** {quiz.get('points_possible', 'N/A')}\n"
                md_content += f"- **Questions:** {quiz.get('question_count', 'N/A')}\n"

                time_limit = quiz.get("time_limit")
                if time_limit:
                    md_content += f"- **Time Limit:** {time_limit} minutes\n"

                due_at = quiz.get("due_at")
                if due_at:
                    md_content += f"- **Due:** {due_at[:10]} {due_at[11:16]} UTC\n"

                lock_at = quiz.get("lock_at")
                if lock_at:
                    md_content += (
                        f"- **Locked After:** {lock_at[:10]} {lock_at[11:16]} UTC\n"
                    )

                unlock_at = quiz.get("unlock_at")
                if unlock_at:
                    md_content += f"- **Available From:** {unlock_at[:10]} {unlock_at[11:16]} UTC\n"

                allowed_attempts = quiz.get("allowed_attempts")
                if allowed_attempts:
                    if allowed_attempts == -1:
                        md_content += "- **Attempts:** Unlimited\n"
                    else:
                        md_content += f"- **Attempts:** {allowed_attempts}\n"

                md_content += (
                    f"- **Published:** {'Yes' if quiz.get('published') else 'No'}\n"
                )
                md_content += f"- **Shuffle Answers:** {'Yes' if quiz.get('shuffle_answers') else 'No'}\n"
                md_content += f"- **One Question at a Time:** {'Yes' if quiz.get('one_question_at_a_time') else 'No'}\n"
                md_content += f"- **Can't Go Back:** {'Yes' if quiz.get('cant_go_back') else 'No'}\n"

                access_code = quiz.get("access_code")
                if access_code:
                    md_content += f"- **Access Code:** {access_code}\n"

                md_content += (
                    f"- **Scoring Policy:** {quiz.get('scoring_policy', 'N/A')}\n"
                )
                md_content += f"- **Hide Results:** {quiz.get('hide_results', 'N/A')}\n"
                md_content += f"- **URL:** {quiz.get('html_url', 'N/A')}\n"

                md_content += "\n"

                description = quiz.get("description")
                if description:
                    md_content += "## Description\n\n"
                    md_content += markdownify(
                        description, heading_style="ATX", strip=["script", "style"]
                    )
                    md_content += "\n\n"

                md_content += "## Questions\n\n"

                for i, question in enumerate(questions, 1):
                    q_name = question.get("question_name", f"Question {i}")
                    q_type = question.get("question_type", "unknown")
                    q_points = question.get("points_possible", 0)

                    md_content += f"### Question {i}: {q_name}\n\n"
                    md_content += f"**Type:** {q_type}  \n"
                    md_content += f"**Points:** {q_points}\n\n"

                    q_text = question.get("question_text")
                    if q_text:
                        md_content += markdownify(
                            q_text, heading_style="ATX", strip=["script", "style"]
                        )
                        md_content += "\n\n"

                    answers = question.get("answers", [])
                    if answers and q_type != "essay_question":
                        md_content += "**Answer Options:**\n\n"
                        for ans in answers:
                            ans_text = ans.get("text", "")
                            ans_weight = ans.get("weight", 0)
                            is_correct = ans_weight > 0

                            if is_correct:
                                md_content += f"- [x] **{ans_text}** (correct)\n"
                            else:
                                md_content += f"- [ ] {ans_text}\n"
                        md_content += "\n"

                    correct_comments = question.get("correct_comments")
                    if correct_comments:
                        md_content += "**Correct Feedback:**\n\n"
                        md_content += markdownify(
                            correct_comments,
                            heading_style="ATX",
                            strip=["script", "style"],
                        )
                        md_content += "\n\n"

                    incorrect_comments = question.get("incorrect_comments")
                    if incorrect_comments:
                        md_content += "**Incorrect Feedback:**\n\n"
                        md_content += markdownify(
                            incorrect_comments,
                            heading_style="ATX",
                            strip=["script", "style"],
                        )
                        md_content += "\n\n"

                    neutral_comments = question.get("neutral_comments")
                    if neutral_comments:
                        md_content += "**Neutral Feedback:**\n\n"
                        md_content += markdownify(
                            neutral_comments,
                            heading_style="ATX",
                            strip=["script", "style"],
                        )
                        md_content += "\n\n"

                    md_content += "---\n\n"

                with open(filename, "w", encoding="utf-8") as f:
                    f.write(md_content)

                self.cli.poutput(
                    f"Downloaded {len(questions)} questions to: {filename}"
                )
            else:
                import json

                quiz_details = {
                    "id": quiz.get("id"),
                    "title": quiz.get("title"),
                    "description": quiz.get("description"),
                    "quiz_type": quiz.get("quiz_type"),
                    "points_possible": quiz.get("points_possible"),
                    "question_count": quiz.get("question_count"),
                    "time_limit": quiz.get("time_limit"),
                    "due_at": quiz.get("due_at"),
                    "lock_at": quiz.get("lock_at"),
                    "unlock_at": quiz.get("unlock_at"),
                    "published": quiz.get("published"),
                    "allowed_attempts": quiz.get("allowed_attempts"),
                    "shuffle_answers": quiz.get("shuffle_answers"),
                    "show_correct_answers": quiz.get("show_correct_answers"),
                    "one_question_at_a_time": quiz.get("one_question_at_a_time"),
                    "cant_go_back": quiz.get("cant_go_back"),
                    "access_code": quiz.get("access_code"),
                    "scoring_policy": quiz.get("scoring_policy"),
                    "hide_results": quiz.get("hide_results"),
                    "html_url": quiz.get("html_url"),
                    "workflow_state": quiz.get("workflow_state"),
                    "locked_for_user": quiz.get("locked_for_user"),
                    "lock_explanation": quiz.get("lock_explanation"),
                }

                data = {"quiz": quiz_details, "questions": questions}

                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                self.cli.poutput(
                    f"Downloaded {len(questions)} questions to: {filename}"
                )

        except Exception as e:
            self.cli.poutput(f"Failed to download quiz questions: {e}")

    def download_quiz_submissions(
        self, quiz_id: int, output_dir: Optional[str], markdown: bool = False
    ) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course["id"]

            all_quizzes = self.canvas_client.get_quizzes_for_course(course_id)
            quiz = next((q for q in all_quizzes if q["id"] == quiz_id), None)

            if not quiz:
                self.cli.poutput(
                    f"Cannot find quiz with ID: {quiz_id} in course '{course['name']}'"
                )
                return

            assignment_id = quiz.get("assignment_id")
            if not assignment_id:
                self.cli.poutput(
                    f"Quiz '{quiz['title']}' has no associated assignment_id. Cannot retrieve submission answers."
                )
                return

            submissions_data = self.canvas_client.get_quiz_submissions(
                course_id, quiz_id
            )
            submissions = submissions_data.get("quiz_submissions", [])

            if not submissions:
                self.cli.poutput(f"No submissions found for quiz '{quiz['title']}'")
                return

            students = self.canvas_client.get_students_for_course(course_id)
            student_map = {s["id"]: s for s in students}

            assignment_submissions = self.canvas_client.canvas_re.make_request(
                f"/courses/{course_id}/assignments/{assignment_id}/submissions?per_page=100&include[]=submission_history&include[]=user"
            )

            assignment_sub_map = {}
            if isinstance(assignment_submissions, list):
                for sub in assignment_submissions:
                    assignment_sub_map[sub["user_id"]] = sub

            if not output_dir:
                safe_quiz_title = "".join(
                    c for c in quiz["title"] if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                output_dir = (
                    f"quiz_{quiz_id}_{safe_quiz_title.replace(' ', '_')}_submissions"
                )

            os.makedirs(output_dir, exist_ok=True)
            count = 0

            for submission in submissions:
                user_id = submission["user_id"]
                student = student_map.get(
                    user_id, {"name": f"Unknown ({user_id})", "email": "N/A"}
                )

                if markdown:
                    md_content = f"# Quiz Submission: {quiz.get('title', 'Quiz')}\n\n"

                    md_content += "**Student Information**\n\n"
                    md_content += f"- **Name:** {student.get('name', 'Unknown')}\n"
                    md_content += f"- **Email:** {student.get('email', 'N/A')}\n"
                    md_content += f"- **User ID:** {user_id}\n"
                    md_content += f"- **Submission ID:** {submission['id']}\n\n"

                    md_content += "**Submission Details**\n\n"
                    md_content += (
                        f"- **Started:** {submission.get('started_at', 'N/A')}\n"
                    )
                    md_content += (
                        f"- **Finished:** {submission.get('finished_at', 'N/A')}\n"
                    )
                    md_content += (
                        f"- **Time Spent:** {submission.get('time_spent', 0)} seconds\n"
                    )
                    md_content += f"- **Attempt:** {submission.get('attempt', 1)}\n"
                    md_content += f"- **Score:** {submission.get('score', 0)}/{submission.get('quiz_points_possible', 0)}\n"
                    md_content += (
                        f"- **Status:** {submission.get('workflow_state', 'Unknown')}\n"
                    )
                    md_content += (
                        f"- **Quiz URL:** {submission.get('html_url', 'N/A')}\n\n"
                    )

                    assignment_sub = assignment_sub_map.get(user_id)
                    if (
                        assignment_sub
                        and "submission_history" in assignment_sub
                        and assignment_sub["submission_history"]
                    ):
                        history = assignment_sub["submission_history"][0]
                        if "submission_data" in history:
                            answers = history["submission_data"]
                            if answers:
                                md_content += "## Student Answers\n\n"

                                for ans in answers:
                                    q_id = ans.get("question_id", "Unknown")
                                    ans_text = ans.get("text", "")
                                    points = ans.get("points", 0)
                                    correct = ans.get("correct", "undefined")

                                    md_content += f"### Question ID: {q_id}\n\n"
                                    md_content += f"**Points:** {points}  \n"
                                    md_content += f"**Correct:** {correct}\n\n"

                                    if ans_text:
                                        md_content += "**Answer:**\n\n"
                                        md_content += markdownify(
                                            ans_text,
                                            heading_style="ATX",
                                            strip=["script", "style"],
                                        )
                                        md_content += "\n\n"
                                    else:
                                        md_content += (
                                            "**Answer:** *(no answer provided)*\n\n"
                                        )

                                    md_content += "---\n\n"

                    safe_student_name = "".join(
                        c
                        for c in student.get("name", f"user_{user_id}")
                        if c.isalnum() or c in (" ", "-", "_")
                    ).strip()
                    filename = os.path.join(
                        output_dir,
                        f"{safe_student_name.replace(' ', '_')}.md",
                    )

                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(md_content)
                else:
                    enriched_submission = {
                        "id": submission["id"],
                        "user_id": user_id,
                        "student_name": student.get("name"),
                        "student_email": student.get("email"),
                        "started_at": submission.get("started_at"),
                        "finished_at": submission.get("finished_at"),
                        "score": submission.get("score"),
                        "kept_score": submission.get("kept_score"),
                        "attempt": submission.get("attempt"),
                        "time_spent": submission.get("time_spent"),
                        "workflow_state": submission.get("workflow_state"),
                        "html_url": submission.get("html_url"),
                        "quiz_id": submission.get("quiz_id"),
                        "quiz_points_possible": submission.get("quiz_points_possible"),
                    }

                    assignment_sub = assignment_sub_map.get(user_id)
                    if (
                        assignment_sub
                        and "submission_history" in assignment_sub
                        and assignment_sub["submission_history"]
                    ):
                        history = assignment_sub["submission_history"][0]
                        if "submission_data" in history:
                            enriched_submission["answers"] = history["submission_data"]

                    safe_student_name = "".join(
                        c
                        for c in student.get("name", f"user_{user_id}")
                        if c.isalnum() or c in (" ", "-", "_")
                    ).strip()
                    filename = os.path.join(
                        output_dir,
                        f"submission_{submission['id']}_{safe_student_name.replace(' ', '_')}.json",
                    )

                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(enriched_submission, f, indent=2, ensure_ascii=False)

                count += 1

            self.cli.poutput(
                f"Downloaded {count} submissions to directory: {output_dir}"
            )

        except Exception as e:
            self.cli.poutput(f"Failed to download quiz submissions: {e}")

    def download_assignment_submissions(
        self, assignment_id: int, output_dir: Optional[str]
    ) -> None:
        """Download assignment submissions with file attachments"""

        course = self.require_course()
        if not course:
            return

        course_id = course["id"]

        try:
            # Validate assignment exists
            all_assignments = self.canvas_client.get_assignments_for_course(course_id)
            assignment = next(
                (a for a in all_assignments if a["id"] == assignment_id), None
            )

            if not assignment:
                self.cli.poutput(
                    f"Cannot find assignment with ID: {assignment_id} in course '{course['name']}'"
                )
                return

            self.cli.poutput(f"\nAssignment Submission Download Summary:")
            self.cli.poutput(f"   Course: {course['name']}")
            self.cli.poutput(f"   Assignment: {assignment['name']}")

            # Get submissions with attachments
            submissions = (
                self.canvas_client.get_assignment_submissions_with_attachments(
                    course_id, assignment_id
                )
            )
            students = self.canvas_client.get_students_for_course(course_id)
            student_map = {student["id"]: student for student in students}

            if not submissions:
                self.cli.poutput("No submissions found for this assignment.")
                return

            # Create output directory
            if not output_dir:
                safe_assignment_name = "".join(
                    c for c in assignment["name"] if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                output_dir = f"assignment_{assignment_id}_{safe_assignment_name.replace(' ', '_')}_submissions"

            import os

            os.makedirs(output_dir, exist_ok=True)

            # Prepare summary data
            summary_data = []
            total_files_downloaded = 0
            submissions_with_files = 0

            self.cli.poutput(f"\nProcessing {len(submissions)} submissions...")

            for i, submission in enumerate(submissions, 1):
                user_id = submission.get("user_id")
                student = student_map.get(
                    user_id, {"name": f"Unknown ({user_id})", "email": "N/A"}
                )

                # Create student directory
                safe_student_name = "".join(
                    c
                    for c in student.get("name", f"user_{user_id}")
                    if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                student_dir = os.path.join(output_dir, f"{safe_student_name}_{user_id}")
                os.makedirs(student_dir, exist_ok=True)

                # Get attachments from submission
                attachments = []

                # Check current submission for attachments
                if "attachments" in submission and submission["attachments"]:
                    attachments.extend(submission["attachments"])

                # Check submission history for attachments
                if (
                    "submission_history" in submission
                    and submission["submission_history"]
                ):
                    for history_item in submission["submission_history"]:
                        if (
                            "attachments" in history_item
                            and history_item["attachments"]
                        ):
                            attachments.extend(history_item["attachments"])

                # Remove duplicate attachments based on ID
                seen_ids = set()
                unique_attachments = []
                for att in attachments:
                    if att.get("id") and att["id"] not in seen_ids:
                        seen_ids.add(att["id"])
                        unique_attachments.append(att)

                # Download attachments
                files_downloaded = 0
                attachment_info = []

                for att in unique_attachments:
                    file_name = att.get(
                        "display_name",
                        att.get("filename", f"file_{att.get('id', 'unknown')}"),
                    )
                    file_url = att.get("url", "")

                    if file_url:
                        # Sanitize filename
                        safe_filename = "".join(
                            c
                            for c in file_name
                            if c.isalnum() or c in (".", "-", "_", " ")
                        ).strip()
                        if not safe_filename:
                            safe_filename = f"file_{att.get('id', 'unknown')}"

                        local_path = os.path.join(student_dir, safe_filename)

                        # Download the file
                        self.cli.poutput(
                            f"  Downloading: {student.get('name', f'User {user_id}')} - {file_name}"
                        )

                        if self.canvas_client.download_file_from_url(
                            file_url, local_path
                        ):
                            files_downloaded += 1
                            attachment_info.append(
                                {
                                    "filename": file_name,
                                    "size": att.get("size", 0),
                                    "content_type": att.get("content-type", "unknown"),
                                }
                            )
                        else:
                            self.cli.poutput(f"    Failed to download: {file_name}")

                if files_downloaded > 0:
                    submissions_with_files += 1
                    total_files_downloaded += files_downloaded

                # Add to summary data
                summary_data.append(
                    {
                        "student_name": student.get("name", ""),
                        "student_email": student.get("email", ""),
                        "student_id": user_id,
                        "submitted_at": submission.get("submitted_at", ""),
                        "workflow_state": submission.get("workflow_state", ""),
                        "files_count": files_downloaded,
                        "files_list": "; ".join(
                            [info["filename"] for info in attachment_info]
                        ),
                    }
                )

                # Show progress
                if i % 10 == 0:
                    self.cli.poutput(
                        f"  Processed {i}/{len(submissions)} submissions..."
                    )

            # Create summary CSV
            summary_file = os.path.join(output_dir, "submission_summary.csv")
            with open(summary_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "student_name",
                    "student_email",
                    "student_id",
                    "submitted_at",
                    "workflow_state",
                    "files_count",
                    "files_list",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(summary_data)

            # Final summary
            self.cli.poutput(f"\n✅ Download Complete!")
            self.cli.poutput(f"   Output directory: {output_dir}")
            self.cli.poutput(f"   Total submissions: {len(submissions)}")
            self.cli.poutput(f"   Submissions with files: {submissions_with_files}")
            self.cli.poutput(f"   Total files downloaded: {total_files_downloaded}")
            self.cli.poutput(f"   Summary CSV: {summary_file}")

        except Exception as e:
            self.cli.poutput(f"Failed to download assignment submissions: {e}")
