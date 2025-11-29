import os
import requests
import posixpath
from typing import Optional, List, Dict
from canvas_request_executor import CanvasRequestExecutor
from config import FILE_UPLOAD_CONFIG

class CanvasClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = base_url
        self.token = token
        self.all_courses = None
        self.current_course = None
        self.canvas_re = CanvasRequestExecutor(base_url, token)

    def get_all_courses(self, force_refresh: bool = False) -> List[Dict]:
        """Return cached courses; refresh from Canvas if needed."""
        if force_refresh or not self.all_courses:
            self.all_courses = self.canvas_re.make_request(
                '/courses?enrollment_state=active&per_page=100'
            )
        return self.all_courses

    def get_folders_for_course(self, course_id: str) -> List[Dict]:
        """Get the list of folders in a course"""

        try:
            folders = self.canvas_re.make_request(f'/courses/{course_id}/folders')
            return folders
        except Exception as e:
            raise RuntimeError(f"Failed to get folders for course {course_id}: {e}") from e

    def get_assignments_for_course(self, course_id: int) -> List[Dict]:
        """List assignments for a course"""

        try:
            assignments = self.canvas_re.make_request(f'/courses/{course_id}/assignments?per_page=100&include[]=assignment_group')
            return assignments
        except Exception as e:
            raise RuntimeError(f"Failed to get assignments for course {course_id}: {e}") from e

    def get_submissions_for_assignment(self, course_id: int, assignment_id: int) -> List[Dict]:
        """Get submissions for a specific assignment"""

        try:
            return self.canvas_re.make_request(f'/courses/{course_id}/assignments/{assignment_id}/submissions?include[]=user&per_page=100')
        except Exception as e:
            raise RuntimeError(f"Failed to get submissions for assignment {assignment_id} in course {course_id}: {e}") from e

    def get_students_for_course(self, course_id: int) -> List[Dict]:
        """List students in a course"""

        try:
            students = self.canvas_re.make_request(f'/courses/{course_id}/users?enrollment_type[]=student&per_page=300')
            return students
        except Exception as e:
            raise RuntimeError(f"Failed to get students for course {course_id}: {e}") from e

    def get_quizzes_for_course(self, course_id: int) -> List[Dict]:
        """List quizzes in a course"""

        try:
            quizzes = self.canvas_re.make_request(f'/courses/{course_id}/quizzes?per_page=100')
            return quizzes
        except Exception as e:
            raise RuntimeError(f"Failed to get quizzes for course {course_id}: {e}") from e

    def get_quiz_questions(self, course_id: int, quiz_id: int) -> List[Dict]:
        """Get questions for a specific quiz"""

        try:
            questions = self.canvas_re.make_request(f'/courses/{course_id}/quizzes/{quiz_id}/questions?per_page=100')
            return questions
        except Exception as e:
            raise RuntimeError(f"Failed to get questions for quiz {quiz_id} in course {course_id}: {e}") from e

    def get_quiz_submissions(self, course_id: int, quiz_id: int) -> Dict:
        """Get submissions for a specific quiz"""

        try:
            return self.canvas_re.make_request(f'/courses/{course_id}/quizzes/{quiz_id}/submissions?per_page=100')
        except Exception as e:
            raise RuntimeError(f"Failed to get submissions for quiz {quiz_id} in course {course_id}: {e}") from e

    def get_assignment_submissions_with_attachments(self, course_id: int, assignment_id: int) -> List[Dict]:
        """Get submissions for an assignment including attachments and submission history"""

        try:
            result = self.canvas_re.make_request(
                f'/courses/{course_id}/assignments/{assignment_id}/submissions?'
                f'include[]=user&include[]=submission_history&include[]=attachments&per_page=100'
            )
            # Canvas API returns a list, but make_request might return dict in some cases
            return result if isinstance(result, list) else []
        except Exception as e:
            raise RuntimeError(f"Failed to get submissions with attachments for assignment {assignment_id} in course {course_id}: {e}") from e

    def download_file_from_url(self, file_url: str, local_path: str, show_progress: bool = True) -> bool:
        """Download a file from Canvas URL with authentication and progress tracking"""

        if not self.token:
            print("Error: Canvas API token not configured")
            return False

        try:
            # Ensure we have proper authentication headers
            headers = {'Authorization': f'Bearer {self.token}'}

            # Make the request with stream=True for large files
            response = requests.get(file_url, headers=headers, stream=True, timeout=300)
            response.raise_for_status()

            # Get file size for progress tracking
            file_size = int(response.headers.get('content-length', 0))

            # Download the file in chunks
            downloaded = 0
            chunk_size = 8192

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Show progress for large files
                        if show_progress and file_size > 1024 * 1024:  # > 1MB
                            progress = (downloaded / file_size) * 100
                            print(f"\rDownloading: {progress:.1f}% ({downloaded // 1024}KB/{file_size // 1024}KB)", end="")

            if show_progress and file_size > 1024 * 1024:
                print()  # New line after progress

            return True

        except Exception as e:
            print(f"Failed to download file from {file_url}: {e}")
            return False

    def ensure_course_folder(self, course_id: int, folder_path: str) -> Dict:
        """
        Ensure the POSIX folder path exists under the course root.
        Returns the final folder object (as dict).
        Example: ensure_course_folder(12345, "Grade_Feedback/Homework1")
        """
        norm = posixpath.normpath(folder_path).lstrip("/")
        parts = [p for p in norm.split("/") if p and p != "."]

        try:
            chain: List[Dict] = self.canvas_re.make_request(f"/courses/{course_id}/folders/by_path/{norm}")

            return chain[-1]
        except Exception:
            pass

        root = self.canvas_re.make_request(f"/courses/{course_id}/folders/root")
        current = root

        if not parts:
            return current

        for seg in parts:
            children = self.canvas_re.make_request(f"/folders/{current['id']}/folders")
            nxt = next((f for f in children if f.get("name") == seg), None)
            if not nxt:
                nxt = self.canvas_re.make_request(f"/folders/{current['id']}/folders", method="POST", data={"name": seg})

            current = nxt

        return current

    def upload_file_to_course(self, file_path: str, course_id: int, parent_folder_id: int) -> Dict:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        max_size = FILE_UPLOAD_CONFIG['max_file_size_mb'] * 1024 * 1024

        if file_size > max_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {max_size} bytes)")

        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in FILE_UPLOAD_CONFIG['allowed_extensions']:
            raise ValueError(f"File type not allowed: {file_ext}")

        file_info = {
            'name': os.path.basename(file_path),
            'size': file_size,
            'content_type': self._get_content_type(file_ext),
            'parent_folder_id': parent_folder_id
        }

        upload_params = self.canvas_re.make_request(f"/courses/{course_id}/files", method="POST", data=file_info)

        with open(file_path, 'rb') as f:
            files = {'file': f}
            response2 = requests.post(
                upload_params['upload_url'],
                data=upload_params['upload_params'],
                files=files,
                timeout=FILE_UPLOAD_CONFIG['upload_timeout']
            )
            response2.raise_for_status()

        file_data = response2.json()

        file_info = {
            'id': file_data['id'],
            'name': file_data['display_name'],
            'url': f"{self.base_url}/courses/{course_id}/files/{file_data['id']}",
            'download_url': f"{self.base_url}/courses/{course_id}/files/{file_data['id']}/download",
            'public_url': file_data.get('url', '')
        }

        return file_info

    def submit_grade(self, course_id: int, assignment_id: int, student_id: int,
                    grade: float, html_comment: str = None) -> dict:
        """Submit a grade with optional HTML comment"""
        endpoint = f'/courses/{course_id}/assignments/{assignment_id}/submissions/{student_id}'

        data = {
            'submission': {
                'posted_grade': str(grade)
            }
        }

        if html_comment:
            data['comment'] = {
                'text_comment': html_comment
            }

        return self.canvas_re.make_request(endpoint, method='PUT', data=data)

    def update_grades(self, course_id: int, assignment_id: int, grade_data: dict) -> dict:
        """Submit a grade with optional HTML comment"""
        endpoint = f'/courses/{course_id}/assignments/{assignment_id}/submissions/update_grades'

        data = { "grade_data": grade_data }

        return self.canvas_re.make_request(endpoint, method='POST', data=data)

    def query_progress(self, progress_id: int) -> dict:
        """Query a Canvas Progress object"""
        endpoint = f'/progress/{progress_id}'

        return self.canvas_re.make_request(endpoint)

    def create_assignment(self, course_id: int, assignment_data: dict) -> dict:
        """Create a new assignment in a course"""
        endpoint = f'/courses/{course_id}/assignments'
        return self.canvas_re.make_request(endpoint, method='POST', data=assignment_data)

    def delete_assignment(self, course_id: int, assignment_id: int) -> dict:
        """Delete an assignment from a course"""
        endpoint = f'/courses/{course_id}/assignments/{assignment_id}'
        return self.canvas_re.make_request(endpoint, method='DELETE')

    def _get_content_type(self, file_ext: str) -> str:
        """Get MIME type for file extension"""
        content_types = {
            '.pdf': 'application/pdf',
            '.md': 'text/markdown',
            '.txt': 'text/plain',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav'
        }
        return content_types.get(file_ext.lower(), 'application/octet-stream')
