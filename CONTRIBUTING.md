# Contributing to TermiVoxed

First off, thank you for considering contributing to TermiVoxed! It's people like you that make this tool better for everyone.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Documentation](#documentation)

---

## Code of Conduct

This project and everyone participating in it is governed by basic principles of respect and professionalism. By participating, you are expected to uphold this code.

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

---

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the problem
- **Expected behavior** vs **actual behavior**
- **Screenshots** if applicable
- **Environment details** (OS, Python version, FFmpeg version)
- **Log files** from `logs/console_editor.log`

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title and description**
- **Use case** - why would this be useful?
- **Proposed solution** if you have one
- **Alternatives considered**
- **Additional context** or screenshots

### Your First Code Contribution

Unsure where to begin? Look for issues labeled:
- `good-first-issue` - Simple issues perfect for beginners
- `help-wanted` - Issues where we'd appreciate community help

---

## Development Setup

### 1. Fork and Clone

\`\`\`bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/termivoxed.git
cd termivoxed
\`\`\`

### 2. Create Virtual Environment

\`\`\`bash
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
\`\`\`

### 3. Install Development Dependencies

\`\`\`bash
pip install --upgrade pip
pip install -r requirements-dev.txt
\`\`\`

### 4. Create a Branch

\`\`\`bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
\`\`\`

### 5. Make Your Changes

Edit the code, add tests, update documentation as needed.

### 6. Test Your Changes

\`\`\`bash
# Run the application
python main.py

# Run tests (when available)
pytest

# Check code style
black --check .
flake8 .
\`\`\`

---

## Coding Standards

### Python Style

We follow **PEP 8** with these specifics:

- **Line length**: 100 characters (configured in pyproject.toml)
- **Formatting**: Use Black formatter
- **Imports**: Organized with isort
- **Type hints**: Encouraged but not required
- **Docstrings**: Google style for functions and classes

### Code Formatting

Before committing, format your code:

\`\`\`bash
# Format with Black
black .

# Sort imports
isort .

# Check for issues
flake8 .
mypy . --ignore-missing-imports
\`\`\`

### File Organization

- **New features**: Add to appropriate module (backend/, core/, utils/)
- **Models**: Add to models/ if creating new data structures
- **UI components**: Add to ui/ if creating interface elements
- **Tests**: Mirror source structure in tests/ directory

---

## Commit Messages

### Format

\`\`\`
<type>: <subject>

<body>

<footer>
\`\`\`

### Type

- **Add**: New feature or functionality
- **Fix**: Bug fix
- **Update**: Changes to existing feature
- **Refactor**: Code restructuring without behavior change
- **Docs**: Documentation only changes
- **Style**: Code style changes (formatting, etc.)
- **Test**: Adding or updating tests
- **Chore**: Maintenance tasks (dependencies, etc.)

### Examples

\`\`\`bash
Add: Interactive voice preview in voice selector

Implemented audio playback preview using pygame mixer.
Users can now listen to voice samples before selection.

Closes #42
\`\`\`

\`\`\`bash
Fix: Subtitle rendering with disabled borders

When borders were disabled, text became invisible on light backgrounds.
Now uses opaque box background (borderstyle=3) for visibility.

Fixes #67
\`\`\`

---

## Pull Request Process

### Before Submitting

1. **Update documentation** if you changed behavior
2. **Add tests** for new features (when test framework is available)
3. **Run formatters** (black, isort)
4. **Check for errors** (flake8, mypy)
5. **Test manually** to ensure nothing broke
6. **Update CHANGELOG.md** with your changes

### Submitting

1. **Push your branch** to your fork
2. **Open a Pull Request** on GitHub
3. **Fill out the PR template** completely
4. **Link related issues** (e.g., "Closes #123")
5. **Request review** from maintainers

### PR Title Format

\`\`\`
<type>: <clear description>
\`\`\`

Examples:
- `Add: Batch export functionality`
- `Fix: Memory leak in audio processing`
- `Update: Improve voice selection UX`

### Review Process

- Maintainers will review your PR within a few days
- Address any requested changes
- Once approved, a maintainer will merge your PR
- Your contribution will be credited in CHANGELOG.md

---

## Testing

### Manual Testing

Always test your changes manually:

1. **Run the application**: `python main.py`
2. **Test affected features**: Try the feature you changed
3. **Test edge cases**: Try unusual inputs or scenarios
4. **Check logs**: Review `logs/console_editor.log` for errors

### Automated Testing (Future)

We plan to add comprehensive tests. For now:
- Focus on manual testing
- Document test cases in your PR
- Help us build the test suite!

### Test Checklist

- [ ] Feature works as expected
- [ ] No errors in console output
- [ ] No errors in log files
- [ ] Works on your platform (Windows/macOS/Linux)
- [ ] Documentation updated if needed

---

## Documentation

### When to Update Documentation

- Adding a new feature
- Changing existing behavior
- Adding configuration options
- Fixing bugs that affect usage

### What to Update

- **README.md**: User-facing changes
- **CHANGELOG.md**: All changes
- **Docstrings**: For functions and classes
- **Reference docs**: Technical documentation
- **Comments**: For complex logic

### Documentation Style

- **Clear and concise**: Assume user is semi-technical
- **Examples**: Provide code examples where helpful
- **Platform-specific**: Note Windows/macOS/Linux differences
- **Screenshots**: Include for UI changes (if applicable)

---

## Questions?

- **Open an issue** for questions
- **Start a discussion** on GitHub Discussions (if enabled)
- **Check existing issues** - your question might be answered

---

Thank you for contributing to TermiVoxed! 🎬

**— Santhosh T**
