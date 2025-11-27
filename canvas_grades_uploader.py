"""
Canvas Grades Uploader Module

This module provides functionality for uploading student grades and feedback files to Canvas LMS.
It handles the complete workflow of loading grade data, uploading PDF feedback files to organized
course folders, and submitting grades to Canvas assignments.

Classes:
    CanvasGradesUploader: Main class for handling grade uploads and file management

Key Features:
    - Upload PDF feedback files to organized course folders
    - Submit grades with text comments and file attachments
    - Validate student IDs against course roster
    - Generate HTML-formatted comments with file links
    - Track upload progress with real-time status updates
    - Automatic folder naming with timestamps and assignment names
"""

import time
from typing import Optional, List, Final
from datetime import datetime
from pathlib import Path
from cmd2 import Cmd
import pandas as pd
from canvas_client import CanvasClient
from canvas_grades_loader import CanvasGradesLoader

class CanvasGradesUploader:
    def __init__(self, cli: Cmd, canvas_client: CanvasClient, csv_filepath: str, root_dir: Optional[str]):
        self.cli = cli
        self.canvas_client = canvas_client
        self.grades_loader = CanvasGradesLoader(csv_filepath, root_dir)
        self.data_frame = self.grades_loader.data_frame

    def _upload_all_files_to_course(self, course_id: int,  assignment_id: Optional[int] = None, assignment_name: Optional[str] = None) -> None:
        if self.data_frame is None:
            raise RuntimeError("CSV file not loaded")

        if not 'pdf_eval_file' in self.data_frame.columns:
            self.cli.poutput(f"The CSV file doesn't contains PDF file comments")
            return

        folder_name = self._generate_feedback_folder_name(assignment_name, assignment_id)
        self.cli.poutput(f"Uploading files to course folder: {folder_name}")

        target_folder = self.canvas_client.ensure_course_folder(course_id, folder_name)

        for index, row in self.data_frame.iterrows():
            for column in self.grades_loader.pdf_file_columns:
                if column not in self.data_frame.columns:
                    continue

                pdf_filepath = str(row.get(column, '')).strip()

                if not pdf_filepath:
                    continue

                filename = Path(pdf_filepath).name

                self.cli.poutput(f"Uploading file '{filename}'...")

                file_info = self.canvas_client.upload_file_to_course(pdf_filepath, course_id, target_folder['id']);

                self.data_frame.at[index, f'{column}_canvas_id'] = str(file_info['id'])
                self.data_frame.at[index, f'{column}_canvas_name'] = file_info['name']
                self.data_frame.at[index, f'{column}_url'] = str(file_info['url'])
                self.data_frame.at[index, f'{column}_download_url'] = str(file_info['download_url'])
                self.data_frame.at[index, f'{column}_folder_path'] = folder_name
                self.data_frame.at[index, f'{column}_public_url'] = str(file_info['public_url'])

        self.cli.poutput(f"{len(self.data_frame)} files were uploaded successfully.")

    def _generate_feedback_folder_name(self, assignment_name: Optional[str] = None, assignment_id: Optional[int] = None) -> str:
        """Generate a unique folder name for feedback files"""

        today = datetime.now().strftime("%Y-%m-%d")

        if assignment_name:
            clean_name = "".join(c for c in assignment_name if c.isalnum() or c in (' ', '-', '_')).strip()
            clean_name = clean_name.replace(' ', '_')[:30]  # Limit length
            return f"Grade_Feedback/{today}_{clean_name}"
        elif assignment_id:
            return f"Grade_Feedback/{today}_Assignment_{assignment_id}"
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            return f"Grade_Feedback/{timestamp}_Manual_Upload"

    def _build_html_comments(self, row: pd.Series) -> str:
        html_comments = ""

        pdf_exam_file1_url = str(row.get("pdf_exam_file1_url", ""))
        if pdf_exam_file1_url:
            pdf_exam_file1_download_url = str(row.get("pdf_exam_file1_download_url", ""))

            html_comments += f"""<p>📄 <strong>Exam submission (Format 1)</strong></p>
            <p><a href="{pdf_exam_file1_url}" target="_blank">🔍 View</a><br>
            <a href="{pdf_exam_file1_download_url}">💾 Download File</a></p>"""

        pdf_exam_file2_url = str(row.get("pdf_exam_file2_url", ""))
        if pdf_exam_file2_url:
            pdf_exam_file2_download_url = str(row.get("pdf_exam_file2_download_url", ""))

            html_comments += f"""<p>📄 <strong>Exam submission (Format 2)</strong></p>
            <p><a href="{pdf_exam_file2_url}" target="_blank">🔍 View</a><br>
            <a href="{pdf_exam_file2_download_url}">💾 Download File</a></p>"""

        pdf_eval_file_url = str(row.get("pdf_eval_file_url", ""))
        if pdf_eval_file_url:
            pdf_eval_file_download_url = str(row.get("pdf_eval_file_download_url", ""))

            html_comments += f"""<p>📄 <strong>Detailed feedback</strong></p>
            <p><a href="{pdf_eval_file_url}" target="_blank">🔍 View</a><br>
            <a href="{pdf_eval_file_download_url}">💾 Download File</a></p>"""

        return html_comments

    def upload_grades(self, course_id: int, assignment_id: int, assignment_name: str) -> None:
        if self.data_frame is None:
            raise RuntimeError("CSV file not loaded")

        self._upload_all_files_to_course(course_id, assignment_id, assignment_name)

        # Get student information for validation
        students = self.canvas_client.get_students_for_course(course_id)
        student_map = {str(student['id']): student['name'] for student in students}

        # Check students
        for index, row in self.data_frame.iterrows():
            student_id = str(row['student_id'])

            if student_id not in student_map:
                raise RuntimeError(f"Student ID {student_id} not found in course")

        grade_data = {}

        for index, row in self.data_frame.iterrows():
            student_id = str(row['student_id'])
            grade = row['grade']
            comment = row.get('comment', '') if 'comment' in self.data_frame.columns else ''
            file_path = str(row.get('pdf_eval_file', '')).strip()

            student_name = student_map[student_id]
            self.cli.poutput(f"Processing grade {grade} for {student_name} (ID: {student_id})...")

            final_comment = comment
            if file_path:
                html_comments = self._build_html_comments(row)

                if final_comment:
                    final_comment = f"{final_comment}<br>{html_comments}"
                else:
                    final_comment = html_comments

            student_grade_data = { 'posted_grade': str(grade) }

            if final_comment:
                student_grade_data['text_comment'] = final_comment

            grade_data[student_id] = student_grade_data

        # Submit grades to Canvas Server
        if len(grade_data) > 0:
            self.cli.poutput(f"Sending {len(grade_data)} grades to Canvas Server...")
            progress_obj = self.canvas_client.update_grades(course_id, assignment_id, grade_data)

            progress_id = progress_obj['id']
            progress_status = progress_obj.get('workflow_state', 'failed')

            while not progress_status in ("completed", "failed", "canceled"):
                time.sleep(1)

                progress_obj = self.canvas_client.query_progress(progress_id)
                progress_status = progress_obj.get('workflow_state', 'failed')
                self.cli.poutput(f"Uploading grades. Status: {progress_status}")
