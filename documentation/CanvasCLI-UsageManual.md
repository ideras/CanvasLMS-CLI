# Canvas CLI Usage Manual

## Overview
Canvas CLI is a command-line interface for managing Canvas LMS courses, assignments, and grades. It allows you to interact with your Canvas instance directly from the terminal.

## Getting Started

## 🚀 Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/CanvasLMS-CLI.git
cd CanvasLMS-CLI
```

2. Install dependencies:

**Option A: Using uv (recommended):**

```bash
uv sync
```

**Option B: Using pip:**

```bash
pip install -r requirements.txt
```

3. Configure your Canvas settings:

```bash
cp config.example.py config.py
# Edit config.py with your Canvas URL and API token
```

## ⚙️ Configuration

Edit `config.py` to set up your Canvas connection:

```python
CANVAS_CONFIG = {
    'base_url': 'https://your-institution.instructure.com',
    'token': 'your-canvas-api-token'
}
```

### Getting Your Canvas API Token

1. Log in to your Canvas account
2. Go to Account → Settings
3. Scroll down to "Approved Integrations"
4. Click "+ New Access Token"
5. Enter a purpose/description
6. Copy the generated token to your `config.py`

### Launch the CLI

```bash
python3 canvas_cli.py
```

Or if using `uv`

```bash
uv run canvas_cli.py
```

## Commands

### Course Management

#### List Courses
```
ls courses [options]
```

**Options:**

- `--name, -n <regex>`: Filter by course name using a regular expression
- `--code, -c <regex>`: Filter by course code using a regular expression
- `-i, --ignore-case`: Make regex case-insensitive
- `--refresh`: Refresh courses from Canvas (ignore cache)

**Examples:**

```
ls courses
ls courses --name "COMPILADORES"
ls courses --name "2025Q1" -i
ls courses --code "15" -i
```

#### Select Course

```
use course <course_id>
```

Switch to a specific course context. The prompt will update to show the current course.

**Example:**

```
use course 81944
```

#### List Folders

```
ls folders [course_id]
```

List all folders in a course. If no course_id is provided, uses the currently selected course.

**Example:**

```
ls folders 81944
```

### Assignment Management

#### List Assignments

```
show assignments
```

Show all assignments in the currently selected course. Displays: name, due date, points, assignment group, and ID.

**Example:**

```
use course 81944
show assignments
```

#### Show Assignment Details

```
show assignment <assignment_id>
```

Display detailed information about a specific assignment.

**Information shown:**

- Name and ID
- Description (if any)
- Assignment group
- Points possible
- Due date
- Lock/unlock dates (if set)
- Submission types
- Allowed attempts
- Published status
- Workflow state
- Whether it has submissions
- Needs grading count
- Direct URL

**Example:**

```bash
show assignment 1514425
```

#### Create Assignment

```bash
create assignment <name> [options]
```

Create a new assignment in the currently selected course.

**Options:**

- `--points, -p <float>`: Points possible
- `--due-date, -d <date>`: Due date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
- `--description, --desc <text>`: Assignment description
- `--published`: Publish immediately

**Example:**

```bash
create assignment "Homework 1" --points 100 --due-date 2024-12-31T23:59:59Z --published
```

#### Delete Assignment

```bash
delete assignment <assignment_id>
```

Delete an assignment from the currently selected course.

**Example:**

```bash
delete assignment 1514425
```

### Student Management

#### List Students

```bash
show students
```

Show all students in the currently selected course. Displays: Canvas ID, name, and email.

**Example:**

```bash
show students
```

#### Download Students CSV

```bash
download students [--file FILE]
```

Export the student list to a CSV file. If no filename is provided, generates one based on the course name.

**CSV format:** `canvas_id`, `name`, `email`, `sis_user_id`

**Example:**

```bash
download students
download students --file my_students.csv
```

### Grade Management

#### Download Assignment Grades

```bash
download assignment grades <assignment_id> [--file FILE]
```

Download grades for a specific assignment as CSV. If no filename is provided, generates one based on the course and assignment name.

**CSV format:** `canvas_id`, `name`, `email`, `grade`, `submitted_at`, `workflow_state`, `late`

**Example:**

```bash
download assignment grades 1514425
download assignment grades 1514425 --file exam1_grades.csv
```

#### Upload Assignment Grades

```bash
upload assignment grades <assignment_id> --file FILE [--root-dir DIR]
```

Upload grades from a CSV file to a specific assignment.

**CSV requirements:** Must contain `canvas_id` and `grade` columns. Can optionally include `comment` and `file` columns.

**Options:**

- `--file, -f <path>`: Path to the CSV file (required)
- `--root-dir, -r <path>`: Root directory to resolve relative file paths in the CSV (defaults to CSV file's parent directory)

**Example:**

```bash
upload assignment grades 1514425 --file grades.csv
upload assignment grades 1514425 --file grades.csv --root-dir /path/to/files
```

### General Commands

#### Exit the CLI

```bash
exit
quit
```

Both commands will terminate the CLI session.

## Command Flow Examples

### Example 1: Setting up a new course

```bash
# List available courses
ls courses

# Select a course
use course 81944

# View assignments
show assignments

# View students
show students

# Download student list
download students
```

### Example 2: Working with assignment grades

```bash
# Select course
use course 81944

# Show assignment details
show assignment 1514425

# Download current grades
download assignment grades 1514425 --file current_grades.csv

# Upload new grades
upload assignment grades 1514425 --file updated_grades.csv
```

### Example 3: Creating and managing assignments

```bash
# Select course
use course 81944

# Create a new assignment
create assignment "Final Project" --points 200 --due-date 2024-12-15T23:59:59Z --published

# View all assignments to see the new one
show assignments

# Show details of the new assignment
show assignment 1519999
```

### CSV File Formats

#### Grade Upload CSV Format

The CSV file for uploading grades should have these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `student_id` | Yes | Canvas student ID |
| `grade` | Yes | Numeric grade |
| `comment` | No | Text comment for the grade |
| `md_eval_file` | No | Path to Markdown evaluation and feedback file |
| `md_exam_file1` | No | Path to Markdown exam file *format 1* |
| `md_exam_file2` | No | Path to Markdown exam file *format 2* |
| `pdf_exam_file1` | No | Path to PDF exam file *format 1* |
| `pdf_exam_file2` | No | Path to PDF exam file *format 2* |
| `pdf_eval_file` | No | Path to PDF evaluation and feedback file |

**Notes:**

- When submitting grades use **Markdown** or **PDF** but not both.
- `pdf_exam_file1` and `pdf_exam_file2` can be used when applying handwritten exams. `pdf_exam_file1` can be the scanned student submission and `pdf_exam_file2` can be the transcription, usually created with AI help.
- When using Markdown files the system will convert then to PDF before submitting in to **Canvas LMS**.

Example CSV:

```csv
student_id,grade,comment,md_eval_file
12345,85,Good work!,feedback/student_12345.md
67890,92,Good solution,feedback/student_67890.md
```

## Tips

- Use **TAB** for auto-completion of commands
- The prompt shows the currently selected course (e.g., `canvas/compiladores_i_2025q4>`)
- Most commands require a course to be selected first (use `use course <id>`)
- Use `ls courses` to see available courses and their IDs
- The CLI caches course data; use `--refresh` to force updates from Canvas

## Error Handling

The CLI provides clear error messages for common issues:

- "No course selected" - Use `use course <id>` first
- "Course not found" - Check the course ID with `ls courses`
- "Assignment not found" - Verify the assignment ID with `show assignments`
- "Invalid assignment id" - Assignment IDs must be numbers

## Configuration

### Canvas Configuration (`config.py`)

- `base_url`: Your Canvas instance URL
- `token`: Your Canvas API access token

### Application Configuration (`config.py`)

- `default_encoding`: File encoding for CSV operations (default: utf-8)

### File Upload Configuration (`config.py`)

- `max_file_size_mb`: Maximum file size for uploads
- `allowed_extensions`: List of permitted file extensions
- `upload_timeout`: Timeout for upload operations
