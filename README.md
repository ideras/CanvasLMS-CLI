# Canvas LMS CLI

A powerful command-line interface for managing Canvas LMS courses, students, assignments, and grade uploads. Built for educators who need efficient tools to handle course administration and grading workflows.

## 🌟 Features

- **Interactive CLI**: User-friendly command-line interface with tab completion
- **Course Management**: List, filter, and select courses
- **Student Management**: View and export student lists
- **Assignment Management**: View assignments and manage grades
- **Bulk Grade Upload**: CSV-based grade uploads with optional file attachments
- **Markdown to PDF**: Convert Markdown feedback files to PDF format automatically
- **File Organization**: Automatic Canvas folder creation and organization
- **Progress Tracking**: Real-time upload progress with Canvas API integration

## 📋 Requirements

- Python 3.8+
- Canvas LMS account with API access  
- Canvas API token
- [uv](https://docs.astral.sh/uv/) (recommended) or pip for dependency management

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

## 🎯 Usage

### Starting the CLI

```bash
python3 canvas_cli.py
```

### Basic Commands

#### List and Select Courses
```bash
# List all your courses
canvas> ls courses

# Filter courses by name (regex supported)
canvas> ls courses --name "Programming"

# Select a course to work with
canvas> use course 12345
```

#### Manage Students
```bash
# Show students in current course
canvas/programming_course> show students

# Export student list to CSV
canvas/programming_course> download students --file students.csv
```

#### Manage Assignments
```bash
# Show assignments in current course
canvas/programming_course> show assignments

# Download assignment grades
canvas/programming_course> download assignment grades 67890 --file grades.csv
```

#### Upload Grades
```bash
# Upload grades from CSV file
canvas/programming_course> upload assignment grades 67890 --file updated_grades.csv
```

### CSV File Formats

#### Grade Upload CSV Format
The CSV file for uploading grades should have these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `student_id` | Yes | Canvas student ID |
| `grade` | Yes | Numeric grade |
| `comment` | No | Text comment for the grade |
| `markdown_file` | No | Path to Markdown feedback file |
| `pdf_file` | No | Path to PDF feedback file |

Example CSV:
```csv
student_id,grade,comment,markdown_file
12345,85,Great work!,feedback/student_12345.md
67890,92,Excellent solution,feedback/student_67890.md
```

#### Features of Grade Upload
- **Automatic PDF Conversion**: Markdown files are automatically converted to PDF
- **File Organization**: Files are uploaded to organized Canvas folders
- **Rich Comments**: HTML comments with download links are added automatically
- **Progress Tracking**: Real-time progress updates during bulk operations

## 🔧 Advanced Features

### Markdown to PDF Conversion

The tool automatically converts Markdown feedback files to PDF with professional styling:

```python
# Supported Markdown features:
- Headers and formatting
- Code blocks with syntax highlighting
- Tables
- Lists and blockquotes
- Math expressions (with proper extensions)
```

### File Upload System

Files are automatically organized in Canvas under:
```
Grade_Feedback/
├── 2024-08-14_Assignment_1/
│   ├── student_feedback_1.pdf
│   └── student_feedback_2.pdf
└── 2024-08-14_Midterm_Exam/
    └── detailed_feedback.pdf
```

### Bulk Operations

- Process hundreds of students efficiently
- Automatic retry on API failures
- Rate limiting to respect Canvas API limits
- Detailed progress reporting

## 🛠️ Development

### Project Structure

```
CanvasLMS-CLI/
├── canvas_cli.py                 # Main CLI entry point
├── canvas_cli_cmd_handler.py     # Command handlers
├── canvas_client.py              # Canvas API client
├── canvas_request_executor.py    # HTTP request handler
├── canvas_grades_uploader.py     # Grade upload logic
├── markdown_converter.py         # Markdown to PDF conversion
├── config.py                     # Configuration settings
└── csv_files/                    # Sample CSV files
```

### Development Setup

```bash
# Clone and setup with uv
git clone https://github.com/yourusername/CanvasLMS-CLI.git
cd CanvasLMS-CLI
uv sync --dev  # Install dependencies and dev tools
cp config.example.py config.py  # Configure your Canvas settings
```

### Running Tests

```bash
# Test markdown conversion
uv run python markdown_converter.py

# Test individual components  
uv run python -c "from canvas_client import CanvasClient; print('Client loaded')"

# Run with uv
uv run python canvas_cli.py
```

## 🚨 Security Notes

- **API Token**: Never commit your Canvas API token to version control
- **Student Data**: Be careful with student information and follow your institution's privacy policies
- **File Permissions**: Ensure proper file permissions for uploaded feedback files

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

- Create an issue for bug reports or feature requests
- Check the [CLAUDE.md](CLAUDE.md) file for development guidance

## 🙏 Acknowledgments

- Built for educational institutions using Canvas LMS
- Designed to streamline grading workflows for educators
- Supports modern pedagogical practices with rich feedback mechanisms

---

**Note**: This tool is not officially affiliated with Instructure or Canvas LMS. It's an independent project designed to enhance the Canvas experience for educators.
