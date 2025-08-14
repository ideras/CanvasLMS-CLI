#!/usr/bin/env python3
"""
Canvas Configuration Module - EXAMPLE
Contains all configuration settings for Canvas API access

IMPORTANT: 
1. Copy this file to 'config.py'
2. Replace the placeholder values with your actual Canvas settings
3. Never commit the actual config.py with real credentials to version control
"""

# Canvas API Configuration
CANVAS_CONFIG = {
    'base_url': 'https://your-institution.instructure.com',  # Replace with your Canvas URL
    'token': 'your-canvas-api-token-here'  # Replace with your Canvas API token
}

# File upload settings
FILE_UPLOAD_CONFIG = {
    'max_file_size_mb': 50,  # Maximum file size in MB
    'allowed_extensions': ['.pdf', '.md', '.txt', '.docx', '.png', '.jpg', '.mp3', '.wav'],
    'upload_timeout': 60,  # Timeout in seconds for file uploads
}

# Application settings
APP_CONFIG = {
    'default_encoding': 'utf-8',
    'csv_delimiter': ',',
    'progress_delay': 0.4,  # Delay between API calls to avoid rate limiting
    'max_preview_students': 10,  # Number of students to show in preview
}

# Markdown to PDF conversion settings
MARKDOWN_CONFIG = {
    'pdf_engine': 'weasyprint',  # Options: 'weasyprint', 'pdfkit'
    'css_style': 'academic',  # Options: 'github', 'academic', 'minimal', 'custom'
    'include_toc': False,  # Include table of contents
    'page_margins': '0.7in',  # Page margins
    'font_family': 'Calibri, sans-serif',
    'font_size': '11pt',
    'line_height': '1.6',
    'code_highlighting': True,  # Syntax highlighting for code blocks
    'custom_css_file': None,  # Path to custom CSS file (optional)
}
