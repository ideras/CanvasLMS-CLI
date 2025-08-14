import os
import pandas as pd
import time
from typing import List
from cmd2 import Cmd
from datetime import datetime
from pathlib import Path
from canvas_client import CanvasClient
from markdown_converter import MarkdownToPDFConverter

class CanvasGradesUploader:
    def __init__(self, cli: Cmd, canvas_client: CanvasClient):
        self.cli = cli
        self.canvas_client = canvas_client
        self.data_frame = None
        pass

    def load_csv_file(self, csv_file: str) -> None:
        """Load the CSV file with grades"""
        
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        
        try:
            self.data_frame = pd.read_csv(csv_file)

            valid_columns: List[str] = ["canvas_id", "student_id", "grade", "comment", "comments", "markdown_file", "pdf_file"]

            rename_map = {
                "canvas_id": "student_id",
                "comments": "comment",
            }

            self.data_frame.rename(columns=rename_map, inplace=True)

            invalid = [c for c in self.data_frame.columns if c not in valid_columns]
            if invalid:
                raise ValueError(f"Invalid column(s) in CSV file: {', '.join(invalid)}")
        
            self.cli.poutput(self.data_frame.columns)

            self.data_frame = self.data_frame.dropna(subset=['student_id', 'grade'])
            self.data_frame['student_id'] = self.data_frame['student_id'].astype(str).str.strip()
            self.data_frame['grade'] = pd.to_numeric(self.data_frame['grade'], errors='coerce')
            self.data_frame = self.data_frame.dropna(subset=['grade'])
            
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {e}") from e
        
    def check_files_exists(self) -> bool:
        if self.data_frame is None:
            raise RuntimeError("CSV file not loaded")
        
        if not any(column in self.data_frame.columns for column in ['markdown_file', 'pdf_file']):
            self.cli.poutput(f"The CSV file doesn't contains file comments")
            return True
        
        record_valid = True

        for index, row in self.data_frame.iterrows():
            markdown_file = str(row.get('markdown_file', '')).strip()
            pdf_file = str(row.get('pdf_file', '')).strip()
           
            if markdown_file:
                if os.path.exists(markdown_file):
                    if not markdown_file.lower().endswith('.md'):
                        self.cli.poutput(f"Invalid markdown file: {markdown_file}")
                        record_valid = False
                else:
                    self.cli.poutput(f"Markdown file: '{markdown_file}' doesn't exists")
                    record_valid = False           
 
            elif pdf_file and str(pdf_file).strip():
                pdf_file = str(pdf_file).strip()
                
                if os.path.exists(pdf_file):
                    if not pdf_file.lower().endswith('.pdf'):
                        self.cli.poutput(f"Invalid markdown file: {pdf_file}")
                        record_valid = False
                else:
                    self.cli.poutput(f"PDF file: '{pdf_file}' doesn't exists")
                    record_valid = False
        
        return record_valid
    
    def convert_markdown_files(self) -> bool:
        if self.data_frame is None:
            raise RuntimeError("CSV file not loaded")
        
        if not 'markdown_file' in self.data_frame.columns:
            self.cli.poutput(f"The CSV file doesn't contains Markdown file comments")
            return True

        md_converter = MarkdownToPDFConverter()

        for index, row in self.data_frame.iterrows():
            markdown_file = str(row.get('markdown_file', '')).strip()
                        
            if not markdown_file:
                continue

            md_filepath = Path(markdown_file)
            pdf_filepath = md_filepath.with_suffix(".pdf")
                    
            converted_pdf = md_converter.convert_file(md_filepath, pdf_filepath)

            if not converted_pdf:
                self.cli.poutput(f"Cannot convert file '{markdown_file}'")
                return False
            
            self.data_frame.at[index, 'pdf_file'] = str(pdf_filepath)
        
        return True
    
    def upload_all_files_to_course(self, course_id: int,  assignment_id: int = None, assignment_name: str = None) -> None:
        if self.data_frame is None:
            raise RuntimeError("CSV file not loaded")
        
        if not 'pdf_file' in self.data_frame.columns:
            self.cli.poutput(f"The CSV file doesn't contains PDF file comments")
            return
        
        folder_name = self._generate_feedback_folder_name(assignment_name, assignment_id)
        self.cli.poutput(f"Uploading files to course folder: {folder_name}")
        
        target_folder = self.canvas_client.ensure_course_folder(course_id, folder_name)

        for index, row in self.data_frame.iterrows():
            pdf_filepath = str(row.get('pdf_file', '')).strip()
                        
            if not pdf_filepath:
                continue

            filename = Path(pdf_filepath).name

            self.cli.poutput(f"Uploading file '{filename}'...")

            file_info = self.canvas_client.upload_file_to_course(pdf_filepath, course_id, target_folder['id']);

            self.data_frame.at[index, 'canvas_id'] = str(file_info['id'])
            self.data_frame.at[index, 'canvas_name'] = file_info['name']
            self.data_frame.at[index, 'canvas_url'] = str(file_info['url'])
            self.data_frame.at[index, 'canvas_download_url'] = str(file_info['download_url'])
            self.data_frame.at[index, 'canvas_folder_path'] = folder_name
            self.data_frame.at[index, 'canvas_public_url'] = str(file_info['public_url'])
        
        self.cli.poutput(f"{len(self.data_frame)} files were uploaded successfully.")

    def _generate_feedback_folder_name(self, assignment_name: str = None, assignment_id: int = None) -> str:
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

    
    def upload_grades(self, course_id: int, assignment_id: int) -> None:
        if self.data_frame is None:
            raise RuntimeError("CSV file not loaded")

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
            file_path = str(row.get('pdf_file', '')).strip()

            student_name = student_map[student_id]
            self.cli.poutput(f"Processing grade {grade} for {student_name} (ID: {student_id})...")
            
            final_comment = comment
            if file_path:
                canvas_url = str(row.get("canvas_url", ""))
                canvas_download_url = str(row.get("canvas_download_url", ""))
                canvas_name = str(row.get("canvas_name", ""))

                file_link = f'''
                <p>📄 <strong>Detailed feedback</strong></p>
                <p><a href="{canvas_url}" target="_blank">🔍 View</a><br>
                <a href="{canvas_download_url}">💾 Download File</a></p>
                '''

                if final_comment:
                    final_comment = f"{final_comment}<br>{file_link}"
                else:
                    final_comment = file_link

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

