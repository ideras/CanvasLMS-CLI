# Contributing to Canvas LMS CLI

Thank you for your interest in contributing to Canvas LMS CLI! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Copy the configuration template:
   ```bash
   cp config.example.py config.py
   # Edit config.py with your Canvas settings
   ```

## 🔧 Development Guidelines

### Code Style

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and small
- Use type hints where appropriate

### Project Structure

- `canvascli/app.py`: Main CLI application using Rich and prompt_toolkit
- `canvascli/cli/ui.py`: Rich-based UI components (styling, tables, progress bars)
- `canvascli/cli/cmd_handler.py`: Business logic for CLI commands
- `canvascli/api/client.py`: Canvas API wrapper
- `canvascli/api/request_executor.py`: HTTP request handling
- `canvascli/grades/uploader.py`: Grade upload logic
- `canvascli/grades/loader.py`: CSV grade loading and validation
- `canvascli/converters/markdown_converter.py`: Markdown to PDF conversion

### Adding New Features

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Implement your feature following the existing patterns:
   - Add CLI commands in `canvascli/app.py`
   - Add command handlers in `canvascli/cli/cmd_handler.py`
   - Implement logic in appropriate subpackage
   - Update configuration if needed

3. Test your changes thoroughly

4. Update documentation:
   - Update README.md if needed
   - Add docstrings to new functions
   - Update CLAUDE.md for development guidance

### Testing

- Test manually with different Canvas courses
- Verify CSV upload/download functionality
- Test markdown to PDF conversion
- Check error handling for edge cases

## 📝 Pull Request Process

1. Ensure your code follows the project's style guidelines
2. Update documentation as needed
3. Add a clear description of your changes
4. Reference any related issues
5. Ensure your branch is up to date with main

### Pull Request Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Tested manually
- [ ] Added appropriate error handling
- [ ] Verified with different Canvas courses

## Related Issues
Closes #[issue number]
```

## 🐛 Bug Reports

When reporting bugs, please include:

- Python version
- Operating system
- Canvas LMS version/institution
- Steps to reproduce
- Expected vs actual behavior
- Error messages or stack traces
- Sample CSV files (with sensitive data removed)

## 💡 Feature Requests

For new features, please:

- Check existing issues first
- Describe the use case clearly
- Explain how it would benefit educators
- Consider Canvas API limitations
- Provide examples of desired behavior

## 📚 Documentation

Documentation improvements are always welcome:

- Fix typos or unclear explanations
- Add usage examples
- Improve installation instructions
- Add troubleshooting guides

## 🔐 Security

- Never commit API tokens or sensitive data
- Use `config.example.py` for configuration templates
- Report security issues privately
- Follow responsible disclosure practices

## 🏷️ Commit Messages

Use clear, descriptive commit messages:

```
feat: add bulk student export functionality
fix: handle missing student names in CSV upload
docs: update installation instructions
refactor: simplify grade upload progress tracking
```

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🤝 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers get started
- Maintain a positive environment

## 🙋 Getting Help

- Check existing issues and documentation
- Create an issue for questions
- Join discussions in existing issues
- Be patient and provide context

## 🎯 Development Priorities

Current focus areas:
- Improved error handling
- Better progress reporting
- Additional Canvas API features
- Enhanced markdown styling
- Cross-platform compatibility

Thank you for helping make Canvas LMS CLI better for educators worldwide! 🎓