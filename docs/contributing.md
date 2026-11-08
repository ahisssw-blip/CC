# Contributing to Telegram Channel Saver

Thank you for your interest in contributing to Telegram Channel Saver! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please help us maintain a positive and inclusive environment by following these guidelines:

- Be respectful and considerate of others
- Use inclusive language and be mindful of cultural differences
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

## Ways to Contribute

There are many ways you can contribute to the project:

1. **Report bugs**: Submit bug reports by creating issues in the repository
2. **Suggest features**: Propose new features or improvements
3. **Improve documentation**: Help us improve existing documentation or add new documentation
4. **Submit code changes**: Fix bugs or implement new features
5. **Review code**: Review pull requests from other contributors

## Development Process

### Setting up the Development Environment

Please refer to the [Setup Guide](setup.md) for detailed instructions on setting up your development environment.

### Workflow

1. **Fork the repository**: Create your own fork of the project
2. **Create a branch**: Create a branch for your changes
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```
3. **Make changes**: Implement your changes
4. **Test**: Ensure your changes work as expected
5. **Commit**: Commit your changes with clear and descriptive commit messages
6. **Push**: Push your changes to your fork
7. **Pull Request**: Create a pull request from your fork to the main repository

### Commit Guidelines

Follow these guidelines for your commit messages:

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Start with a capital letter
- Keep the first line under 72 characters
- Reference issues and pull requests when appropriate

Example:
```
Add support for downloading images from channels

- Implement media download functionality
- Add file type detection
- Create directory structure for saved media

Fixes #42
```

## Pull Request Process

1. **Check existing issues and PRs**: Make sure your PR doesn't duplicate existing work
2. **Document your changes**: Update documentation to reflect your changes
3. **Include tests**: Add tests for new features or bug fixes
4. **Keep it focused**: Each PR should address a single concern
5. **Be responsive**: Respond to feedback and make requested changes

## Code Style and Standards

### Python Style Guidelines

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use 4 spaces for indentation (no tabs)
- Keep lines under 100 characters
- Use docstrings for functions, classes, and modules
- Add type hints where appropriate

### Documentation Standards

- Use Markdown for documentation
- Keep language simple and clear
- Include code examples where helpful
- Update documentation when making changes to the code

## Testing

- Write unit tests for new functionality
- Ensure all tests pass before submitting a pull request
- Test your changes in different environments if possible

## Issue Reporting Guidelines

When reporting issues, please include:

1. **Issue description**: A clear description of the issue
2. **Steps to reproduce**: Detailed steps to reproduce the problem
3. **Expected behavior**: What you expected to happen
4. **Actual behavior**: What actually happened
5. **Environment**: Python version, OS, etc.
6. **Screenshots**: If applicable
7. **Additional context**: Any other relevant information

## Feature Request Guidelines

When suggesting features, please include:

1. **Feature description**: A clear description of the proposed feature
2. **Use case**: Why this feature would be valuable
3. **Potential implementation**: If you have ideas on how to implement it
4. **Alternatives considered**: Any alternative solutions you've considered

## Getting Help

If you need help with contributing:

1. Check the [documentation](setup.md)
2. Ask questions in issues or existing discussions
3. Contact the maintainers

## License

By contributing to Telegram Channel Saver, you agree that your contributions will be licensed under the same license as the project. 