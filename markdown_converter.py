#!/usr/bin/env python3
"""
Markdown to PDF Converter Module
Converts Markdown files to PDF with various styling options

Requirements:
pip install markdown weasyprint pygments

Alternative engines:
pip install pdfkit  # Requires wkhtmltopdf
# or use pandoc (external dependency)
"""

import os
import tempfile
from typing import Optional
from pathlib import Path
import markdown
from markdown.extensions import codehilite, toc, tables, fenced_code

from config import MARKDOWN_CONFIG


class MarkdownToPDFConverter:
    def __init__(self):
        self.config = MARKDOWN_CONFIG
        self.css_styles = self._get_css_styles()
    
    def convert_file(self, md_file_path: str, output_pdf_path: str = None) -> Optional[str]:
        """Convert a Markdown file to PDF"""
        if not os.path.exists(md_file_path):
            raise FileNotFoundError(f"Markdown file not found: {md_file_path}")
        
        # Read markdown content
        with open(md_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Generate output path if not provided
        if not output_pdf_path:
            md_path = Path(md_file_path)
            output_pdf_path = str(md_path.with_suffix('.pdf'))
        
        return self.convert_content(md_content, output_pdf_path)
    
    def convert_content(self, md_content: str, output_pdf_path: str) -> Optional[str]:
        """Convert Markdown content string to PDF"""
        try:
            # Configure markdown extensions
            extensions = ['tables', 'fenced_code']
            extension_configs = {}
            
            if self.config['code_highlighting']:
                extensions.append('codehilite')
                extension_configs['codehilite'] = {
                    'css_class': 'highlight',
                    'use_pygments': True
                }
            
            if self.config['include_toc']:
                extensions.append('toc')
                extension_configs['toc'] = {
                    'title': 'Table of Contents'
                }
            
            # Convert markdown to HTML
            md = markdown.Markdown(
                extensions=extensions,
                extension_configs=extension_configs
            )
            html_content = md.convert(md_content)
            
            # Wrap in complete HTML document
            full_html = self._create_html_document(html_content)
            
            # Convert to PDF using selected engine
            if self.config['pdf_engine'] == 'weasyprint':
                return self._convert_with_weasyprint(full_html, output_pdf_path)
            elif self.config['pdf_engine'] == 'pdfkit':
                return self._convert_with_pdfkit(full_html, output_pdf_path)
            else:
                raise ValueError(f"Unsupported PDF engine: {self.config['pdf_engine']}")
        
        except Exception as e:
            print(f"Failed to convert markdown to PDF: {e}")
            return None
    
    def _convert_with_weasyprint(self, html_content: str, output_path: str) -> Optional[str]:
        """Convert HTML to PDF using WeasyPrint"""
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            print(f"Converting to PDF using WeasyPrint...")
            
            # Create CSS for styling
            css_content = self._get_weasyprint_css()
            css = CSS(string=css_content)
            
            # Convert to PDF
            html_doc = HTML(string=html_content)
            html_doc.write_pdf(output_path, stylesheets=[css])
            
            print(f"PDF created successfully: {output_path}")
            return output_path
            
        except ImportError:
            print("WeasyPrint not installed. Run: pip install weasyprint")
            return None
        except Exception as e:
            print(f"WeasyPrint conversion failed: {e}")
            return None
    
    def _convert_with_pdfkit(self, html_content: str, output_path: str) -> Optional[str]:
        """Convert HTML to PDF using pdfkit/wkhtmltopdf"""
        try:
            import pdfkit
            
            print(f"Converting to PDF using pdfkit...")
            
            options = {
                'page-size': 'A4',
                'margin-top': self.config['page_margins'],
                'margin-right': self.config['page_margins'],
                'margin-bottom': self.config['page_margins'],
                'margin-left': self.config['page_margins'],
                'encoding': "UTF-8",
                'no-outline': None
            }
            
            pdfkit.from_string(html_content, output_path, options=options)
            
            print(f"PDF created successfully: {output_path}")
            return output_path
            
        except ImportError:
            print("❌ pdfkit not installed. Run: pip install pdfkit")
            print("   Also install wkhtmltopdf: https://wkhtmltopdf.org/downloads.html")
            return None
        except Exception as e:
            print(f"❌ pdfkit conversion failed: {e}")
            return None
    
    def _create_html_document(self, body_content: str) -> str:
        """Create a complete HTML document with styling"""
        css_style = self.css_styles.get(self.config['css_style'], self.css_styles['github'])
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feedback Document</title>
    <style>
        {css_style}
    </style>
</head>
<body>
    <div class="container">
        {body_content}
    </div>
</body>
</html>
"""
        return html
    
    def _get_weasyprint_css(self) -> str:
        """Get CSS specifically formatted for WeasyPrint"""
        return f"""
        @page {{
            margin: {self.config['page_margins']};
            size: A4;
        }}
        
        body {{
            font-family: {self.config['font_family']};
            font-size: {self.config['font_size']};
            line-height: {self.config['line_height']};
            color: #333;
            max-width: 100%;
        }}
        
        .container {{
            max-width: 100%;
            margin: 0 auto;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        
        h1 {{ font-size: 1.8em; border-bottom: 2px solid #3498db; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid #bdc3c7; padding-bottom: 0.2em; }}
        h3 {{ font-size: 1.3em; }}
        
        p {{ margin-bottom: 1em; }}
        
        ul, ol {{ margin-bottom: 1em; padding-left: 2em; }}
        li {{ margin-bottom: 0.3em; }}
        
        code {{
            background-color: #f8f9fa;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        pre {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 1em;
            overflow-x: auto;
            margin-bottom: 1em;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 1em 0;
            padding-left: 1em;
            color: #7f8c8d;
            font-style: italic;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 1em;
        }}
        
        th, td {{
            border: 1px solid #bdc3c7;
            padding: 0.5em;
            text-align: left;
        }}
        
        th {{
            background-color: #ecf0f1;
            font-weight: bold;
        }}
        
        .highlight {{
            background-color: #f8f9fa;
            border-radius: 6px;
            padding: 1em;
        }}
        """
    
    def _get_css_styles(self) -> dict:
        """Get predefined CSS styles for different themes"""
        return {
            'github': """
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 2em;
                }
                h1, h2 { border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
                h1 { font-size: 2em; }
                h2 { font-size: 1.5em; }
                h3 { font-size: 1.25em; }
                code { background-color: rgba(27,31,35,0.05); padding: 0.2em 0.4em; border-radius: 3px; }
                pre { background-color: #f6f8fa; padding: 16px; border-radius: 6px; overflow: auto; }
                blockquote { padding: 0 1em; color: #6a737d; border-left: 0.25em solid #dfe2e5; }
                table { border-collapse: collapse; }
                th, td { border: 1px solid #dfe2e5; padding: 6px 13px; }
                th { background-color: #f6f8fa; }
            """,
            
            'academic': """
                body {
                    font-family: 'Times New Roman', serif;
                    line-height: 1.8;
                    color: #2c3e50;
                    max-width: 750px;
                    margin: 0 auto;
                    padding: 2em;
                }
                h1, h2, h3, h4 { color: #2c3e50; margin-top: 2em; }
                h1 { font-size: 1.8em; text-align: center; }
                h2 { font-size: 1.4em; }
                p { text-align: justify; margin-bottom: 1.2em; }
                blockquote { font-style: italic; margin: 1.5em 2em; }
                code { font-family: 'Courier New', monospace; background-color: #f8f9fa; padding: 0.1em 0.3em; }
            """,
            
            'minimal': """
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.5;
                    color: #444;
                    max-width: 700px;
                    margin: 0 auto;
                    padding: 1.5em;
                }
                h1, h2, h3 { color: #333; }
                h1 { font-size: 1.6em; }
                h2 { font-size: 1.3em; }
                h3 { font-size: 1.1em; }
                ul, ol { padding-left: 1.5em; }
                code { background-color: #f5f5f5; padding: 0.1em 0.3em; }
                pre { background-color: #f5f5f5; padding: 1em; border-left: 3px solid #ccc; }
            """
        }


def create_sample_markdown_files():
    """Create sample markdown files for testing"""
    samples = {
        'sample_feedback.md': """# Assignment 1 Feedback

## Student Performance Summary

**Overall Grade: 85/100**

### Strengths ✅

- **Code Structure**: Well-organized and readable code
- **Documentation**: Excellent comments and docstrings
- **Algorithm Implementation**: Correct implementation of core algorithms
- **Testing**: Good test coverage

### Areas for Improvement 🔧

1. **Error Handling**: Missing try-catch blocks in critical sections
2. **Performance**: Some algorithms could be optimized
3. **Code Style**: Minor PEP 8 violations

### Detailed Comments

#### Part 1: Data Processing (25/25)
Perfect implementation! Your data cleaning logic is efficient and handles edge cases well.

```python
# Example of good code structure
def clean_data(raw_data):
    \"\"\"Clean and validate input data\"\"\"
    if not raw_data:
        return []
    return [item.strip() for item in raw_data if item]
```

#### Part 2: Algorithm Implementation (30/35)
Good work overall, but consider optimizing the sorting algorithm:

- Current complexity: O(n²)
- Suggested: Use built-in `sorted()` for O(n log n)

#### Part 3: Testing (30/40)
Your test cases cover the main functionality, but missing:

- Edge case testing
- Error condition testing
- Performance testing

## Recommendations for Next Assignment

1. **Review error handling patterns**
2. **Study time complexity analysis**
3. **Expand test coverage**

## Resources

- [Python Error Handling Guide](https://docs.python.org/3/tutorial/errors.html)
- [Algorithm Complexity Reference](https://wiki.python.org/moin/TimeComplexity)

---
*Great job overall! Keep up the good work! 🎉*
""",

        'sample_rubric.md': """# Programming Assignment Rubric

## Course: Compiladores II
**Assignment**: Parser Implementation  
**Total Points**: 100

---

## Grading Criteria

### 1. Code Quality (25 points)

| Criteria | Excellent (23-25) | Good (18-22) | Satisfactory (13-17) | Needs Work (0-12) |
|----------|-------------------|--------------|----------------------|-------------------|
| **Structure** | Clear, modular design | Mostly well organized | Some organization | Poor structure |
| **Naming** | Descriptive variable/function names | Generally clear names | Some unclear names | Poor naming |
| **Comments** | Comprehensive documentation | Good documentation | Basic comments | Minimal/no comments |

### 2. Functionality (35 points)

- ✅ **Lexical Analysis (10 pts)**: Correctly tokenizes input
- ✅ **Syntax Analysis (15 pts)**: Parses according to grammar
- ✅ **Error Handling (10 pts)**: Graceful error reporting

### 3. Testing (20 points)

- **Unit Tests (10 pts)**: Individual component testing
- **Integration Tests (5 pts)**: End-to-end testing  
- **Edge Cases (5 pts)**: Boundary condition testing

### 4. Documentation (20 points)

- **README (5 pts)**: Clear setup and usage instructions
- **Code Comments (10 pts)**: Inline documentation
- **Design Document (5 pts)**: Architecture explanation

---

## Bonus Opportunities (+5 points each)

- 🌟 **Performance Optimization**: Demonstrable speed improvements
- 🌟 **Extended Features**: Additional functionality beyond requirements
- 🌟 **Creative Testing**: Novel test cases or testing approaches

## Common Issues to Avoid ⚠️

1. **Memory Leaks**: Ensure proper resource cleanup
2. **Infinite Loops**: Validate termination conditions
3. **Buffer Overflows**: Check array bounds
4. **Grammar Conflicts**: Resolve ambiguous productions

---

**Submission Deadline**: Friday, August 15, 2025 at 11:59 PM  
**Late Penalty**: -10% per day

*Good luck! Remember to start early and test thoroughly! 🚀*
"""
    }
    
    for filename, content in samples.items():
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created sample markdown file: {filename}")
    
    print(f"\n📋 Sample markdown files created!")
    print(f"   Edit them with your content, then convert to PDF")
    print(f"   Example: python -c \"from markdown_converter import MarkdownToPDFConverter; MarkdownToPDFConverter().convert_file('sample_feedback.md')\"")


# Utility function for easy conversion
def convert_markdown_to_pdf(md_file: str, output_pdf: str = None) -> Optional[str]:
    """Convenience function to convert markdown to PDF"""
    converter = MarkdownToPDFConverter()
    return converter.convert_file(md_file, output_pdf)


if __name__ == "__main__":
    # Test the converter
    print("🧪 Testing Markdown to PDF converter...")
    create_sample_markdown_files()
    
    # Try converting a sample file
    converter = MarkdownToPDFConverter()
    result = converter.convert_file('sample_feedback.md', 'sample_feedback.pdf')
    
    if result:
        print(f"🎉 Test conversion successful: {result}")
    else:
        print("❌ Test conversion failed")