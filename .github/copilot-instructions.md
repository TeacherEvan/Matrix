# Matrix Display - GitHub Copilot Instructions

**ALWAYS follow these instructions first** and only fall back to additional search and context gathering if the information here is incomplete or found to be in error.

## Project Overview

Matrix Display is a Windows desktop overlay application that creates a Matrix-style digital rain effect. It's a PyQt6-based GUI application that shows falling symbols with interactive explosion physics and CPU-based performance management.

## System Requirements & Dependencies

**Operating System:**
- Windows 10 or later (REQUIRED - uses pywin32 for window layering)
- Python 3.7 or higher

**Critical Dependencies:**
```bash
pip install PyQt6 psutil pywin32
```

**Installation Commands (VALIDATED):**
```bash
# Install Python dependencies - NEVER CANCEL: Takes 60-90 seconds
pip install PyQt6 psutil pywin32
```

## Working Effectively

### Bootstrap and Setup
```bash
# Clone and navigate to repository
git clone <repository-url>
cd Matrix

# Install dependencies - NEVER CANCEL: Allow 60+ seconds for PyQt6 installation
pip install PyQt6 psutil pywin32

# Verify installation
python -c "import PyQt6, psutil; print('Dependencies OK')"
```

### Running the Application
```bash
# Direct execution
python MatrixDisplay.py

# Using provided batch file (Windows)
run_cpu_overlay.bat
```

**IMPORTANT:** This application requires a Windows environment with a display. It will NOT run properly in:
- Linux/macOS environments
- Headless/container environments
- WSL without X11 forwarding

**BATCH FILE NOTE:** The batch file has been updated to correctly reference `MatrixDisplay.py` (was previously referencing the old name `MatrixCPUdisplay.py`).

### Development Validation
```bash
# Test syntax and imports (works on any platform)
python -c "
import ast
with open('MatrixDisplay.py', 'r') as f:
    ast.parse(f.read())
print('Syntax validation: PASSED')
"

# Test core dependencies (partial - GUI components need Windows)
python -c "
import psutil
print(f'CPU cores: {psutil.cpu_count()}')
print(f'Current CPU: {psutil.cpu_percent(interval=1)}%')
print('Core dependencies: VALIDATED')
"
```

## Key Application Features

### Performance Monitoring
- Automatically suspends when CPU usage > 75%
- Resumes when CPU usage < 75% and no fullscreen apps detected
- Real-time monitoring every 2 seconds

### Visual Effects
- 600 simultaneous Matrix symbols falling at variable speeds
- Random explosion effects (0.001% chance per symbol)
- Physics-based particle interactions
- 60-second symbol trails with transparency
- CPU-responsive display suspension

### Window Behavior
- Transparent overlay using PyQt6 + pywin32
- Click-through window (WS_EX_TRANSPARENT)
- Always on top positioning
- Full-screen coverage with 60% height usage

## File Structure Reference

```
Matrix/
├── MatrixDisplay.py          # Main application (777 lines)
├── README.md                 # User documentation
├── ProjectDescription.mdc    # Detailed project specification
├── history.mdc              # Development changelog
├── run_cpu_overlay.bat      # Windows launcher script
├── MatrixDisplay.code-workspace  # VS Code workspace
└── .github/
    └── copilot-instructions.md   # This file
```

## Development Guidelines

### Making Changes
```bash
# ALWAYS validate syntax after changes
python -c "
import ast
with open('MatrixDisplay.py', 'r') as f:
    ast.parse(f.read())
print('Code validation: PASSED')
"

# Test basic functionality (where possible)
python -c "
import sys, os
sys.path.insert(0, '.')
# Basic imports test
try:
    import psutil
    print('✓ psutil working')
except Exception as e:
    print(f'✗ psutil error: {e}')
"
```

### Performance Considerations
- Target frame rate: 20 FPS (50ms per frame)
- Symbol update frequency: Every 50ms via QTimer
- CPU check frequency: Every 2 seconds
- Maximum symbols: 600 (reduced from 1200 for performance)

### Code Architecture
**Core Classes:**
- `MatrixWindow`: Main application window and controller
- `MatrixSymbol`: Individual falling symbols with physics
- `SymbolTrail`: Fading trails behind symbols
- `ExplosionParticle`: Physics particles from explosions
- `CodeEffect`: Explosion animation management

**Key Methods:**
- `update_symbols()`: Main animation loop (20 FPS)
- `check_system_state()`: CPU/fullscreen monitoring
- `paintEvent()`: Rendering pipeline
- `set_window_layer()`: Windows-specific layering

## Timing Expectations

**NEVER CANCEL these operations:**
- `pip install PyQt6`: 60-90 seconds
- Application startup: 2-3 seconds
- Symbol generation: Instantaneous
- Frame rendering: <50ms target

## Validation Scenarios

### After Making Changes
1. **Syntax Validation** (Required - works anywhere):
```bash
python -c "import ast; f=open('MatrixDisplay.py'); ast.parse(f.read()); f.close(); print('SYNTAX: OK')"
```

2. **Import Testing** (Partial - Windows features will fail on Linux):
```bash
python -c "
try:
    import psutil
    print('✓ psutil OK')
    import sys, random, time, math
    from collections import deque
    print('✓ Standard libraries OK')
except Exception as e:
    print(f'✗ Import error: {e}')
"
```

3. **Performance Testing** (Algorithm validation):
```bash
python -c "
import time, random
start = time.time()
# Simulate 600 symbols for 100 frames
for frame in range(100):
    symbols = [{'x': random.uniform(0, 1920), 'y': random.uniform(0, 1080)} for _ in range(600)]
duration = time.time() - start
print(f'Performance test: {duration:.3f}s (target: <5.0s)')
"
```

### Windows-Only Validation
These commands require a Windows environment with display:
```bash
# Full application test (Windows only)
python MatrixDisplay.py

# Quick GUI test (Windows only)
python -c "
from PyQt6.QtWidgets import QApplication
app = QApplication([])
print('GUI system: AVAILABLE')
app.quit()
"
```

### Manual Testing Scenarios (Windows Required)
When the application runs successfully, verify these behaviors:

**Startup Behavior:**
- Application creates transparent overlay covering 60% of screen height
- Matrix symbols begin falling immediately
- No visible window borders or title bar
- Overlay is click-through (desktop remains interactive)

**Visual Effects:**
- Green digital symbols falling at varying speeds
- Symbols occasionally change characters during descent
- Very rare explosion effects (may take several minutes to observe)
- CPU monitoring console messages every 2 seconds

**Performance Monitoring:**
- On high CPU systems (>75%): Display automatically suspends
- Console shows suspension message
- Display resumes when CPU normalizes

**Manual CPU Test:**
```bash
# In separate terminal - artificially load CPU to test suspension
python -c "
import threading
import time
def cpu_load():
    while True:
        pass
# Start multiple threads to load CPU
for _ in range(8):
    threading.Thread(target=cpu_load, daemon=True).start()
time.sleep(10)  # Load CPU for 10 seconds
"
```

## Common Issues & Solutions

### "ModuleNotFoundError: No module named 'win32gui'"
- **Solution**: Install pywin32: `pip install pywin32`
- **Note**: This is Windows-only functionality

### "libEGL.so.1: cannot open shared object file"
- **Solution**: This indicates a Linux environment. PyQt6 GUI features require Windows.
- **Workaround**: Use syntax and logic validation only

### Application appears to hang on startup
- **Cause**: Normal behavior - allow 2-3 seconds for window initialization
- **Action**: NEVER CANCEL - wait for completion

### High CPU usage
- **Expected**: Application automatically suspends at >75% CPU
- **Action**: Monitor for automatic suspension message in console

## CI/Build Information

**No formal CI pipeline exists** - this is a simple Python desktop application.

**No build process required** - direct Python execution.

**No tests exist** - validation is manual and syntax-based.

## Quick Reference Commands

```bash
# Complete setup from fresh clone
git clone <repo> && cd Matrix
pip install PyQt6 psutil pywin32
python -c "import ast; f=open('MatrixDisplay.py'); ast.parse(f.read()); f.close(); print('READY')"

# Run application (Windows only)
python MatrixDisplay.py

# Validate changes
python -c "import ast; f=open('MatrixDisplay.py'); ast.parse(f.read()); f.close(); print('SYNTAX: OK')"

# Performance check
python -c "import psutil; print(f'CPU: {psutil.cpu_percent(interval=1)}%')"
```

## Development History

Key evolution points documented in `history.mdc`:
- Started as CPU performance overlay
- Evolved to Matrix-style visualization  
- Added physics-based explosion system
- Implemented CPU-based suspension
- Optimized for 600 simultaneous symbols

**Remember**: Always validate syntax after changes, respect timing requirements, and understand that full functionality requires Windows environment.