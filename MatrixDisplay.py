import sys
import random
import time
import math
from collections import deque
# PyQt6 is generally recommended over PySide6 unless specific licensing is a concern
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QRect, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QScreen, QPainterPath, QBrush, QLinearGradient, QFont

# pywin32 for Windows-specific features
import win32gui
import win32con
import win32api

# For CPU monitoring
import psutil

class SymbolTrail:
    """Represents a fading trail left behind a symbol"""
    # Class-level reusable color object for drawing (optimization)
    _draw_color = QColor()
    
    def __init__(self, symbol, pos_x, pos_y, color, start_time, duration=60.0):
        self.symbol = symbol         # The Matrix symbol character
        self.pos = QPointF(pos_x, pos_y)  # Position of the trail
        self.color = color           # Base color of trail
        self.start_time = start_time # Time when trail was created
        self.duration = duration     # How long the trail remains visible
        # Pre-calculate the base alpha for faster draw operations
        self._base_alpha = color.alpha() * 0.56  # 0.7 * 0.8 = 0.56 (30% + 20% more transparent)
        
    def is_active(self, current_time):
        """Check if the trail is still active"""
        return current_time - self.start_time < self.duration
        
    def get_fade_factor(self, current_time):
        """Get fade factor from 1.0 (fresh) to 0.0 (expired)"""
        elapsed = current_time - self.start_time
        return max(0.0, 1.0 - elapsed / self.duration)
        
    def draw(self, painter, current_time):
        """Draw the symbol trail with fading effect"""
        # Optimized: inline is_active check to avoid method call overhead
        elapsed = current_time - self.start_time
        if elapsed >= self.duration:
            return
            
        # Optimized: calculate fade factor inline
        fade_factor = 1.0 - elapsed / self.duration
        
        # Optimized: use pre-calculated base alpha and reuse class-level color object
        trail_alpha = int(self._base_alpha * fade_factor)
        SymbolTrail._draw_color.setRgb(
            self.color.red(), self.color.green(), self.color.blue(), trail_alpha
        )
        
        painter.setPen(SymbolTrail._draw_color)
        # Removed redundant painter.setFont() call - uses current font automatically
        painter.drawText(self.pos, self.symbol)

class ExplosionParticle:
    """Represents a single particle in an explosion that can interact with other symbols"""
    # Class-level cached color to avoid creating new QColor in hot paths
    _BLOOD_RED = QColor(200, 0, 0, 220)
    # Cache math.sqrt for faster access
    _sqrt = math.sqrt
    
    def __init__(self, symbol, x_pos, y_pos, direction, speed, color, size):
        self.symbol = symbol
        self.pos = QPointF(x_pos, y_pos)
        self.direction = direction   # (dx, dy) normalized direction vector
        self.speed = speed
        self.color = color
        self.size = size * 2.0  # Double the size of explosion particles
        self.last_pos = QPointF(x_pos, y_pos)
        self.active = True
        self.hit_force = speed * 0.2  # Force applied to symbols when hit
        
    def update(self, elapsed):
        """Update position based on direction and speed"""
        self.last_pos = QPointF(self.pos)
        # Move according to direction and speed (reduced by 50%)
        dx = self.direction[0] * self.speed * elapsed * 0.5
        dy = self.direction[1] * self.speed * elapsed * 0.5
        self.pos.setX(self.pos.x() + dx)
        self.pos.setY(self.pos.y() + dy)
        
    def check_collision(self, symbol):
        """Check if this particle collides with a symbol"""
        # Optimized: use squared distance to avoid expensive sqrt()
        collision_dist = self.size + symbol.size
        collision_dist_sq = collision_dist * collision_dist
        dx = self.pos.x() - symbol.pos.x()
        dy = self.pos.y() - symbol.pos.y()
        dist_sq = dx*dx + dy*dy
        
        return dist_sq < collision_dist_sq
    
    def affect_symbol(self, symbol):
        """Apply physics effect to a symbol when hit"""
        # Calculate impulse direction (from particle to symbol)
        dx = symbol.pos.x() - self.pos.x()
        dy = symbol.pos.y() - self.pos.y()
        
        # Optimized: avoid sqrt for normalization when possible, use cached sqrt
        length_sq = dx*dx + dy*dy
        if length_sq > 0.001:  # Avoid division by very small numbers
            length = ExplosionParticle._sqrt(length_sq)
            dx /= length
            dy /= length
        else:
            # Use default direction if symbols are too close
            dx, dy = 1.0, 0.0
            
        # Apply impulse to symbol velocity - random drift plus directed force
        symbol.drift_x = dx * self.hit_force + random.uniform(-1, 1)
        symbol.drift_y = dy * self.hit_force + random.uniform(-1, 1)
        
        # Flag symbol as affected
        symbol.affected_by_explosion = True
        
        # Optimized: use class-level cached color instead of creating new QColor
        symbol.color = ExplosionParticle._BLOOD_RED

class CodeEffect:
    """Represents a special effect when symbols explode randomly"""
    # Class-level symbol pool for better performance
    SYMBOL_POOL = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
    SYMBOL_POOL_LEN = len(SYMBOL_POOL)
    
    # Class-level cached colors to avoid repeated QColor creation
    _BLOOD_RED_220 = QColor(200, 0, 0, 220)
    _BLOOD_RED_180 = QColor(200, 0, 0, 180)
    _draw_color = QColor()  # Reusable color for drawing
    
    # Cache for math functions
    _cos = math.cos
    _sin = math.sin
    _sqrt = math.sqrt
    
    def __init__(self, x_pos, y_pos, color, start_time, size_factor=1.0):
        self.x_pos = x_pos                # X position of explosion
        self.y_pos = y_pos                # Y position of explosion
        self.color = color                # Base color
        self.start_time = start_time      # Time when animation started
        self.duration = 4.8               # Animation duration doubled again (from 2.4 to 4.8)
        self.size_factor = size_factor    # Relative size of explosion (randomized)
        
        # Base radius varies from 50 to 150 (randomized for each explosion)
        self.radius = 75 * self.size_factor
        
        self.particles = []               # Explosion particles
        self.symbol_trails = []           # Trails left by particles
        self.last_update_time = start_time
        
        # Generate effect symbols (more symbols for richer effect)
        num_symbols = int(20 * size_factor)  # Scale number of particles with size
        
        # Reuse class-level cached color
        self.effect_color = CodeEffect._BLOOD_RED_220
        
        # Pre-calculate constants for particle creation
        two_pi = 2 * math.pi
        sqrt_size = CodeEffect._sqrt(size_factor)
        
        # Create particle objects
        for i in range(num_symbols):
            # Random symbol from cached pool
            symbol = self.SYMBOL_POOL[random.randrange(self.SYMBOL_POOL_LEN)]
            
            # Calculate direction angles with variation
            angle = two_pi * i / num_symbols + random.uniform(-0.2, 0.2)
            direction = (CodeEffect._cos(angle), CodeEffect._sin(angle))
            
            # Random speeds (vary based on size factor) - reduced by 50%
            speed = random.uniform(10, 25) * sqrt_size  # Reduced from 20-50 to 10-25
            
            # Create particle with randomized size
            particle_size = random.uniform(2, 5) * size_factor
            
            # Add particle
            self.particles.append(
                ExplosionParticle(
                    symbol, x_pos, y_pos, direction, speed, 
                    self.effect_color, particle_size
                )
            )
        
    def is_active(self, current_time):
        """Check if the animation is still active"""
        return current_time - self.start_time < self.duration
        
    def get_progress(self, current_time):
        """Get animation progress from 0.0 to 1.0"""
        elapsed = current_time - self.start_time
        return min(1.0, elapsed / self.duration)
        
    def update_positions(self, current_time, symbols):
        """Update particle positions, check for collisions with symbols, and return any new trails"""
        if not self.is_active(current_time):
            return []
            
        elapsed_since_last = current_time - self.last_update_time
        self.last_update_time = current_time
        
        progress = self.get_progress(current_time)
        new_trails = []
        
        # Update particle positions and check for collisions
        for particle in self.particles:
            if not particle.active:
                continue
                
            # Update particle position
            particle.update(elapsed_since_last)
            
            # Check for collisions with symbols (optimized)
            for i, symbol in enumerate(symbols):
                if symbol is not None and symbol.is_active:
                    if particle.check_collision(symbol):
                        # Apply physics effect to symbol
                        particle.affect_symbol(symbol)
                        # Deactivate particle after first collision for performance
                        particle.active = False
                        break
            
            # Create occasional trails
            if random.random() < 0.4 and progress > 0.1:
                # Optimized: use class-level cached blood red color
                # Create a fading trail
                new_trails.append(
                    SymbolTrail(
                        particle.symbol,
                        particle.pos.x(), particle.pos.y(),
                        CodeEffect._BLOOD_RED_180, 
                        current_time,
                        duration=1.2  # Short duration doubled (from 0.6 to 1.2)
                    )
                )
            
        return new_trails
        
    def draw(self, painter, current_time):
        """Draw the code effect"""
        if not self.is_active(current_time):
            return
            
        progress = self.get_progress(current_time)
        
        # Fade out particles as the animation progresses
        alpha = int(255 * (1.0 - progress * 0.7))
        # Optimized: reuse class-level color object instead of creating new QColor
        CodeEffect._draw_color.setRgb(200, 0, 0, alpha)
        
        painter.setPen(CodeEffect._draw_color)
        
        # Optimized: get base font once and track size changes
        base_font = QFont(painter.font())
        current_font_size = -1
        
        # Draw each particle
        for particle in self.particles:
            if particle.active:
                target_size = particle.size * 2.5
                # Only update font if size changed
                if current_font_size != target_size:
                    base_font.setPointSizeF(target_size)
                    painter.setFont(base_font)
                    current_font_size = target_size
                
                # Draw the particle
                painter.drawText(particle.pos, particle.symbol)

class MatrixSymbol:
    """Represents a falling Matrix symbol"""
    # Class-level symbol pool for better performance
    SYMBOL_POOL = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
    SYMBOL_POOL_LEN = len(SYMBOL_POOL)
    
    # Pre-cached shared color for squares (optimization: avoid per-instance creation)
    _SQUARE_COLOR = QColor(255, 255, 255, 120)
    
    def __init__(self, x, y, speed, color, size):
        self.pos = QPointF(x, y)
        self.last_pos = QPointF(x, y)  # Track previous position for trail generation
        self.speed = speed
        
        # Increase transparency by 40% in total (30% + additional 10%) by reducing alpha
        original_alpha = color.alpha()
        reduced_alpha = int(original_alpha * 0.6)  # 40% more transparent
        color.setAlpha(reduced_alpha)
        self.color = color
        
        self.size = size * 1.0  # Original size (changed from 0.8 to 1.0)
        self.is_active = True           # Flag to check if symbol is active
        self.change_counter = 0         # Counter for changing the symbol
        self.trail_counter = 0          # Counter to control trail frequency
        
        # Square properties - use class-level cached color
        self.has_square = True
        self.square_color = MatrixSymbol._SQUARE_COLOR  # Reuse shared color instance
        self.square_flash_timer = 0
        self.square_visible = True
        
        # Physics properties
        self.drift_x = 0                # Horizontal drift (added by explosions)
        self.drift_y = 0                # Vertical drift (added by explosions)
        self.affected_by_explosion = False  # Flag to track if affected
        self.drift_damping = 0.95       # Damping factor to gradually reduce drift
        
        # Explosion properties - pre-initialized to avoid hasattr() checks in hot paths
        self.rigged_to_explode = False  # Flag for delayed explosion
        self.explosion_time = 0.0       # Time when explosion should trigger
        
        # Choose a random Matrix-like character from cached pool
        self.symbol = self.SYMBOL_POOL[random.randrange(self.SYMBOL_POOL_LEN)]
        
        # Randomize fall time before disappearing
        self.max_fall_time = random.uniform(10, 30)  # Between 10 and 30 seconds
        self.birth_time = time.time()
        
        # Chance to have a brighter (lead) symbol
        self.is_lead = random.random() < 0.15
        if self.is_lead:
            bright_color = QColor(self.color)
            bright_alpha = min(255, reduced_alpha + 70)  # Maintain 40% transparency increase
            bright_color.setAlpha(bright_alpha)
            self.color = bright_color

class MatrixWindow(QWidget):
    # Class-level cached math functions for performance
    _sin = math.sin  # Cache math.sin for faster access in hot loops
    
    def __init__(self):
        super().__init__()
        
        # --- Performance Optimizations ---
        # Pre-defined symbol pool for better performance
        self.symbol_pool = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
        self.symbol_pool_len = len(self.symbol_pool)
        
        # Pre-calculated colors for better performance
        self._blood_red_cache = QColor(200, 0, 0, 220)
        self._trail_alpha_cache = {}  # Cache for trail alpha calculations
        self._white_pulse_cache = QColor(255, 255, 255, 255)  # Reusable white color for pulsating
        
        # Performance counters
        self._total_symbols_created = 0
        self._total_trails_created = 0
        # ------------------------------
        
        # --- Performance Tracking ---
        self.last_frame_time = time.time()
        self.frame_times = deque(maxlen=60)  # Keep last 60 frame times for average
        # --------------------------

        # --- Color Theme Management ---
        self.color_themes = {
            "green": [
                QColor(0, 255, 50, 180),   # Bright matrix green
                QColor(0, 220, 40, 160),   # Medium matrix green
                QColor(0, 180, 30, 140),   # Dark matrix green
                QColor(0, 160, 20, 120),   # Very dark matrix green
                QColor(0, 240, 60, 200)    # Very bright matrix green
            ],
            "red": [
                QColor(200, 0, 0, 180),    # Blood red
                QColor(220, 0, 0, 160),    # Bright red
                QColor(180, 0, 0, 140),    # Medium red
                QColor(160, 0, 0, 120),    # Dark red
                QColor(240, 0, 0, 200)     # Very bright red
            ]
        }
        
        # Use matrix green theme
        self.symbol_colors = self.color_themes["green"]
        
        # --- Matrix Symbol System Setup ---
        self.symbols = []
        self.max_symbols = 600         # Reduced by 50% from 1200 to 600
        self.symbol_count = 0          # Active symbol count for quick access
        # ---------------------------

        # --- Code Effect Animation State ---
        self.code_effects = []             # List of active code effects
        self.symbol_trails = []            # List to store symbol trails
        # ------------------------------
        
        # --- Symbol Generation Timing ---
        self.last_symbol_add_time = time.time()
        self.symbol_add_interval = 2.0     # Add a new symbol every 2 seconds
        # ------------------------------
        
        # --- Monitoring State ---
        self.monitoring_timer = None
        self.is_suspended = False
        self.last_check_time = time.time()
        self.fullscreen_check_interval = 5.0  # Check for fullscreen apps every 5 seconds
        # -----------------------

        self.initUI()
        self.setup_timer()
        self.setup_monitoring()
        # No longer need explicit HWND for drawing, but keep for layering
        self.hwnd = self.winId()

    def initUI(self):
        # --- Basic Window Setup ---
        self.setWindowTitle('Matrix Display')
        # Flags for a borderless, transparent, always-on-top (initially) window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |        # No border or title bar
            Qt.WindowType.WindowStaysOnTopHint |       # Keep on top (will be refined later)
            Qt.WindowType.Tool                         # Prevent appearing in taskbar/alt-tab
        )
        # Enable transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Black background with 40% increased transparency (60% of original opacity)
        bg_opacity = int(180 * 0.6)  # 40% more transparent
        self.setStyleSheet(f"background-color: rgba(0, 0, 0, {bg_opacity});")

        # --- Positioning and Sizing ---
        screen = QApplication.primaryScreen()
        if not screen:
            print("Error: Could not get primary screen.")
            sys.exit(1)
            
        screen_geometry = screen.geometry()
        self.screen_width = screen_geometry.width()
        self.screen_height = screen_geometry.height()

        # Use full screen dimensions
        self.setGeometry(0, 0, self.screen_width, self.screen_height)
        self.overlay_height = self.screen_height  # Store height

        # Set fixed width Matrix font
        self.matrix_font = QFont("Courier New", 9)  # Increased from 7 to 9
        self.matrix_font.setBold(True)
        self.setFont(self.matrix_font)

        # Add initial symbols - preallocate symbol list for performance
        self.symbols = [None] * self.max_symbols
        # Start with 0 symbols instead of half-full

    def setup_monitoring(self):
        """Set up the monitoring timer to check CPU usage and fullscreen apps"""
        self.monitoring_timer = QTimer(self)
        self.monitoring_timer.timeout.connect(self.check_system_state)
        self.monitoring_timer.start(2000)  # Check every 2 seconds
        
    def is_fullscreen_app_running(self):
        """Check if any fullscreen application is currently running"""
        try:
            foreground_window = win32gui.GetForegroundWindow()
            if foreground_window and foreground_window != self.hwnd:
                # Get window rect
                window_rect = win32gui.GetWindowRect(foreground_window)
                window_width = window_rect[2] - window_rect[0]
                window_height = window_rect[3] - window_rect[1]
                
                # Check if window covers at least 90% of screen
                if (window_width >= self.screen_width * 0.9 and 
                    window_height >= self.screen_height * 0.9):
                    
                    # Get window style to check if it's a game/fullscreen app
                    style = win32gui.GetWindowLong(foreground_window, win32con.GWL_STYLE)
                    
                    # Many games and fullscreen apps don't have these borders/decorations
                    if (style & win32con.WS_CAPTION) == 0 or (style & win32con.WS_THICKFRAME) == 0:
                        return True
                        
                    # Check window title for keywords that might indicate games
                    window_title = win32gui.GetWindowText(foreground_window).lower()
                    game_keywords = ['game', 'play', 'factorio', 'minecraft', 'steam', 'directx', 'fullscreen']
                    for keyword in game_keywords:
                        if keyword in window_title:
                            return True
        except Exception as e:
            print(f"Error checking fullscreen apps: {e}")
            
        return False
        
    def check_system_state(self):
        """Check CPU usage and running apps, suspend if necessary"""
        current_time = time.time()
        
        # Only do full check periodically to avoid performance impact
        if current_time - self.last_check_time < self.fullscreen_check_interval:
            # Do a quick CPU check more frequently
            cpu_percent = psutil.cpu_percent(interval=None)
            if cpu_percent > 75 and not self.is_suspended:
                print(f"Suspending Matrix display due to high CPU usage: {cpu_percent}%")
                self.suspend_matrix()
            elif cpu_percent <= 75 and self.is_suspended and not self.is_fullscreen_app_running():
                print(f"Resuming Matrix display, CPU usage normal: {cpu_percent}%")
                self.resume_matrix()
            return
            
        self.last_check_time = current_time
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        print(f"Current CPU usage: {cpu_percent}%")
        
        # Check for fullscreen applications
        fullscreen_detected = self.is_fullscreen_app_running()
        
        if (cpu_percent > 75 or fullscreen_detected) and not self.is_suspended:
            reason = "high CPU usage" if cpu_percent > 75 else "fullscreen application"
            print(f"Suspending Matrix display due to {reason}")
            self.suspend_matrix()
        elif cpu_percent <= 75 and not fullscreen_detected and self.is_suspended:
            print("Resuming Matrix display, system state normal")
            self.resume_matrix()
    
    def suspend_matrix(self):
        """Suspend the Matrix display"""
        if not self.is_suspended:
            self.symbol_timer.stop()
            self.is_suspended = True
            
            # Reset all display elements
            self.reset_display_state()
            
            self.hide()  # Hide the window
    
    def resume_matrix(self):
        """Resume the Matrix display"""
        if self.is_suspended:
            # Make sure we're starting with a clean state
            self.reset_display_state()
            
            self.symbol_timer.start()
            self.is_suspended = False
            self.show()  # Show the window
            
            # Reset the window to be on top when resuming
            if self.hwnd:
                self.set_window_layer()
    
    def reset_display_state(self):
        """Reset all display elements to their initial state"""
        # Clear all active symbols
        for i in range(self.max_symbols):
            if self.symbols[i] is not None and self.symbols[i].is_active:
                self.symbols[i].is_active = False
        
        # Reset symbol count
        self.symbol_count = 0
        
        # Clear all explosion effects
        self.code_effects.clear()
        
        # Clear all symbol trails
        self.symbol_trails.clear()
        
        # Reset timing
        self.last_symbol_add_time = time.time()
        self.last_frame_time = time.time()

    def add_symbol(self, x_pos=None):
        """Adds a new Matrix symbol"""
        if self.symbol_count >= self.max_symbols:
            return

        # Find first available slot
        for i in range(self.max_symbols):
            if self.symbols[i] is None or not self.symbols[i].is_active:
                x = x_pos if x_pos is not None else random.uniform(0, self.screen_width)
                y = random.uniform(-20, 0) # Start just above the view
                speed = random.uniform(1, 5) # Base speed restored to original range (was 0.5-2.5, now doubled back)
                color = random.choice(self.symbol_colors)
                # Adjust alpha based on speed (faster = brighter)
                color.setAlpha(int(max(100, min(255, color.alpha() + speed * 10))))
                size = random.uniform(8, 12) # Font size variation increased by 1.25x (from 6.4-9.6 to 8-12)

                self.symbols[i] = MatrixSymbol(x, y, speed, color, size)
                self.symbol_count += 1
                self._total_symbols_created += 1
                return
    
    def remove_symbol(self, index):
        """Mark a symbol as inactive"""
        if 0 <= index < self.max_symbols and self.symbols[index] is not None:
            self.symbols[index].is_active = False
            self.symbol_count -= 1

    def setup_timer(self):
        # Timer for symbol updates
        self.symbol_timer = QTimer(self)
        self.symbol_timer.timeout.connect(self.update_symbols)
        self.symbol_timer.start(50) # Update at ~20fps (more Matrix-like stuttery feeling)

    def update_symbols(self):
        """Update symbol positions and handle animations"""
        current_time = time.time()
        
        frame_duration = current_time - self.last_frame_time
        self.frame_times.append(frame_duration)
        self.last_frame_time = current_time
        
        # Calculate average frame time and log if it's high
        if len(self.frame_times) >= 60:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            if avg_frame_time > 0.05:  # More than 50ms (less than 20fps)
                print(f"Performance Warning: Avg frame time {avg_frame_time*1000:.1f}ms | "
                      f"Symbols: {self.symbol_count}/{self.max_symbols} | "
                      f"Trails: {len(self.symbol_trails)} | "
                      f"Effects: {len(self.code_effects)}")
            elif len(self.frame_times) == 60:  # Log performance stats periodically
                print(f"Performance: {avg_frame_time*1000:.1f}ms avg | "
                      f"Symbols: {self.symbol_count} | Trails: {len(self.symbol_trails)}")
        
        widget_height = self.overlay_height
        
        # Symbol generation every 2 seconds
        if self.symbol_count < self.max_symbols and current_time - self.last_symbol_add_time >= self.symbol_add_interval:
            self.add_symbol()
            self.last_symbol_add_time = current_time

        # --- Clean up expired code effects and trails ---
        i = 0
        while i < len(self.code_effects):
            # Update effect positions and collect any new trails
            new_trails = self.code_effects[i].update_positions(current_time, self.symbols)
            self.symbol_trails.extend(new_trails)
            
            if not self.code_effects[i].is_active(current_time):
                self.code_effects.pop(i)
            else:
                i += 1
                
        # --- Clean up expired symbol trails (optimized batch cleanup) ---
        if len(self.symbol_trails) > 100:  # Only clean up when we have many trails
            # Use list comprehension for faster cleanup
            self.symbol_trails = [trail for trail in self.symbol_trails if trail.is_active(current_time)]
        else:
            # Regular cleanup for smaller lists
            i = 0
            while i < len(self.symbol_trails):
                if not self.symbol_trails[i].is_active(current_time):
                    self.symbol_trails.pop(i)
                else:
                    i += 1

        # --- Update Symbol Positions & Check for Random Explosions (optimized) ---
        symbols_to_remove = []  # Batch removal for better performance
        
        for i, s in enumerate(self.symbols):
            if s is None or not s.is_active:
                continue
                
            # Store last position before updating
            s.last_pos = QPointF(s.pos)
            
            # Update square flashing
            s.square_flash_timer += 1
            if s.square_flash_timer >= 5:  # Flash every 250ms (at 20fps)
                s.square_flash_timer = 0
                s.square_visible = not s.square_visible
            
            # Apply physics drift if affected by an explosion
            if s.affected_by_explosion:
                # Apply drift to position
                s.pos.setX(s.pos.x() + s.drift_x)
                s.pos.setY(s.pos.y() + s.drift_y)
                
                # Dampen drift for next frame
                s.drift_x *= s.drift_damping
                s.drift_y *= s.drift_damping
                
                # If drift becomes very small, reset affected flag
                if abs(s.drift_x) < 0.1 and abs(s.drift_y) < 0.1:
                    s.affected_by_explosion = False
                    s.drift_x = 0
                    s.drift_y = 0
            else:
                # Normal falling motion if not affected by explosion
                s.pos.setY(s.pos.y() + s.speed * 2)  # Doubled falling speed
            
            # Occasionally change the symbol character (Matrix-like effect)
            s.change_counter += 1
            if s.change_counter >= random.randint(5, 20):  # Change frequency varies
                s.change_counter = 0
                # Use cached symbol pool for better performance
                s.symbol = self.symbol_pool[random.randrange(self.symbol_pool_len)]
            
            # Create trails behind falling symbols
            s.trail_counter += 1
            if s.trail_counter >= 2:  # Create trail frequently for Matrix effect
                s.trail_counter = 0
                
                # Only create trails if there has been movement
                # Optimized: cache position values to avoid repeated method calls
                last_y = s.last_pos.y()
                last_x = s.last_pos.x()
                pos_y = s.pos.y()
                pos_x = s.pos.x()
                
                if abs(last_y - pos_y) > 0.5 or abs(last_x - pos_x) > 0.5:
                    # Optimized: calculate trail alpha once and create color efficiently
                    trail_alpha = int(s.color.alpha() * 0.6)
                    trail_color = QColor(s.color)
                    trail_color.setAlpha(trail_alpha)
                    
                    # Add trail at the last position with optimized 30-second duration
                    self.symbol_trails.append(
                        SymbolTrail(
                            s.symbol,
                            last_x, last_y,
                            trail_color, current_time,
                            duration=30.0  # Reduced from 60 to 30 seconds for better performance
                        )
                    )
                    self._total_trails_created += 1
            
            # Check if symbol has been falling too long (based on randomized max_fall_time)
            if current_time - s.birth_time > s.max_fall_time:
                self.remove_symbol(i)
                continue
            
            # Random explosion with 0.0003% chance per symbol (further reduced for performance)
            if random.random() < 0.000003:  # 0.0003% chance (reduced from 0.0005% for better performance)
                # Mark this symbol for explosion (will happen in 3 seconds)
                s.rigged_to_explode = True
                s.explosion_time = current_time + 3.0
                continue

            # Check if symbol is rigged to explode and it's time
            # Optimized: removed hasattr() checks since attributes are pre-initialized
            if s.rigged_to_explode and current_time >= s.explosion_time:
                # Create a code effect at the current position
                # Use cached blood red color for explosion
                
                # Randomize explosion size between 0.5 and 2.5 times base size
                size_factor = random.uniform(0.5, 2.5)
                
                # Add code effect with current time as start time
                self.code_effects.append(
                    CodeEffect(s.pos.x(), s.pos.y(), self._blood_red_cache, current_time, size_factor)
                )
                
                # Remove symbol after it explodes
                self.remove_symbol(i)
                continue
            
            # Remove symbol if it goes outside the widget bounds
            if (s.pos.y() > widget_height + 20 or 
                s.pos.x() < -20 or 
                s.pos.x() > self.screen_width + 20):
                self.remove_symbol(i)

        # Trigger repaint
        self.update()

    def paintEvent(self, event):
        current_time = time.time()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set font for all Matrix symbols
        font = self.matrix_font
        painter.setFont(font)

        rect = self.rect()
        widget_height = rect.height()
        
        # --- Draw Symbol Trails (draw first so they appear behind symbols) ---
        for trail in self.symbol_trails:
            trail.draw(painter, current_time)
        
        # --- Draw Code Effects ---
        for effect in self.code_effects:
            effect.draw(painter, current_time)
        
        # --- Draw Matrix Symbols (optimized) ---
        base_font = QFont(font)
        current_font_size = -1  # Track current font size to avoid redundant operations
        
        for s in self.symbols:
            if s is None or not s.is_active:
                continue
            
            # Draw flashing square first (if visible)
            # Optimized: removed hasattr() checks since attributes are pre-initialized
            if s.square_visible and s.has_square:
                square_size = s.size
                square_rect = QRect(
                    int(s.pos.x()), 
                    int(s.pos.y() - square_size/2), # Slightly above symbol
                    int(square_size), 
                    int(square_size)
                )
                painter.fillRect(square_rect, s.square_color)
            
            # Calculate target font size
            target_font_size = s.size
            
            # Check if symbol is rigged to explode
            # Optimized: removed hasattr() check since attribute is pre-initialized
            if s.rigged_to_explode:
                # Pulsating white effect for symbols about to explode
                # Optimized: use cached sin function for faster attribute lookup
                pulse_intensity = 0.5 + 0.5 * MatrixWindow._sin(current_time * 5)  # 0.5 to 1.0 pulsating
                # Optimized: reuse cached white color and just update alpha
                self._white_pulse_cache.setAlpha(int(255 * pulse_intensity))
                painter.setPen(self._white_pulse_cache)
                
                # Increase size for emphasis (pulsating size)
                size_multiplier = 1.0 + 0.5 * pulse_intensity
                target_font_size = s.size * size_multiplier
            else:
                # Normal symbol
                painter.setPen(s.color)
            
            # Only update font if size changed (optimization)
            if current_font_size != target_font_size:
                base_font.setPointSizeF(target_font_size)
                painter.setFont(base_font)
                current_font_size = target_font_size
            
            # Draw the symbol
            painter.drawText(s.pos, s.symbol)

    def showEvent(self, event):
        # Attempt advanced layering *after* the window is shown and has a valid HWND
        super().showEvent(event)
        # Make sure HWND is obtained before trying to set layer
        if not self.hwnd:
            self.hwnd = self.winId()
            print(f"HWND obtained in showEvent: {self.hwnd}")

        if self.hwnd:
            self.set_window_layer()
        else:
            print("Error: Could not get HWND in showEvent.")

    def set_window_layer(self):
        # --- Advanced Window Layering using pywin32 ---
        try:
            print(f"Attempting to set styles for HWND: {self.hwnd}")
            # Get current extended style
            style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
            # Add WS_EX_LAYERED for transparency effects
            # Add WS_EX_TRANSPARENT to make it click-through
            style = style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, style)

            # Set position to be topmost - above all other windows
            win32gui.SetWindowPos(self.hwnd,
                                  win32con.HWND_TOPMOST,  # Changed from NOTOPMOST to TOPMOST
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

            print("Applied WS_EX_LAYERED | WS_EX_TRANSPARENT and set HWND_TOPMOST.")

        except Exception as e:
            print(f"Error applying window styles/position via pywin32: {e}")

    def closeEvent(self, event):
        # Clean stop monitoring timer
        if self.monitoring_timer:
            self.monitoring_timer.stop()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    overlay = MatrixWindow()
    overlay.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 