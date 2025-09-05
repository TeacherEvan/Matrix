# Matrix Display - GitHub Copilot Instructions

Matrix Display is a Python-based desktop application that creates an interactive Matrix-style digital rain overlay for Windows desktops. It features falling symbols, dynamic color cycling, CPU usage monitoring, and physics-based explosion effects.

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Environment Setup
- **CRITICAL**: This application is designed for Windows and requires `pywin32` for full functionality.
- **Linux/macOS**: Basic functionality works but lacks window positioning and transparency features.
- Python 3.7+ is required (tested with Python 3.12.3).

### Installation Process
1. **Install Python dependencies**:
   
   **Windows**:
   ```bash
   pip install PyQt6 psutil pywin32
   ```
   
   **Linux/macOS**:
   ```bash
   pip install PyQt6 psutil
   # Note: pywin32 is Windows-only, skip it on Linux/macOS
   ```
   
   - **TIMING**: Installation takes 30-180 seconds depending on network. NEVER CANCEL.
   - **Expected output**: Should show successful installation of packages
   - **Known issues**: Network timeouts may require retrying the command

2. **Linux GUI testing setup** (for development):
   ```bash
   # Install required system libraries - TIMING: 60-180 seconds. NEVER CANCEL.
   sudo apt update && sudo apt install -y mesa-utils libegl1 libxrandr2 libxss1 libxcursor1 libxcomposite1 libasound2t64 libxi6 libxtst6 xvfb libxcb-cursor0
   
   # Start virtual display for testing
   export DISPLAY=:99
   Xvfb :99 -screen 0 1024x768x24 &
   
   # Use offscreen platform for GUI testing
   export QT_QPA_PLATFORM=offscreen
   ```

### Running the Application
- **Windows**: `python MatrixDisplay.py`
- **Auto-start on Windows**: Use `run_cpu_overlay.bat` and place shortcut in `shell:startup` folder
- **Linux (limited functionality)**: `QT_QPA_PLATFORM=offscreen python MatrixDisplay.py`

**IMPORTANT**: The batch file `run_cpu_overlay.bat` references the correct filename `MatrixDisplay.py`. If you see references to `MatrixCPUdisplay.py` in older documentation, that is the old filename - always use `MatrixDisplay.py`.

### Performance Characteristics
- **Startup time**: 1-2 seconds
- **CPU monitoring**: Updates every 1 second
- **Frame rate**: Target 30-50 FPS, automatically adjusts based on performance
- **Memory usage**: Typically 50-100MB with symbol trail caching

## Validation

### CRITICAL: Manual Testing Requirements
**ALWAYS** manually validate changes using these specific scenarios. Simply running `python MatrixDisplay.py` and checking it starts is **NOT sufficient** validation.

### Complete Testing Scenarios

#### 1. Installation Validation (Fresh Environment)
```bash
# Test complete installation from scratch
pip install PyQt6 psutil pywin32  # Windows
pip install PyQt6 psutil           # Linux

# Verify imports work
python -c "from PyQt6.QtWidgets import QApplication; import psutil; print('✓ Dependencies OK')"
```
**Expected result**: No import errors, "✓ Dependencies OK" message

#### 2. Basic Application Startup
```bash
python MatrixDisplay.py
```
**Validation checklist**:
- [ ] Application window appears (Windows) or starts without errors (Linux)
- [ ] Matrix rain symbols begin falling immediately
- [ ] CPU percentage displays in bottom area and updates every ~1 second
- [ ] No crash or error messages in console
- [ ] Window covers approximately 60% of screen height (Windows only)

#### 3. CPU Monitoring Integration Test
**This is the core feature - must be thoroughly tested**:

1. **Normal operation**: Let application run with normal CPU
   - [ ] Symbols fall continuously
   - [ ] CPU percentage shows reasonable values (0-50%)

2. **High CPU simulation**: Run CPU-intensive task
   ```bash
   # In another terminal, simulate high CPU
   python -c "while True: pass"  # Creates high CPU load
   ```
   - [ ] CPU percentage should rise above 75%
   - [ ] Matrix rain should **stop falling** (symbols freeze)
   - [ ] Console should show "Suspending Matrix display due to high CPU usage"

3. **Recovery test**: Stop the CPU-intensive task
   - [ ] CPU percentage should drop below 25%
   - [ ] Matrix rain should **resume falling**
   - [ ] Console should show "Resuming Matrix display, CPU usage normal"

**TIMING**: This test takes 2-3 minutes to properly validate. NEVER SKIP.

#### 4. Color Cycling Validation
**Must observe for at least 30 seconds**:
- [ ] Initial color (usually green Matrix-style)
- [ ] After 10 seconds: Color changes to blue
- [ ] After 20 seconds: Color changes to purple
- [ ] After 30 seconds: Color changes to black/gray
- [ ] Cycle continues through LSD (multicolor) theme

#### 5. Explosion Physics Test
**This is a patience test - explosions are rare (0.001% probability)**:
- Let application run for 2-5 minutes
- [ ] Observe at least one explosion effect (blood-red particles)
- [ ] Verify explosion particles affect nearby symbols
- [ ] Verify affected symbols change trajectory and color

**Note**: If no explosions occur in 5 minutes, this is normal due to low probability

#### 6. Performance Validation
Monitor console output during operation:
- [ ] No "Average frame time" warnings >50ms
- [ ] Smooth animation without stuttering
- [ ] Memory usage stable (check Task Manager/Activity Monitor)
- [ ] CPU usage from Matrix app itself <10% when not suspended

### Linux Testing (Development Only)
```bash
export QT_QPA_PLATFORM=offscreen
python3 -c "
from PyQt6.QtWidgets import QApplication
import psutil
print('CPU usage:', psutil.cpu_percent(interval=1))
app = QApplication([])
app.quit()
print('✓ Basic functionality works')
"
```

## Code Structure and Navigation

### Key Files
- **`MatrixDisplay.py`** (776 lines): Main application file containing all functionality
- **`run_cpu_overlay.bat`**: Windows startup script
- **`README.md`**: Basic usage instructions  
- **`ProjectDescription.mdc`**: Detailed technical specifications
- **`history.mdc`**: Complete development log with all changes
- **`MatrixDisplay.code-workspace`**: VSCode workspace configuration

### Important Classes and Functions
```python
# Key classes in MatrixDisplay.py:
class SymbolTrail:      # Lines 19-54: Fading trails behind symbols
class CodeEffect:       # Lines 56-95: Explosion particle effects  
class Symbol:           # Lines 97-168: Individual falling symbols
class MatrixWindow:     # Lines 170-776: Main application window

# Key methods:
def update_symbols():           # Symbol movement and physics
def update_cpu_monitoring():    # CPU usage tracking
def paintEvent():              # Main rendering loop
def apply_window_effects():    # Windows-specific transparency/positioning
```

### Symbol System
- **600 simultaneous symbols** for optimal density
- **Trail duration**: 60 seconds with gradual fading
- **Explosion probability**: 0.001% per symbol (extremely rare events)
- **Color themes**: 5 themes cycling every 10 seconds
- **Font**: Various symbols including ASCII, numbers, Japanese katakana

### CPU Integration
- **Suspension threshold**: >75% CPU usage pauses rain
- **Resume threshold**: <25% CPU usage resumes rain  
- **Monitoring interval**: 1 second updates
- **Fullscreen detection**: Automatically pauses during fullscreen apps (Windows only)

### Expected Error Messages and Solutions

**Common startup errors and fixes:**

1. **`ModuleNotFoundError: No module named 'PyQt6'`**:
   - **Solution**: Run `pip install PyQt6 psutil`
   - **Cause**: Dependencies not installed

2. **`ModuleNotFoundError: No module named 'win32gui'`**:
   - **On Windows**: Run `pip install pywin32`
   - **On Linux**: Expected - application has limited functionality without Windows features

3. **`qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`**:
   - **Solution**: Use `export QT_QPA_PLATFORM=offscreen` for Linux testing
   - **Alternative**: Install missing X11 libraries (see Linux setup above)

4. **Network timeout during pip install**:
   - **Solution**: Retry the command - network issues are common
   - **Expected timing**: Allow up to 3 minutes for complete installation

### Performance Issues
- Monitor console output for "Average frame time" warnings
- Frame times >50ms indicate performance problems
- Reduce symbol count if performance issues persist

### Windows-Specific Features That Don't Work on Linux
- Window transparency and click-through behavior
- Always-on-top positioning
- Fullscreen application detection
- Advanced window layering effects

## Development Guidelines

### Making Changes
- **Always test on Windows** for full functionality validation
- **Linux testing** only for basic import/logic verification
- **Performance impact**: Monitor frame times when adding features
- **Symbol limits**: Don't exceed 1200 symbols (causes performance issues)
- **Trail optimization**: Long trails (>60s) can cause memory issues

### Code Style
- Follow existing naming conventions (camelCase for methods, PascalCase for classes)
- Add debug print statements for validation (follow existing pattern)
- Keep symbol physics calculations efficient (runs 30-50 times per second)
- Use QColor objects for all color manipulations

### Adding New Features
1. Test basic functionality first with minimal code
2. Add performance timing if feature affects rendering
3. Validate memory usage for features that create objects
4. Test color theme compatibility (ensure works with all 5 themes)
5. Consider Windows vs Linux compatibility

## Quick Reference Commands

```bash
# Basic development workflow:
pip install PyQt6 psutil                    # Linux setup
pip install PyQt6 psutil pywin32            # Windows setup  
python MatrixDisplay.py                     # Run application
export QT_QPA_PLATFORM=offscreen            # Linux GUI testing

# Performance monitoring:
# Watch console output for frame time warnings
# Monitor CPU percentage display updates
# Verify smooth symbol animation

# File locations:
ls -la *.py *.bat *.md                      # All main files
cat README.md                               # Basic usage info
cat ProjectDescription.mdc                  # Technical details
cat history.mdc                            # Development history
```

**CRITICAL**: This is a Windows-first application. Full functionality testing requires a Windows environment with pywin32. Linux testing is limited to basic imports and logic verification only.