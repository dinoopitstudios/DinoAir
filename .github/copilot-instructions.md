# DinoAir 2.0 - AI-Powered Note Management System

DinoAir 2.0 is a Python-based AI-powered note-taking and project management system with a React TypeScript frontend and FastAPI backend. The system includes database management, RAG (Retrieval-Augmented Generation), and multiple specialized tools.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Build the Repository

- Install Python dependencies:
  - `python3 -m venv venv`
  - `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows)
  - `pip install -r requirements.txt` -- takes 1 minute. NEVER CANCEL.
  - `pip install -r requirements-dev.txt` -- takes 1 minute. NEVER CANCEL.

- Install Node.js dependencies:
  - `npm install` -- takes 23 seconds. NEVER CANCEL.

- **CRITICAL BUILD ISSUE**: The frontend build is currently broken due to missing `src/lib/` directory. Do not attempt `npm run build` as it will fail with TypeScript import errors.

### Run Tests

- Database tests: `python -m pytest database/tests/ -v` -- takes 30 seconds. NEVER CANCEL. Set timeout to 60+ seconds.
  - Expected: 140 tests pass, 32 may fail (known issues)
- Individual module tests:
  - Models: `python -m pytest models/tests/ -v` -- takes < 1 second
  - Tools: `python -m pytest tools/tests/ -v -k "not integration"` -- takes < 1 second
  - Utils tests currently have configuration issues and may fail

### Linting and Code Quality

- Python linting (fast, < 1 second): `ruff check .` -- Set timeout to 30+ seconds.
- Python auto-fix: `ruff check --fix .`
- Python formatting check: `black --check .` -- takes 16 seconds. NEVER CANCEL. Set timeout to 60+ seconds.
- Python formatting apply: `black .`
- Type checking: `mypy database/` -- takes 6 seconds. NEVER CANCEL. Set timeout to 30+ seconds.
- Node.js linting: `npm run lint` -- takes 8 seconds. Currently fails due to missing lib files.

### Application Components

**CRITICAL**: The application cannot currently run due to missing dependencies and configuration issues:

- **API Server**: Cannot start due to missing dependencies (`pythonjsonlogger`, etc.) and incorrect path references
- **Frontend**: Cannot build due to missing `src/lib/` directory containing API client code
- **CLI Tools**: Most CLI tools are not properly configured for execution

### Manual Validation Scenarios

**IMPORTANT**: Since the full application cannot run, validation is limited to:

1. **Import Testing**: Verify core modules can be imported:
   - `python -c "import database; print('Database OK')"`
   - `python -c "import utils; print('Utils OK')"`
   - `python -c "import tools; print('Tools OK')"`

2. **Test Suite Validation**: Run the database test suite to ensure core functionality works
3. **Linting Validation**: Run all linting tools to ensure code quality

**Note**: Full end-to-end application testing is currently not possible due to build configuration issues.

## Common Tasks

### Development Workflow

1. **Always activate virtual environment first**: `source venv/bin/activate`
2. **Before making changes**: Run `ruff check .` and `black --check .`
3. **After making changes**:
   - Run relevant test suite: `python -m pytest [module]/tests/ -v`
   - Run linting: `ruff check --fix .`
   - Run formatting: `black .`
4. **Before committing**: Run `python -m pytest database/tests/ -v` (the most stable test suite)

### Repository Structure

```
DinoAir/
├── database/           # SQLite database management and schema
├── utils/             # Utility functions and helpers
├── models/            # Data models and validation
├── tools/             # Specialized tools (pseudocode translator, etc.)
├── src/               # React TypeScript frontend (incomplete)
├── API_files/         # FastAPI backend (missing dependencies)
├── config/            # Configuration management system
├── rag/               # Retrieval-Augmented Generation components
├── requirements.txt   # Python runtime dependencies
├── requirements-dev.txt # Python development dependencies
├── package.json       # Node.js frontend dependencies
└── pyproject.toml     # Python project configuration
```

### Key Project Components

- **Database Layer**: Comprehensive SQLite-based system with migrations, notes, projects, appointments
- **Utils**: Configuration management, logging, security, file processing
- **Tools**: Pseudocode translator, file search, notes management, project management
- **Models**: Pydantic-based data validation for notes, projects, artifacts
- **Frontend**: React TypeScript UI (currently incomplete)
- **Backend API**: FastAPI-based REST API (currently broken)

## Configuration and Environment

### Python Requirements

- **Python**: 3.12+ (confirmed working with 3.12.3)
- **Virtual Environment**: Required for dependency isolation
- **Core Dependencies**: pydantic, aiofiles, httpx, cryptography, pypdf, psutil

### Node.js Requirements

- **Node.js**: 18.0.0+ (confirmed working with v20.19.5)
- **npm**: 9.0.0+
- **Frontend Framework**: React 18 with TypeScript and Vite

### Known Issues and Workarounds

1. **Frontend Build Failure**: Missing `src/lib/` directory prevents TypeScript compilation
2. **API Server Startup**: Missing `pythonjsonlogger` and path configuration issues
3. **Editable Install**: `pip install -e .` fails due to network timeouts in build dependencies
4. **Utils Tests**: Configuration marker issues prevent test execution
5. **Path Mismatches**: `vite.config.ts` references `10_src` but actual source is in `src`

### Timing Expectations

- **NEVER CANCEL** any build or test commands. All operations complete within reasonable time:
  - Python dependency install: 1 minute
  - Node.js dependency install: 23 seconds
  - Database tests: 30 seconds
  - Python linting (ruff): < 1 second
  - Python formatting (black): 16 seconds
  - Type checking (mypy): 6 seconds
  - Node.js linting: 8 seconds

### Development Best Practices

1. **Always use virtual environment** for Python development
2. **Run tests frequently** to catch regressions early
3. **Use ruff and black** for consistent Python code style
4. **Focus on database and utils modules** as they are the most stable
5. **Avoid frontend development** until lib directory structure is fixed
6. **Do not attempt to run full application** until dependency issues are resolved

## Testing Strategy

Since full application testing is not possible, focus on:

1. **Unit Testing**: Run individual module test suites
2. **Import Testing**: Verify modules can be imported without errors
3. **Linting Validation**: Ensure code passes quality checks
4. **Database Testing**: The most comprehensive and reliable test suite

## Troubleshooting

### Common Problems

- **Import Errors**: Ensure virtual environment is activated and dependencies are installed
- **Test Failures**: Some test failures are expected; focus on whether new changes break additional tests
- **Build Failures**: Frontend build is known to be broken; avoid `npm run build`
- **Path Issues**: Some tools reference incorrect paths; use Python module imports instead of direct execution

This completes the DinoAir 2.0 development guide. The system has a solid foundation but requires dependency resolution and configuration fixes before full application functionality can be restored.
