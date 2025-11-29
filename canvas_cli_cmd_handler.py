#!/usr/bin/env python3
import argparse
import re
import csv
from typing import Optional, Dict
from cmd2 import Cmd, ansi
from canvas_cli_ui import CLIStyler, TableFormatter
from canvas_client import CanvasClient
from canvas_grades_uploader import CanvasGradesUploader
from config import CANVAS_CONFIG, APP_CONFIG

class CanvasCLICommandHandler:
    def __init__(self, cli: Cmd):
        self.cli = cli
        self.canvas_client = CanvasClient(
                CANVAS_CONFIG['base_url'],
                CANVAS_CONFIG['token']
            )

        self.selected_course: Optional[Dict] = None

        self.update_prompt()

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
                (course for course in all_courses if course['id'] == course_id_number),
                None
            )

            if not self.selected_course:
                self.cli.perror(f"Course with Canvas ID {course_id} not found in your accessible courses")
                self.cli.poutput("💡 Use 'ls courses' to see available courses and their IDs")
                return

            self.update_prompt()
            self.cli.success(f"Selected course: {self.selected_course['name']}")
            self.cli.update_last_operation(f"Selected course {self.selected_course['name']}")

        except ValueError:
            self.cli.perror(f"Invalid course identifier: {course_id}")
            return

    def update_prompt(self):
        """Update CLI prompt based on current context"""

        if self.selected_course:
            course_name = self.selected_course['name'].lower().replace(' ', '_')
            course_name_prompt = course_name[:20] + "..." if len(course_name) > 20 else course_name

            self.cli.prompt = f"canvas/{course_name_prompt}> "
        else:
            self.cli.prompt = "canvas> "

    def list_courses(self, args: argparse.Namespace) -> None:
        """List all the active courses with optional regex filters."""

        try:
            courses = self.canvas_client.get_all_courses(force_refresh=getattr(args, "refresh", False))
        except Exception as e:
            self.cli.poutput(str(e))
            return

        flags = re.IGNORECASE if getattr(args, "ignore_case", False) else 0

        try:
            name_rx = re.compile(args.name, flags) if getattr(args, "name", None) else None
            code_rx = re.compile(args.code, flags) if getattr(args, "code", None) else None
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

        self.cli.poutput(CLIStyler.boxed_text_double(header_text))
        self.cli.poutput("")

        # Stats
        filter_status = f" | Filtered: {total - count}" if (name_rx or code_rx) else ""
        self.cli.poutput(f"   Total: {total} | Displaying: {count}{filter_status}")
        self.cli.poutput("")

        # Table header
        header = f"{'ID':<10} {'Course Code':<20} {'Term':<20} {'Course Name':<40}"
        self.cli.poutput(ansi.style(f"{header}", fg=ansi.Fg.WHITE, bold=True))
        self.cli.poutput(ansi.style(f"{'─'*110}", fg=ansi.Fg.LIGHT_GRAY))

        # Course rows
        for i, course in enumerate(filtered, 1):
            course_id = str(course.get("id", "N/A"))
            name = course.get("name", "N/A")
            code = course.get('course_code', 'N/A')
            term = course.get('term', {}).get('name', 'N/A')

            # Truncate long fields
            name = name[:37] + '...' if len(name) > 40 else name
            code = code[:17] + '...' if len(code) > 20 else code
            term = term[:17] + '...' if len(term) > 20 else term

            # Selected course highlighting
            is_current = self.selected_course and course.get("id") == self.selected_course.get("id")
            if is_current:
                row = f"{ansi.style('●', fg=ansi.Fg.GREEN)} {course_id:<8} {code:<20} {term:<20} {name:<40}"
                self.cli.poutput(ansi.style(row, fg=ansi.Fg.GREEN))
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

            course_id = course['id']

        try:
            all_folders = self.canvas_client.get_folders_for_course(course_id)

            hdr = f"Available Folders for course {course_id}"
            self.cli.poutput(f"\n{hdr}\n" + "=" * len(hdr))

            for i, folder in enumerate(all_folders, 1):
                self.cli.poutput(f'{i:2d}. "{folder.get("full_name")}" (ID: {folder.get("id")}, Name: \"{folder.get("name")}\")')

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
            course_id = course['id']

            all_assignments = self.canvas_client.get_assignments_for_course(course_id)

            assignment_groups = self.canvas_client.canvas_re.make_request(f'/courses/{course_id}/assignment_groups')
            group_map = {group['id']: group['name'] for group in assignment_groups}

            hdr = f"Available assignments for course {course_id}"
            self.cli.poutput(f"\n{hdr}\n" + "=" * len(hdr))

            for i, assignment in enumerate(all_assignments, 1):
                due_date = assignment.get('due_at', 'No due date')[:10] if assignment.get('due_at') else 'No due date'
                points = assignment.get('points_possible', 'N/A')
                group_id = assignment.get('assignment_group_id')
                group_name = group_map.get(group_id, 'No group') if group_id else 'No group'

                self.cli.poutput(f"{i:2d}. {assignment['name']}")
                self.cli.poutput(f"    Due: {due_date} | Points: {points} | Group: {group_name} | ID: {assignment['id']}")

            if not all_assignments:
                self.cli.poutput("No assignments available in the course.")
            else:
                self.cli.poutput(f"Total assignments available: {len(all_assignments)}")
                self.cli.poutput(f"\n💡 Use 'upload assignment grades {all_assignments[0]['id']} --file <csv_file>' to upload grades")

        except Exception as e:
            self.cli.poutput(str(e))

    def show_assignment_details(self, assignment_id: int) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course['id']
            all_assignments = self.canvas_client.get_assignments_for_course(course_id)

            assignment = next((a for a in all_assignments if a['id'] == assignment_id), None)

            if not assignment:
                self.cli.poutput(f"Cannot find assignment with ID: {assignment_id} in course '{course['name']}'")
                return

            assignment_groups = self.canvas_client.canvas_re.make_request(f'/courses/{course_id}/assignment_groups')
            group_map = {group['id']: group['name'] for group in assignment_groups}

            self.cli.poutput(f"\nAssignment Details: {assignment['name']}")
            self.cli.poutput("=" * (len(assignment['name']) + 20))

            self.cli.poutput(f"ID: {assignment['id']}")

            description = assignment.get('description')
            if description:
                self.cli.poutput(f"Description: {description}")

            group_id = assignment.get('assignment_group_id')
            group_name = group_map.get(group_id, 'No group') if group_id else 'No group'
            self.cli.poutput(f"Group: {group_name}")

            points = assignment.get('points_possible', 'N/A')
            self.cli.poutput(f"Points: {points}")

            due_date = assignment.get('due_at')
            if due_date:
                self.cli.poutput(f"Due: {due_date[:10]} {due_date[11:16]} UTC")
            else:
                self.cli.poutput("Due: No due date")

            lock_at = assignment.get('lock_at')
            if lock_at:
                self.cli.poutput(f"Locked after: {lock_at[:10]} {lock_at[11:16]} UTC")

            unlock_at = assignment.get('unlock_at')
            if unlock_at:
                self.cli.poutput(f"Available from: {unlock_at[:10]} {unlock_at[11:16]} UTC")

            submission_types = assignment.get('submission_types', [])
            if submission_types:
                self.cli.poutput(f"Submission types: {', '.join(submission_types)}")

            allowed_attempts = assignment.get('allowed_attempts')
            if allowed_attempts and allowed_attempts > 0:
                self.cli.poutput(f"Allowed attempts: {allowed_attempts}")
            elif allowed_attempts == -1:
                self.cli.poutput("Allowed attempts: Unlimited")

            self.cli.poutput(f"Published: {'Yes' if assignment.get('published') else 'No'}")
            self.cli.poutput(f"Status: {assignment.get('workflow_state', 'Unknown')}")

            has_submissions = assignment.get('has_submitted_submissions', False)
            self.cli.poutput(f"Has submissions: {'Yes' if has_submissions else 'No'}")

            needs_grading = assignment.get('needs_grading_count', 0)
            if needs_grading > 0:
                self.cli.poutput(f"Needs grading: {needs_grading}")

            self.cli.poutput(f"URL: {assignment.get('html_url', 'N/A')}")

        except Exception as e:
            self.cli.poutput(str(e))

    def list_students(self) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course['id']
            all_students = self.canvas_client.get_students_for_course(course_id)

            hdr = f"Available students for course {course_id}"
            self.cli.poutput(f"\n{hdr}\n" + "=" * len(hdr))

            for i, student in enumerate(all_students, 1):
                student_id = str(student['id'])
                name = student.get('name', 'No name')[:29]
                email = student.get('email', 'No email')[:29]

                self.cli.poutput(f"{student_id:<10} {name:<30} {email:<30}")

            if not all_students:
                self.cli.poutput("No students available in the course.")
            else:
                self.cli.poutput(f"Total students available: {len(all_students)}")
                self.cli.poutput(f"\n💡 Use 'download students --file students.csv' to save full list to CSV")

        except Exception as e:
            self.cli.poutput(str(e))

    def download_students_csv(self, filepath: Optional[str]) -> None:
        """Export student list with IDs to CSV"""

        course = self.require_course()

        if not course:
            return

        try:
            course_id = course['id']
            course_name = course['name']

            all_students = self.canvas_client.get_students_for_course(course_id)

            if not all_students:
                self.cli.poutput("No students found in this course")
                return

            if not filepath:
                safe_course_name = "".join(c for c in course_name if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"students_{course_id}_{safe_course_name.replace(' ', '_')}.csv"
            else:
                filename = filepath

            with open(filename, 'w', newline='', encoding=APP_CONFIG['default_encoding']) as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['canvas_id', 'name', 'email', 'sis_user_id'])

                for student in all_students:
                    writer.writerow([
                        student['id'],
                        student.get('name', ''),
                        student.get('email', ''),
                        student.get('sis_user_id', '')
                    ])

            self.cli.poutput(f"Student list exported to: {filename}")
            self.cli.poutput(f"Total students: {len(all_students)}")
        except Exception as e:
            self.cli.perror(f"Failed to export student list: {e}")

    def download_assignment_grades_csv(self, assignment_id: int, output_file: Optional[str]) -> None:
        """Export course assignments to CSV"""

        course = self.require_course()

        if not course:
            return

        course_id = course['id']

        try:
            all_assignments = self.canvas_client.get_assignments_for_course(course_id)

            assignment = next((a for a in all_assignments if a['id'] == assignment_id), None)

            if not assignment:
                self.cli.poutput(f"Cannot find assignment with ID: {assignment_id} in course '{course['name']}'")
                return

            self.cli.poutput(f"\nGrade Download Summary:")
            self.cli.poutput(f"   Course: {course['name']}")
            self.cli.poutput(f"   Assignment: {assignment['name']}")

            students = self.canvas_client.get_students_for_course(course_id)
            submissions = self.canvas_client.get_submissions_for_assignment(course_id, assignment_id)

            student_map = {student['id']: student for student in students}

            if not output_file:
                safe_assignment_name = "".join(c for c in assignment['name'] if c.isalnum() or c in (' ', '-', '_')).strip()
                output_file = f"grades_{course_id}_{safe_assignment_name.replace(' ', '_')}.csv"

            grade_data = []
            for submission in submissions:
                user_id = submission.get('user_id')
                if user_id in student_map:
                    student = student_map[user_id]
                    grade_data.append({
                        'canvas_id': user_id,
                        'name': student.get('name', ''),
                        'email': student.get('email', ''),
                        'grade': submission.get('score', ''),
                        'submitted_at': submission.get('submitted_at', ''),
                        'workflow_state': submission.get('workflow_state', ''),
                        'late': submission.get('late', False)
                    })

            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['canvas_id', 'name', 'email', 'grade', 'submitted_at', 'workflow_state', 'late']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(grade_data)

            print(f"Downloaded {len(grade_data)} grades to: {output_file}")
            return output_file

        except Exception as e:
            print(f"Failed to download grades: {e}")

    def upload_assignment_grades_csv(self, assignment_id: int, csv_filepath: str, root_dir: Optional[str]) -> None:
        """Upload course assignment grades from a file in CSV format"""

        course = self.require_course()

        if not course:
            return

        course_id = course['id']

        try:
            canvas_grades_uploader = CanvasGradesUploader(self.cli, self.canvas_client, csv_filepath, root_dir)

            all_assignments = self.canvas_client.get_assignments_for_course(course_id)

            assignment = next((a for a in all_assignments if a['id'] == assignment_id), None)

            if not assignment:
                self.cli.poutput(f"Cannot find assignment with ID: {assignment_id} in course '{course['name']}'")
                return

            canvas_grades_uploader.upload_grades(course_id, assignment_id, assignment['name'])
        except Exception as e:
            self.cli.poutput(f"Error uploading grades to Canvas: {e}")

    def create_assignment(self, args: argparse.Namespace) -> None:
        course = self.require_course()
        if not course:
            return

        assignment_data = {'name': args.name}
        if args.points:
            assignment_data['points_possible'] = args.points
        if args.due_date:
            assignment_data['due_at'] = args.due_date
        if args.description:
            assignment_data['description'] = args.description
        if args.published:
            assignment_data['published'] = True

        try:
            new_assignment = self.canvas_client.create_assignment(course['id'], {'assignment': assignment_data})
            self.cli.poutput(f"✅ Assignment created: {new_assignment['name']} (ID: {new_assignment['id']})")
        except Exception as e:
            self.cli.perror(f"Failed to create assignment: {e}")

    def delete_assignment(self, assignment_id: int) -> None:
        course = self.require_course()
        if not course:
            return

        try:
            all_assignments = self.canvas_client.get_assignments_for_course(course['id'])
            assignment = next((a for a in all_assignments if a['id'] == assignment_id), None)

            if not assignment:
                self.cli.poutput(f"Cannot find assignment with ID: {assignment_id} in course '{course['name']}'")
                return

            self.cli.poutput(f"⚙️ Deleting assignment: {assignment['name']} (ID: {assignment_id}) …")
            deleted_assignment = self.canvas_client.delete_assignment(course['id'], assignment_id)
            self.cli.poutput(f"✅ Assignment deleted.")
        except Exception as e:
            self.cli.perror(f"Failed to delete assignment: {e}")

    def list_quizzes(self) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course['id']
            all_quizzes = self.canvas_client.get_quizzes_for_course(course_id)

            assignment_groups = self.canvas_client.canvas_re.make_request(f'/courses/{course_id}/assignment_groups')
            group_map = {group['id']: group['name'] for group in assignment_groups}

            hdr = f"Available quizzes for course {course_id}"
            self.cli.poutput(f"\n{hdr}\n" + "=" * len(hdr))

            for i, quiz in enumerate(all_quizzes, 1):
                due_date = quiz.get('due_at', 'No due date')[:10] if quiz.get('due_at') else 'No due date'
                points = quiz.get('points_possible', 'N/A')
                group_id = quiz.get('assignment_group_id')
                group_name = group_map.get(group_id, 'No group') if group_id else 'No group'
                question_count = quiz.get('question_count', 0)
                published = 'Yes' if quiz.get('published') else 'No'

                self.cli.poutput(f"{i:2d}. {quiz['title']}")
                self.cli.poutput(f"    Due: {due_date} | Points: {points} | Questions: {question_count} | Published: {published}")
                self.cli.poutput(f"    Group: {group_name} | ID: {quiz['id']}")

            if not all_quizzes:
                self.cli.poutput("No quizzes available in the course.")
            else:
                self.cli.poutput(f"Total quizzes available: {len(all_quizzes)}")

        except Exception as e:
            self.cli.poutput(str(e))

    def show_quiz_details(self, quiz_id: int) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course['id']
            all_quizzes = self.canvas_client.get_quizzes_for_course(course_id)

            quiz = next((q for q in all_quizzes if q['id'] == quiz_id), None)

            if not quiz:
                self.cli.poutput(f"Cannot find quiz with ID: {quiz_id} in course '{course['name']}'")
                return

            assignment_groups = self.canvas_client.canvas_re.make_request(f'/courses/{course_id}/assignment_groups')
            group_map = {group['id']: group['name'] for group in assignment_groups}

            self.cli.poutput(f"\nQuiz Details: {quiz['title']}")
            self.cli.poutput("=" * (len(quiz['title']) + 15))

            self.cli.poutput(f"ID: {quiz['id']}")

            description = quiz.get('description')
            if description:
                self.cli.poutput(f"Description: {description}")

            self.cli.poutput(f"Type: {quiz.get('quiz_type', 'N/A')}")

            group_id = quiz.get('assignment_group_id')
            group_name = group_map.get(group_id, 'No group') if group_id else 'No group'
            self.cli.poutput(f"Group: {group_name}")

            points = quiz.get('points_possible', 'N/A')
            self.cli.poutput(f"Points: {points}")

            question_count = quiz.get('question_count', 0)
            self.cli.poutput(f"Questions: {question_count}")

            time_limit = quiz.get('time_limit')
            if time_limit:
                self.cli.poutput(f"Time limit: {time_limit} minutes")

            due_date = quiz.get('due_at')
            if due_date:
                self.cli.poutput(f"Due: {due_date[:10]} {due_date[11:16]} UTC")
            else:
                self.cli.poutput("Due: No due date")

            lock_at = quiz.get('lock_at')
            if lock_at:
                self.cli.poutput(f"Locked after: {lock_at[:10]} {lock_at[11:16]} UTC")

            unlock_at = quiz.get('unlock_at')
            if unlock_at:
                self.cli.poutput(f"Available from: {unlock_at[:10]} {unlock_at[11:16]} UTC")

            allowed_attempts = quiz.get('allowed_attempts')
            if allowed_attempts and allowed_attempts > 0:
                self.cli.poutput(f"Allowed attempts: {allowed_attempts}")
            elif allowed_attempts == -1:
                self.cli.poutput("Allowed attempts: Unlimited")

            self.cli.poutput(f"Shuffle answers: {'Yes' if quiz.get('shuffle_answers') else 'No'}")
            self.cli.poutput(f"Show correct answers: {'Yes' if quiz.get('show_correct_answers') else 'No'}")
            self.cli.poutput(f"One question at a time: {'Yes' if quiz.get('one_question_at_a_time') else 'No'}")
            self.cli.poutput(f"Can't go back: {'Yes' if quiz.get('cant_go_back') else 'No'}")

            access_code = quiz.get('access_code')
            if access_code:
                self.cli.poutput(f"Access code: {access_code}")

            self.cli.poutput(f"Scoring policy: {quiz.get('scoring_policy', 'N/A')}")
            self.cli.poutput(f"Hide results: {quiz.get('hide_results', 'N/A')}")

            self.cli.poutput(f"Published: {'Yes' if quiz.get('published') else 'No'}")
            self.cli.poutput(f"Status: {quiz.get('workflow_state', 'Unknown')}")

            locked = quiz.get('locked_for_user', False)
            self.cli.poutput(f"Locked for user: {'Yes' if locked else 'No'}")

            if locked and quiz.get('lock_explanation'):
                self.cli.poutput(f"Lock reason: {quiz.get('lock_explanation')}")

            self.cli.poutput(f"URL: {quiz.get('html_url', 'N/A')}")

        except Exception as e:
            self.cli.poutput(str(e))

    def download_quiz_questions(self, quiz_id: int, output_file: Optional[str], markdown: bool = False) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course['id']
            course_name = course['name']

            all_quizzes = self.canvas_client.get_quizzes_for_course(course_id)
            quiz = next((q for q in all_quizzes if q['id'] == quiz_id), None)

            if not quiz:
                self.cli.poutput(f"Cannot find quiz with ID: {quiz_id} in course '{course['name']}'")
                return

            questions = self.canvas_client.get_quiz_questions(course_id, quiz_id)

            if not questions:
                self.cli.poutput(f"No questions found for quiz '{quiz['title']}'")
                return

            if not output_file:
                safe_quiz_title = "".join(c for c in quiz['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
                ext = 'md' if markdown else 'json'
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

                time_limit = quiz.get('time_limit')
                if time_limit:
                    md_content += f"- **Time Limit:** {time_limit} minutes\n"

                due_at = quiz.get('due_at')
                if due_at:
                    md_content += f"- **Due:** {due_at[:10]} {due_at[11:16]} UTC\n"

                lock_at = quiz.get('lock_at')
                if lock_at:
                    md_content += f"- **Locked After:** {lock_at[:10]} {lock_at[11:16]} UTC\n"

                unlock_at = quiz.get('unlock_at')
                if unlock_at:
                    md_content += f"- **Available From:** {unlock_at[:10]} {unlock_at[11:16]} UTC\n"

                allowed_attempts = quiz.get('allowed_attempts')
                if allowed_attempts:
                    if allowed_attempts == -1:
                        md_content += "- **Attempts:** Unlimited\n"
                    else:
                        md_content += f"- **Attempts:** {allowed_attempts}\n"

                md_content += f"- **Published:** {'Yes' if quiz.get('published') else 'No'}\n"
                md_content += f"- **Shuffle Answers:** {'Yes' if quiz.get('shuffle_answers') else 'No'}\n"
                md_content += f"- **One Question at a Time:** {'Yes' if quiz.get('one_question_at_a_time') else 'No'}\n"
                md_content += f"- **Can't Go Back:** {'Yes' if quiz.get('cant_go_back') else 'No'}\n"

                access_code = quiz.get('access_code')
                if access_code:
                    md_content += f"- **Access Code:** {access_code}\n"

                md_content += f"- **Scoring Policy:** {quiz.get('scoring_policy', 'N/A')}\n"
                md_content += f"- **Hide Results:** {quiz.get('hide_results', 'N/A')}\n"
                md_content += f"- **URL:** {quiz.get('html_url', 'N/A')}\n"

                md_content += "\n"

                description = quiz.get('description')
                if description:
                    md_content += "## Description\n\n"
                    md_content += markdownify(description, heading_style="ATX", strip=['script', 'style'])
                    md_content += "\n\n"

                md_content += "## Questions\n\n"

                for i, question in enumerate(questions, 1):
                    q_name = question.get('question_name', f'Question {i}')
                    q_type = question.get('question_type', 'unknown')
                    q_points = question.get('points_possible', 0)

                    md_content += f"### Question {i}: {q_name}\n\n"
                    md_content += f"**Type:** {q_type}  \n"
                    md_content += f"**Points:** {q_points}\n\n"

                    q_text = question.get('question_text')
                    if q_text:
                        md_content += markdownify(q_text, heading_style="ATX", strip=['script', 'style'])
                        md_content += "\n\n"

                    answers = question.get('answers', [])
                    if answers and q_type != 'essay_question':
                        md_content += "**Answer Options:**\n\n"
                        for ans in answers:
                            ans_text = ans.get('text', '')
                            ans_weight = ans.get('weight', 0)
                            is_correct = ans_weight > 0

                            if is_correct:
                                md_content += f"- [x] **{ans_text}** (correct)\n"
                            else:
                                md_content += f"- [ ] {ans_text}\n"
                        md_content += "\n"

                    correct_comments = question.get('correct_comments')
                    if correct_comments:
                        md_content += "**Correct Feedback:**\n\n"
                        md_content += markdownify(correct_comments, heading_style="ATX", strip=['script', 'style'])
                        md_content += "\n\n"

                    incorrect_comments = question.get('incorrect_comments')
                    if incorrect_comments:
                        md_content += "**Incorrect Feedback:**\n\n"
                        md_content += markdownify(incorrect_comments, heading_style="ATX", strip=['script', 'style'])
                        md_content += "\n\n"

                    neutral_comments = question.get('neutral_comments')
                    if neutral_comments:
                        md_content += "**Neutral Feedback:**\n\n"
                        md_content += markdownify(neutral_comments, heading_style="ATX", strip=['script', 'style'])
                        md_content += "\n\n"

                    md_content += "---\n\n"

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(md_content)

                self.cli.poutput(f"Downloaded {len(questions)} questions to: {filename}")
            else:
                import json

                quiz_details = {
                    'id': quiz.get('id'),
                    'title': quiz.get('title'),
                    'description': quiz.get('description'),
                    'quiz_type': quiz.get('quiz_type'),
                    'points_possible': quiz.get('points_possible'),
                    'question_count': quiz.get('question_count'),
                    'time_limit': quiz.get('time_limit'),
                    'due_at': quiz.get('due_at'),
                    'lock_at': quiz.get('lock_at'),
                    'unlock_at': quiz.get('unlock_at'),
                    'published': quiz.get('published'),
                    'allowed_attempts': quiz.get('allowed_attempts'),
                    'shuffle_answers': quiz.get('shuffle_answers'),
                    'show_correct_answers': quiz.get('show_correct_answers'),
                    'one_question_at_a_time': quiz.get('one_question_at_a_time'),
                    'cant_go_back': quiz.get('cant_go_back'),
                    'access_code': quiz.get('access_code'),
                    'scoring_policy': quiz.get('scoring_policy'),
                    'hide_results': quiz.get('hide_results'),
                    'html_url': quiz.get('html_url'),
                    'workflow_state': quiz.get('workflow_state'),
                    'locked_for_user': quiz.get('locked_for_user'),
                    'lock_explanation': quiz.get('lock_explanation')
                }

                data = {
                    'quiz': quiz_details,
                    'questions': questions
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                self.cli.poutput(f"Downloaded {len(questions)} questions to: {filename}")

        except Exception as e:
            self.cli.poutput(f"Failed to download quiz questions: {e}")

    def download_quiz_submissions(self, quiz_id: int, output_dir: Optional[str], markdown: bool = False) -> None:
        course = self.require_course()

        if not course:
            return

        try:
            course_id = course['id']

            all_quizzes = self.canvas_client.get_quizzes_for_course(course_id)
            quiz = next((q for q in all_quizzes if q['id'] == quiz_id), None)

            if not quiz:
                self.cli.poutput(f"Cannot find quiz with ID: {quiz_id} in course '{course['name']}'")
                return

            assignment_id = quiz.get('assignment_id')
            if not assignment_id:
                self.cli.poutput(f"Quiz '{quiz['title']}' has no associated assignment_id. Cannot retrieve submission answers.")
                return

            submissions_data = self.canvas_client.get_quiz_submissions(course_id, quiz_id)
            submissions = submissions_data.get('quiz_submissions', [])

            if not submissions:
                self.cli.poutput(f"No submissions found for quiz '{quiz['title']}'")
                return

            students = self.canvas_client.get_students_for_course(course_id)
            student_map = {s['id']: s for s in students}

            assignment_submissions = self.canvas_client.canvas_re.make_request(
                f'/courses/{course_id}/assignments/{assignment_id}/submissions?per_page=100&include[]=submission_history&include[]=user'
            )

            assignment_sub_map = {}
            if isinstance(assignment_submissions, list):
                for sub in assignment_submissions:
                    assignment_sub_map[sub['user_id']] = sub

            if not output_dir:
                safe_quiz_title = "".join(c for c in quiz['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
                output_dir = f"quiz_{quiz_id}_{safe_quiz_title.replace(' ', '_')}_submissions"

            import os
            os.makedirs(output_dir, exist_ok=True)

            import json
            from markdownify import markdownify
            count = 0

            for submission in submissions:
                user_id = submission['user_id']
                student = student_map.get(user_id, {'name': f'Unknown ({user_id})', 'email': 'N/A'})

                if markdown:
                    md_content = f"# Quiz Submission: {quiz.get('title', 'Quiz')}\n\n"

                    md_content += "**Student Information**\n\n"
                    md_content += f"- **Name:** {student.get('name', 'Unknown')}\n"
                    md_content += f"- **Email:** {student.get('email', 'N/A')}\n"
                    md_content += f"- **User ID:** {user_id}\n"
                    md_content += f"- **Submission ID:** {submission['id']}\n\n"

                    md_content += "**Submission Details**\n\n"
                    md_content += f"- **Started:** {submission.get('started_at', 'N/A')}\n"
                    md_content += f"- **Finished:** {submission.get('finished_at', 'N/A')}\n"
                    md_content += f"- **Time Spent:** {submission.get('time_spent', 0)} seconds\n"
                    md_content += f"- **Attempt:** {submission.get('attempt', 1)}\n"
                    md_content += f"- **Score:** {submission.get('score', 0)}/{submission.get('quiz_points_possible', 0)}\n"
                    md_content += f"- **Status:** {submission.get('workflow_state', 'Unknown')}\n"
                    md_content += f"- **Quiz URL:** {submission.get('html_url', 'N/A')}\n\n"

                    assignment_sub = assignment_sub_map.get(user_id)
                    if assignment_sub and 'submission_history' in assignment_sub and assignment_sub['submission_history']:
                        history = assignment_sub['submission_history'][0]
                        if 'submission_data' in history:
                            answers = history['submission_data']
                            if answers:
                                md_content += "## Student Answers\n\n"

                                for ans in answers:
                                    q_id = ans.get('question_id', 'Unknown')
                                    ans_text = ans.get('text', '')
                                    points = ans.get('points', 0)
                                    correct = ans.get('correct', 'undefined')

                                    md_content += f"### Question ID: {q_id}\n\n"
                                    md_content += f"**Points:** {points}  \n"
                                    md_content += f"**Correct:** {correct}\n\n"

                                    if ans_text:
                                        md_content += "**Answer:**\n\n"
                                        md_content += markdownify(ans_text, heading_style="ATX", strip=['script', 'style'])
                                        md_content += "\n\n"
                                    else:
                                        md_content += "**Answer:** *(no answer provided)*\n\n"

                                    md_content += "---\n\n"

                    safe_student_name = "".join(c for c in student.get('name', f'user_{user_id}') if c.isalnum() or c in (' ', '-', '_')).strip()
                    filename = os.path.join(output_dir, f"submission_{submission['id']}_{safe_student_name.replace(' ', '_')}.md")

                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(md_content)
                else:
                    enriched_submission = {
                        'id': submission['id'],
                        'user_id': user_id,
                        'student_name': student.get('name'),
                        'student_email': student.get('email'),
                        'started_at': submission.get('started_at'),
                        'finished_at': submission.get('finished_at'),
                        'score': submission.get('score'),
                        'kept_score': submission.get('kept_score'),
                        'attempt': submission.get('attempt'),
                        'time_spent': submission.get('time_spent'),
                        'workflow_state': submission.get('workflow_state'),
                        'html_url': submission.get('html_url'),
                        'quiz_id': submission.get('quiz_id'),
                        'quiz_points_possible': submission.get('quiz_points_possible')
                    }

                    assignment_sub = assignment_sub_map.get(user_id)
                    if assignment_sub and 'submission_history' in assignment_sub and assignment_sub['submission_history']:
                        history = assignment_sub['submission_history'][0]
                        if 'submission_data' in history:
                            enriched_submission['answers'] = history['submission_data']

                    safe_student_name = "".join(c for c in student.get('name', f'user_{user_id}') if c.isalnum() or c in (' ', '-', '_')).strip()
                    filename = os.path.join(output_dir, f"submission_{submission['id']}_{safe_student_name.replace(' ', '_')}.json")

                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(enriched_submission, f, indent=2, ensure_ascii=False)

                count += 1

            self.cli.poutput(f"Downloaded {count} submissions to directory: {output_dir}")

        except Exception as e:
            self.cli.poutput(f"Failed to download quiz submissions: {e}")