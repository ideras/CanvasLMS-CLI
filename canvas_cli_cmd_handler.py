#!/usr/bin/env python3
import argparse
import re
import csv
from typing import Optional, Dict
from cmd2 import Cmd
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
        
        self.canvas_grades_uploader = CanvasGradesUploader(cli, self.canvas_client)
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
            self.cli.poutput(f"Selected course: {self.selected_course['name']}")
                
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

        hdr = "Available Courses"
        if name_rx or code_rx:
            hdr += " (filtered)"

        full_hdr = f"{hdr}: {count}/{total}"
        self.cli.poutput(f"\n{full_hdr}\n" + "=" * len(full_hdr))

        for i, course in enumerate(filtered, 1):
            is_current = self.selected_course and course.get("id") == self.selected_course.get("id")

            status = " 📍 CURRENT" if is_current else ""
            self.cli.poutput(f'{i:2d}. "{course.get("name")}" (ID: {course.get("id")}){status}')

        if not filtered:
            self.cli.poutput("No courses matched your filter.")
        else:
            self.cli.poutput("\n💡 Use 'use course <canvas_id>' to select a course")
            self.cli.poutput(f"    Examples: 'use course {filtered[0]['id']}'")

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
            
            hdr = f"Available assignments for course {course_id}"
            self.cli.poutput(f"\n{hdr}\n" + "=" * len(hdr))

            for i, assignment in enumerate(all_assignments, 1):
                due_date = assignment.get('due_at', 'No due date')[:10] if assignment.get('due_at') else 'No due date'
                points = assignment.get('points_possible', 'N/A')
                
                self.cli.poutput(f"{i:2d}. {assignment['name']}")
                self.cli.poutput(f"    Due: {due_date} | Points: {points} | ID: {assignment['id']}")

            if not all_assignments:
                self.cli.poutput("No assignments available in the course.")
            else:
                self.cli.poutput(f"Total assignments available: {len(all_assignments)}")
                self.cli.poutput(f"\n💡 Use 'upload assignment grades {all_assignments[0]['id']} --file <csv_file>' to upload grades")

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
    
    def upload_assignment_grades_csv(self, assignment_id: int, csv_filepath: Optional[str]) -> None:
        """Upload course assignment grades from a file in CSV format"""

        course = self.require_course()

        if not course:
            return
        
        course_id = course['id']

        try:
            self.canvas_grades_uploader.load_csv_file(csv_filepath)
            self.cli.poutput(f"Successfully loaded CSV file '{csv_filepath}'")

            if not self.canvas_grades_uploader.check_files_exists():
                return
            
            if not self.canvas_grades_uploader.convert_markdown_files():
                return
        
            all_assignments = self.canvas_client.get_assignments_for_course(course_id)

            assignment = next((a for a in all_assignments if a['id'] == assignment_id), None)

            if not assignment:
                self.cli.poutput(f"Cannot find assignment with ID: {assignment_id} in course '{course['name']}'")
                return
            
            self.canvas_grades_uploader.upload_all_files_to_course(course_id, assignment_id, assignment['name'])
            self.canvas_grades_uploader.upload_grades(course_id, assignment_id)
        except Exception as e:
            self.cli.poutput(f"Error uploading grades to Canvas: {e}")