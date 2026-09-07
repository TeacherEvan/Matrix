# Matrix Display

An interactive, ambient Matrix-inspired rainfall display for your desktop.

## Description

The Matrix Display is a visual overlay that creates a classic "Matrix digital rain" effect on your desktop. It shows falling symbols with trails, random explosions, and interactive particle effects that respond to the system state.

## Features

- **Matrix-Style Digital Rain**: Falling symbols that create a classic Matrix effect
- **Intelligent Performance Management**: 
  - Automatically suspends when CPU usage exceeds 75%
  - Detects and pauses when fullscreen applications or games are running
  - Resumes when system returns to normal state
- **Dynamic Visual Effects**:
  - Blood-red explosion particles when symbols randomly explode
  - White pulsating effect on symbols about to explode
  - Flashing squares preceding each falling symbol
  - Customizable transparency levels
- **System-Friendly**:
  - Click-through interface that doesn't interfere with normal computer use
  - Low performance impact by design

## System Requirements

- Windows 10 or later
- Python 3.7 or higher
- Required Python packages:
  - PyQt6
  - psutil
  - pywin32

## Installation

1. Clone this repository or download the source code
2. Install the required packages:
   ```
   pip install PyQt6 psutil pywin32
   ```
3. Run the application:
   ```
   python MatrixDisplay.py
   ```

## Usage

The application runs automatically after starting. No user interaction is required.

The Matrix display will intelligently:
- Suspend operation when CPU usage exceeds 75%
- Hide itself when fullscreen applications are detected
- Resume automatically when conditions return to normal

## License

This project is available under the MIT License.

## Acknowledgments

Inspired by the digital rain effect from "The Matrix" film series.

## Testing

The repository ships with an AST-level smoke test suite that runs on any
platform (Windows, Linux, macOS) without requiring PyQt6 / pywin32 runtime
support. The full GUI application only runs on Windows.

Install test dependencies and run the suite:

```
python3 -m pip install -r requirements-dev.txt
python3 -m pytest tests/ -v
```

Or use the bundled wrapper:

```
./scripts/run_tests.sh
```

The suite validates the structural surface (classes, methods, entry point,
imports, no hardcoded secrets) declared in the project specification. It
will not exercise the actual PyQt6 paint loop.
