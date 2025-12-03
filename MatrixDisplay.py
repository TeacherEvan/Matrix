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
    """Represents a fading trail left behind a falling Matrix symbol.
    
    Trails are created as symbols fall and gradually fade out over time,
    creating the characteristic Matrix "rain" effect.
    
    Attributes:
        symbol: The character being displayed.
        pos: QPointF position of the trail.
        color: Base color of the trail.
        start_time: Timestamp when the trail was created.
        duration: How long the trail remains visible in seconds.
    """
    
    def __init__(self, symbol, pos_x, pos_y, color, start_time, duration=60.0):
        """Initialize a new symbol trail.
        
        Args:
            symbol: The Matrix symbol character to display.
            pos_x: X coordinate of the trail position.
            pos_y: Y coordinate of the trail position.
            color: Base color of the trail.
            start_time: Timestamp when the trail was created.
            duration: How long the trail remains visible (default: 60 seconds).
        """
        self.symbol = symbol
        self.pos = QPointF(pos_x, pos_y)
        self.color = color
        self.start_time = start_time
        self.duration = duration
        
    def is_active(self, current_time):
        """Check if the trail is still active.
        
        Args:
            current_time: Current timestamp to compare against.
            
        Returns:
            bool: True if trail should still be visible.
        """
        return current_time - self.start_time < self.duration
        
    def get_fade_factor(self, current_time):
        """Get fade factor from 1.0 (fresh) to 0.0 (expired).
        
        Args:
            current_time: Current timestamp.
            
        Returns:
            float: Fade factor between 0.0 and 1.0.
        """
        elapsed = current_time - self.start_time
        return max(0.0, 1.0 - elapsed / self.duration)
        
    def draw(self, painter, current_time):
        """Draw the symbol trail with fading effect.
        
        Args:
            painter: QPainter object for rendering.
            current_time: Current timestamp for fade calculation.
        """
        if not self.is_active(current_time):
            return
            
        fade_factor = self.get_fade_factor(current_time)
        
        # Adjust alpha based on fade factor with increased transparency (additional 20% reduction)
        trail_alpha = int(self.color.alpha() * fade_factor * 0.56)  # 0.7 * 0.8 = 0.56 (30% + 20% more transparent)
        trail_color = QColor(self.color)
        trail_color.setAlpha(trail_alpha)
        
        painter.setPen(trail_color)
        painter.setFont(painter.font())  # Use current font
        painter.drawText(self.pos, self.symbol)


class ExplosionParticle:
    """Represents a single particle in an explosion that can interact with symbols.
    
    Particles are created when a symbol explodes and travel outward from the
    explosion center. They can collide with other symbols and affect their movement.
    
    Attributes:
        symbol: The character displayed by this particle.
        pos: Current QPointF position.
        direction: Tuple (dx, dy) representing normalized direction vector.
        speed: Movement speed of the particle.
        color: Particle color.
        size: Visual size of the particle.
        active: Whether the particle is still active.
        hit_force: Force applied to symbols on collision.
    """
    
    def __init__(self, symbol, x_pos, y_pos, direction, speed, color, size):
        """Initialize a new explosion particle.
        
        Args:
            symbol: The character to display.
            x_pos: Initial X coordinate.
            y_pos: Initial Y coordinate.
            direction: Tuple (dx, dy) normalized direction vector.
            speed: Movement speed.
            color: Particle color.
            size: Visual size of the particle.
        """
        self.symbol = symbol
        self.pos = QPointF(x_pos, y_pos)
        self.direction = direction
        self.speed = speed
        self.color = color
        self.size = size * 2.0  # Double the size of explosion particles
        self.last_pos = QPointF(x_pos, y_pos)
        self.active = True
        self.hit_force = speed * 0.2  # Force applied to symbols when hit
        
    def update(self, elapsed_time):
        """Update position based on direction and speed.
        
        Args:
            elapsed_time: Time elapsed since last update in seconds.
        """
        self.last_pos = QPointF(self.pos)
        # Move according to direction and speed (reduced by 50%)
        velocity_x = self.direction[0] * self.speed * elapsed_time * 0.5
        velocity_y = self.direction[1] * self.speed * elapsed_time * 0.5
        self.pos.setX(self.pos.x() + velocity_x)
        self.pos.setY(self.pos.y() + velocity_y)
        
    def check_collision(self, target_symbol):
        """Check if this particle collides with a symbol.
        
        Args:
            target_symbol: The symbol to check collision against.
            
        Returns:
            bool: True if collision detected, False otherwise.
        """
        # Optimized: use squared distance to avoid expensive sqrt()
        collision_distance = self.size + target_symbol.size
        collision_distance_squared = collision_distance * collision_distance
        distance_x = self.pos.x() - target_symbol.pos.x()
        distance_y = self.pos.y() - target_symbol.pos.y()
        distance_squared = distance_x * distance_x + distance_y * distance_y
        
        return distance_squared < collision_distance_squared
    
    def affect_symbol(self, target_symbol):
        """Apply physics effect to a symbol when hit by this particle.
        
        Args:
            target_symbol: The symbol to apply physics effects to.
        """
        # Calculate impulse direction (from particle to symbol)
        direction_x = target_symbol.pos.x() - self.pos.x()
        direction_y = target_symbol.pos.y() - self.pos.y()
        
        # Optimized: avoid sqrt for normalization when possible
        direction_length_squared = direction_x * direction_x + direction_y * direction_y
        if direction_length_squared > 0.001:  # Avoid division by very small numbers
            direction_length = math.sqrt(direction_length_squared)
            direction_x /= direction_length
            direction_y /= direction_length
        else:
            # Use default direction if symbols are too close
            direction_x, direction_y = 1.0, 0.0
            
        # Apply impulse to symbol velocity - random drift plus directed force
        target_symbol.drift_x = direction_x * self.hit_force + random.uniform(-1, 1)
        target_symbol.drift_y = direction_y * self.hit_force + random.uniform(-1, 1)
        
        # Flag symbol as affected
        target_symbol.affected_by_explosion = True
        
        # Change symbol color to blood red when affected
        target_symbol.color = QColor(200, 0, 0, 220)  # Blood red with high alpha


class CodeEffect:
    """Represents a special visual effect when symbols explode.
    
    Creates an explosion animation with multiple particles radiating outward.
    Particles can interact with other falling symbols, affecting their movement
    and changing their colors.
    
    Note:
        The color parameter is stored but the actual particle color is always
        blood red (QColor(200, 0, 0, 220)) for visual consistency.
    
    Attributes:
        x_pos: X coordinate of explosion center.
        y_pos: Y coordinate of explosion center.
        color: Base color parameter (stored but particles use blood red).
        start_time: Timestamp when the effect started.
        duration: How long the effect lasts in seconds.
        size_factor: Multiplier for explosion size (0.5 to 2.5).
        particles: List of ExplosionParticle objects.
        effect_color: Actual color used for particles (blood red).
    """
    
    # Class-level symbol pool for better performance
    SYMBOL_POOL = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
    SYMBOL_POOL_LEN = len(SYMBOL_POOL)
    
    def __init__(self, x_pos, y_pos, color, start_time, size_factor=1.0):
        """Initialize a new explosion effect.
        
        Args:
            x_pos: X coordinate of explosion center.
            y_pos: Y coordinate of explosion center.
            color: Base color parameter (stored but particles use blood red).
            start_time: Timestamp when the effect started.
            size_factor: Size multiplier for the explosion (default: 1.0).
        """
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.color = color
        self.start_time = start_time
        self.duration = 4.8  # Animation duration in seconds
        self.size_factor = size_factor
        
        # Base radius varies from 50 to 150 (randomized for each explosion)
        self.radius = 75 * self.size_factor
        
        self.particles = []               # Explosion particles
        self.symbol_trails = []           # Trails left by particles
        self.last_update_time = start_time
        
        # Generate effect symbols (more symbols for richer effect)
        particle_count = int(20 * size_factor)  # Scale number of particles with size
        
        # Always use blood red for explosion particles
        blood_red = QColor(200, 0, 0, 220)
        self.effect_color = blood_red
        
        # Create particle objects
        for particle_index in range(particle_count):
            # Random symbol from cached pool
            particle_symbol = self.SYMBOL_POOL[random.randrange(self.SYMBOL_POOL_LEN)]
            
            # Calculate direction angles with variation
            angle = 2 * math.pi * particle_index / particle_count + random.uniform(-0.2, 0.2)
            direction = (math.cos(angle), math.sin(angle))
            
            # Random speeds (vary based on size factor) - reduced by 50%
            particle_speed = random.uniform(10, 25) * math.sqrt(size_factor)  # Reduced from 20-50 to 10-25
            
            # Create particle with randomized size
            particle_size = random.uniform(2, 5) * size_factor
            
            # Add particle
            self.particles.append(
                ExplosionParticle(
                    particle_symbol, x_pos, y_pos, direction, particle_speed, 
                    self.effect_color, particle_size
                )
            )
        
    def is_active(self, current_time):
        """Check if the animation is still active.
        
        Args:
            current_time: Current timestamp.
            
        Returns:
            bool: True if the effect is still animating.
        """
        return current_time - self.start_time < self.duration
        
    def get_progress(self, current_time):
        """Get animation progress from 0.0 to 1.0.
        
        Args:
            current_time: Current timestamp.
            
        Returns:
            float: Animation progress between 0.0 (start) and 1.0 (end).
        """
        elapsed = current_time - self.start_time
        return min(1.0, elapsed / self.duration)
        
    def update_positions(self, current_time, active_symbols):
        """Update particle positions, check for collisions with symbols, and return any new trails.
        
        Args:
            current_time: Current timestamp in seconds.
            active_symbols: List of MatrixSymbol objects to check for collisions.
            
        Returns:
            List of new SymbolTrail objects created during this update.
        """
        if not self.is_active(current_time):
            return []
            
        elapsed_since_last = current_time - self.last_update_time
        self.last_update_time = current_time
        
        animation_progress = self.get_progress(current_time)
        new_trails = []
        
        # Update particle positions and check for collisions
        for particle in self.particles:
            if not particle.active:
                continue
                
            # Update particle position
            particle.update(elapsed_since_last)
            
            # Check for collisions with symbols (optimized)
            for symbol_index, target_symbol in enumerate(active_symbols):
                if target_symbol is not None and target_symbol.is_active:
                    if particle.check_collision(target_symbol):
                        # Apply physics effect to symbol
                        particle.affect_symbol(target_symbol)
                        # Deactivate particle after first collision for performance
                        particle.active = False
                        break
            
            # Create occasional trails
            if random.random() < 0.4 and animation_progress > 0.1:
                # Always use blood red for trails
                blood_red = QColor(200, 0, 0, 180)
                
                # Create a fading trail
                new_trails.append(
                    SymbolTrail(
                        particle.symbol,
                        particle.pos.x(), particle.pos.y(),
                        blood_red, 
                        current_time,
                        duration=1.2  # Short duration doubled (from 0.6 to 1.2)
                    )
                )
            
        return new_trails
        
    def draw(self, painter, current_time):
        """Draw the explosion effect with all active particles.
        
        Args:
            painter: QPainter object for rendering.
            current_time: Current timestamp for animation progress.
        """
        if not self.is_active(current_time):
            return
            
        animation_progress = self.get_progress(current_time)
        
        # Fade out particles as the animation progresses
        particle_alpha = int(255 * (1.0 - animation_progress * 0.7))
        # Always use blood red for particles
        particle_color = QColor(200, 0, 0, particle_alpha)
        
        painter.setPen(particle_color)
        
        # Draw each particle
        for particle in self.particles:
            if particle.active:
                # Scale font for particle size
                particle_font = QFont(painter.font())
                particle_font.setPointSizeF(particle.size * 2.5)  # Already increased by 1.25x previously
                painter.setFont(particle_font)
                
                # Draw the particle
                painter.drawText(particle.pos, particle.symbol)


class MatrixSymbol:
    """Represents a falling Matrix symbol in the digital rain effect.
    
    Each symbol falls down the screen at a random speed, occasionally changing
    its character, and leaving trails behind. Symbols can be affected by
    explosion effects and respond with physics-based movement.
    
    Attributes:
        pos: Current QPointF position.
        last_pos: Previous position for trail generation.
        speed: Falling speed of the symbol.
        color: Current display color.
        size: Font size for rendering.
        is_active: Whether the symbol is currently active.
        affected_by_explosion: Whether physics drift should be applied.
    """
    
    # Class-level symbol pool for better performance
    SYMBOL_POOL = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
    SYMBOL_POOL_LEN = len(SYMBOL_POOL)
    
    def __init__(self, x_position, y_position, fall_speed, symbol_color, font_size):
        """Initialize a new falling Matrix symbol.
        
        Args:
            x_position: Initial X coordinate.
            y_position: Initial Y coordinate.
            fall_speed: Speed at which the symbol falls.
            symbol_color: Color of the symbol (will be copied, not modified).
            font_size: Size for rendering the symbol.
        """
        self.pos = QPointF(x_position, y_position)
        self.last_pos = QPointF(x_position, y_position)  # Track previous position for trail generation
        self.speed = fall_speed
        
        # Create a copy of the color to avoid modifying the original
        adjusted_color = QColor(symbol_color)
        # Increase transparency by 40% in total (30% + additional 10%) by reducing alpha
        original_alpha = adjusted_color.alpha()
        reduced_alpha = int(original_alpha * 0.6)  # 40% more transparent
        adjusted_color.setAlpha(reduced_alpha)
        self.color = adjusted_color
        
        self.size = font_size * 1.0  # Original size (changed from 0.8 to 1.0)
        self.is_active = True
        self.change_counter = 0  # Counter for changing the symbol character
        self.trail_counter = 0   # Counter to control trail generation frequency
        
        # Square properties for the flashing effect
        self.has_square = True
        self.square_color = QColor(255, 255, 255, 120)  # White semi-transparent
        self.square_flash_timer = 0
        self.square_visible = True
        
        # Physics properties
        self.drift_x = 0                # Horizontal drift (added by explosions)
        self.drift_y = 0                # Vertical drift (added by explosions)
        self.affected_by_explosion = False  # Flag to track if affected
        self.drift_damping = 0.95       # Damping factor to gradually reduce drift
        
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
    """Main application window for the Matrix digital rain display.
    
    Creates a transparent overlay that displays falling Matrix-style symbols
    with explosion effects, trails, and physics-based interactions. The display
    automatically suspends when CPU usage is high or fullscreen apps are detected.
    
    Attributes:
        symbols: List of MatrixSymbol objects.
        code_effects: List of active explosion effects.
        symbol_trails: List of fading trail effects.
        max_symbols: Maximum number of simultaneous symbols.
        is_suspended: Whether the display is currently suspended.
    """
    
    def __init__(self):
        """Initialize the Matrix display window and all subsystems."""
        super().__init__()
        
        # --- Performance Optimizations ---
        # Pre-defined symbol pool for better performance
        self.symbol_pool = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
        self.symbol_pool_len = len(self.symbol_pool)
        
        # Pre-calculated colors for better performance
        self._blood_red_cache = QColor(200, 0, 0, 220)
        self._trail_alpha_cache = {}  # Cache for trail alpha calculations
        
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
        self.max_symbols = 600  # Maximum simultaneous symbols (reduced by 50% from 1200)
        self.symbol_count = 0   # Active symbol count for quick access
        # ---------------------------

        # --- Code Effect Animation State ---
        self.code_effects = []   # List of active explosion effects
        self.symbol_trails = []  # List of fading trail effects
        # ------------------------------
        
        # --- Symbol Generation Timing ---
        self.last_symbol_add_time = time.time()
        self.symbol_add_interval = 2.0  # Add a new symbol every 2 seconds
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
        """Initialize the user interface and window properties.
        
        Sets up window flags for transparency and click-through behavior,
        configures dimensions based on screen size, and initializes the font.
        """
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
        background_opacity = int(180 * 0.6)  # 40% more transparent
        self.setStyleSheet(f"background-color: rgba(0, 0, 0, {background_opacity});")

        # --- Positioning and Sizing ---
        primary_screen = QApplication.primaryScreen()
        if not primary_screen:
            print("Error: Could not get primary screen.")
            sys.exit(1)
            
        screen_geometry = primary_screen.geometry()
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
        """Set up the monitoring timer to check CPU usage and fullscreen apps.
        
        Initializes a timer that triggers system state checks every 2 seconds.
        """
        self.monitoring_timer = QTimer(self)
        self.monitoring_timer.timeout.connect(self.check_system_state)
        self.monitoring_timer.start(2000)  # Check every 2 seconds
        
    def is_fullscreen_app_running(self):
        """Check if any fullscreen application is currently running.
        
        Returns:
            bool: True if a fullscreen app is detected, False otherwise.
        """
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
                    window_style = win32gui.GetWindowLong(foreground_window, win32con.GWL_STYLE)
                    
                    # Many games and fullscreen apps don't have these borders/decorations
                    if (window_style & win32con.WS_CAPTION) == 0 or (window_style & win32con.WS_THICKFRAME) == 0:
                        return True
                        
                    # Check window title for keywords that might indicate games
                    window_title = win32gui.GetWindowText(foreground_window).lower()
                    game_keywords = ['game', 'play', 'factorio', 'minecraft', 'steam', 'directx', 'fullscreen']
                    for keyword in game_keywords:
                        if keyword in window_title:
                            return True
        except Exception as detection_error:
            print(f"Error checking fullscreen apps: {detection_error}")
            
        return False
        
    def check_system_state(self):
        """Check CPU usage and running apps, suspend display if necessary.
        
        Monitors system resources and suspends the Matrix display when:
        - CPU usage exceeds 75%
        - A fullscreen application is detected
        """
        current_time = time.time()
        
        # Only do full check periodically to avoid performance impact
        if current_time - self.last_check_time < self.fullscreen_check_interval:
            # Do a quick CPU check more frequently
            cpu_usage_percent = psutil.cpu_percent(interval=None)
            if cpu_usage_percent > 75 and not self.is_suspended:
                print(f"Suspending Matrix display due to high CPU usage: {cpu_usage_percent}%")
                self.suspend_matrix()
            elif cpu_usage_percent <= 75 and self.is_suspended and not self.is_fullscreen_app_running():
                print(f"Resuming Matrix display, CPU usage normal: {cpu_usage_percent}%")
                self.resume_matrix()
            return
            
        self.last_check_time = current_time
        
        # Check CPU usage
        cpu_usage_percent = psutil.cpu_percent(interval=None)
        print(f"Current CPU usage: {cpu_usage_percent}%")
        
        # Check for fullscreen applications
        fullscreen_detected = self.is_fullscreen_app_running()
        
        if (cpu_usage_percent > 75 or fullscreen_detected) and not self.is_suspended:
            suspension_reason = "high CPU usage" if cpu_usage_percent > 75 else "fullscreen application"
            print(f"Suspending Matrix display due to {suspension_reason}")
            self.suspend_matrix()
        elif cpu_usage_percent <= 75 and not fullscreen_detected and self.is_suspended:
            print("Resuming Matrix display, system state normal")
            self.resume_matrix()
    
    def suspend_matrix(self):
        """Suspend the Matrix display and hide the window.
        
        Stops the animation timer, resets display state, and hides the overlay.
        """
        if not self.is_suspended:
            self.symbol_timer.stop()
            self.is_suspended = True
            
            # Reset all display elements
            self.reset_display_state()
            
            self.hide()  # Hide the window
    
    def resume_matrix(self):
        """Resume the Matrix display and show the window.
        
        Restarts the animation timer and brings the overlay back to the top.
        """
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
        """Reset all display elements to their initial state.
        
        Clears all active symbols, explosion effects, and trails,
        then resets timing counters.
        """
        # Clear all active symbols
        for slot_index in range(self.max_symbols):
            if self.symbols[slot_index] is not None and self.symbols[slot_index].is_active:
                self.symbols[slot_index].is_active = False
        
        # Reset symbol count
        self.symbol_count = 0
        
        # Clear all explosion effects
        self.code_effects.clear()
        
        # Clear all symbol trails
        self.symbol_trails.clear()
        
        # Reset timing
        self.last_symbol_add_time = time.time()
        self.last_frame_time = time.time()

    def add_symbol(self, x_position=None):
        """Adds a new Matrix symbol to the first available slot.
        
        Args:
            x_position: Optional x coordinate for the new symbol.
                       If None, a random position is chosen.
        """
        if self.symbol_count >= self.max_symbols:
            return

        # Find first available slot
        for slot_index in range(self.max_symbols):
            if self.symbols[slot_index] is None or not self.symbols[slot_index].is_active:
                spawn_x = x_position if x_position is not None else random.uniform(0, self.screen_width)
                spawn_y = random.uniform(-20, 0)  # Start just above the view
                fall_speed = random.uniform(1, 5)  # Base speed restored to original range (was 0.5-2.5, now doubled back)
                symbol_color = random.choice(self.symbol_colors)
                # Adjust alpha based on speed (faster = brighter)
                symbol_color.setAlpha(int(max(100, min(255, symbol_color.alpha() + fall_speed * 10))))
                font_size = random.uniform(8, 12)  # Font size variation increased by 1.25x (from 6.4-9.6 to 8-12)

                self.symbols[slot_index] = MatrixSymbol(spawn_x, spawn_y, fall_speed, symbol_color, font_size)
                self.symbol_count += 1
                self._total_symbols_created += 1
                return
    
    def remove_symbol(self, symbol_index):
        """Mark a symbol as inactive and decrement the active count.
        
        Args:
            symbol_index: Index of the symbol to remove.
        """
        if 0 <= symbol_index < self.max_symbols and self.symbols[symbol_index] is not None:
            self.symbols[symbol_index].is_active = False
            self.symbol_count -= 1

    def setup_timer(self):
        """Initialize the animation timer for symbol updates."""
        self.symbol_timer = QTimer(self)
        self.symbol_timer.timeout.connect(self.update_symbols)
        self.symbol_timer.start(50)  # Update at ~20fps (more Matrix-like stuttery feeling)

    def update_symbols(self):
        """Update symbol positions, handle animations, and manage explosion effects.
        
        This method is called every frame (~20fps) and handles:
        - Symbol movement and physics
        - Trail generation
        - Explosion triggering and particle effects
        - Cleanup of expired effects
        """
        current_time = time.time()
        
        frame_duration = current_time - self.last_frame_time
        self.frame_times.append(frame_duration)
        self.last_frame_time = current_time
        
        # Calculate average frame time and log if it's high
        if len(self.frame_times) >= 60:
            average_frame_time = sum(self.frame_times) / len(self.frame_times)
            if average_frame_time > 0.05:  # More than 50ms (less than 20fps)
                print(f"Performance Warning: Avg frame time {average_frame_time*1000:.1f}ms | "
                      f"Symbols: {self.symbol_count}/{self.max_symbols} | "
                      f"Trails: {len(self.symbol_trails)} | "
                      f"Effects: {len(self.code_effects)}")
            elif len(self.frame_times) == 60:  # Log performance stats periodically
                print(f"Performance: {average_frame_time*1000:.1f}ms avg | "
                      f"Symbols: {self.symbol_count} | Trails: {len(self.symbol_trails)}")
        
        display_height = self.overlay_height
        
        # Symbol generation every 2 seconds
        if self.symbol_count < self.max_symbols and current_time - self.last_symbol_add_time >= self.symbol_add_interval:
            self.add_symbol()
            self.last_symbol_add_time = current_time

        # --- Clean up expired code effects and trails ---
        effect_index = 0
        while effect_index < len(self.code_effects):
            # Update effect positions and collect any new trails
            new_trails = self.code_effects[effect_index].update_positions(current_time, self.symbols)
            self.symbol_trails.extend(new_trails)
            
            if not self.code_effects[effect_index].is_active(current_time):
                self.code_effects.pop(effect_index)
            else:
                effect_index += 1
                
        # --- Clean up expired symbol trails (optimized batch cleanup) ---
        if len(self.symbol_trails) > 100:  # Only clean up when we have many trails
            # Use list comprehension for faster cleanup
            self.symbol_trails = [trail for trail in self.symbol_trails if trail.is_active(current_time)]
        else:
            # Regular cleanup for smaller lists
            trail_index = 0
            while trail_index < len(self.symbol_trails):
                if not self.symbol_trails[trail_index].is_active(current_time):
                    self.symbol_trails.pop(trail_index)
                else:
                    trail_index += 1

        # --- Update Symbol Positions & Check for Random Explosions (optimized) ---
        symbols_to_remove = []  # Batch removal for better performance
        
        for symbol_index, current_symbol in enumerate(self.symbols):
            if current_symbol is None or not current_symbol.is_active:
                continue
                
            # Store last position before updating
            current_symbol.last_pos = QPointF(current_symbol.pos)
            
            # Update square flashing
            current_symbol.square_flash_timer += 1
            if current_symbol.square_flash_timer >= 5:  # Flash every 250ms (at 20fps)
                current_symbol.square_flash_timer = 0
                current_symbol.square_visible = not current_symbol.square_visible
            
            # Apply physics drift if affected by an explosion
            if current_symbol.affected_by_explosion:
                # Apply drift to position
                current_symbol.pos.setX(current_symbol.pos.x() + current_symbol.drift_x)
                current_symbol.pos.setY(current_symbol.pos.y() + current_symbol.drift_y)
                
                # Dampen drift for next frame
                current_symbol.drift_x *= current_symbol.drift_damping
                current_symbol.drift_y *= current_symbol.drift_damping
                
                # If drift becomes very small, reset affected flag
                if abs(current_symbol.drift_x) < 0.1 and abs(current_symbol.drift_y) < 0.1:
                    current_symbol.affected_by_explosion = False
                    current_symbol.drift_x = 0
                    current_symbol.drift_y = 0
            else:
                # Normal falling motion if not affected by explosion
                current_symbol.pos.setY(current_symbol.pos.y() + current_symbol.speed * 2)  # Doubled falling speed
            
            # Occasionally change the symbol character (Matrix-like effect)
            current_symbol.change_counter += 1
            if current_symbol.change_counter >= random.randint(5, 20):  # Change frequency varies
                current_symbol.change_counter = 0
                # Use cached symbol pool for better performance
                current_symbol.symbol = self.symbol_pool[random.randrange(self.symbol_pool_len)]
            
            # Create trails behind falling symbols
            current_symbol.trail_counter += 1
            if current_symbol.trail_counter >= 2:  # Create trail frequently for Matrix effect
                current_symbol.trail_counter = 0
                
                # Only create trails if there has been movement
                if abs(current_symbol.last_pos.y() - current_symbol.pos.y()) > 0.5 or abs(current_symbol.last_pos.x() - current_symbol.pos.x()) > 0.5:
                    # Create a trail with slightly transparent version of symbol color
                    trail_color = QColor(current_symbol.color)
                    # Set alpha to be less than the symbol
                    trail_color.setAlpha(int(current_symbol.color.alpha() * 0.6))
                    
                    # Add trail at the last position with optimized 30-second duration
                    self.symbol_trails.append(
                        SymbolTrail(
                            current_symbol.symbol,
                            current_symbol.last_pos.x(), current_symbol.last_pos.y(),
                            trail_color, current_time,
                            duration=30.0  # Reduced from 60 to 30 seconds for better performance
                        )
                    )
                    self._total_trails_created += 1
            
            # Check if symbol has been falling too long (based on randomized max_fall_time)
            if current_time - current_symbol.birth_time > current_symbol.max_fall_time:
                self.remove_symbol(symbol_index)
                continue
            
            # Random explosion with 0.0003% chance per symbol (further reduced for performance)
            if random.random() < 0.000003:  # 0.0003% chance (reduced from 0.0005% for better performance)
                # Mark this symbol for explosion (will happen in 3 seconds)
                current_symbol.rigged_to_explode = True
                current_symbol.explosion_time = current_time + 3.0
                continue

            # Check if symbol is rigged to explode and it's time
            if hasattr(current_symbol, 'rigged_to_explode') and current_symbol.rigged_to_explode:
                # If it's time to explode
                if hasattr(current_symbol, 'explosion_time') and current_time >= current_symbol.explosion_time:
                    # Create a code effect at the current position
                    # Use cached blood red color for explosion
                    
                    # Randomize explosion size between 0.5 and 2.5 times base size
                    explosion_size_factor = random.uniform(0.5, 2.5)
                    
                    # Add code effect with current time as start time
                    self.code_effects.append(
                        CodeEffect(current_symbol.pos.x(), current_symbol.pos.y(), self._blood_red_cache, current_time, explosion_size_factor)
                    )
                    
                    # Remove symbol after it explodes
                    self.remove_symbol(symbol_index)
                    continue
            
            # Remove symbol if it goes outside the widget bounds
            if (current_symbol.pos.y() > display_height + 20 or 
                current_symbol.pos.x() < -20 or 
                current_symbol.pos.x() > self.screen_width + 20):
                self.remove_symbol(symbol_index)

        # Trigger repaint
        self.update()

    def paintEvent(self, event):
        """Handle the paint event for rendering the Matrix display.
        
        Args:
            event: The paint event object.
        """
        current_time = time.time()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set font for all Matrix symbols
        font = self.matrix_font
        painter.setFont(font)

        display_rect = self.rect()
        display_height = display_rect.height()
        
        # --- Draw Symbol Trails (draw first so they appear behind symbols) ---
        for trail in self.symbol_trails:
            trail.draw(painter, current_time)
        
        # --- Draw Code Effects ---
        for effect in self.code_effects:
            effect.draw(painter, current_time)
        
        # --- Draw Matrix Symbols (optimized) ---
        base_font = QFont(font)
        cached_font_size = -1  # Track current font size to avoid redundant operations
        
        for matrix_symbol in self.symbols:
            if matrix_symbol is None or not matrix_symbol.is_active:
                continue
            
            # Draw flashing square first (if visible)
            if hasattr(matrix_symbol, 'square_visible') and matrix_symbol.square_visible and hasattr(matrix_symbol, 'has_square') and matrix_symbol.has_square:
                square_size = matrix_symbol.size
                square_rect = QRect(
                    int(matrix_symbol.pos.x()), 
                    int(matrix_symbol.pos.y() - square_size/2),  # Slightly above symbol
                    int(square_size), 
                    int(square_size)
                )
                painter.fillRect(square_rect, matrix_symbol.square_color)
            
            # Calculate target font size
            target_font_size = matrix_symbol.size
            
            # Check if symbol is rigged to explode
            if hasattr(matrix_symbol, 'rigged_to_explode') and matrix_symbol.rigged_to_explode:
                # Pulsating white effect for symbols about to explode
                pulse_intensity = 0.5 + 0.5 * math.sin(current_time * 5)  # 0.5 to 1.0 pulsating
                pulsating_color = QColor(255, 255, 255, int(255 * pulse_intensity))
                painter.setPen(pulsating_color)
                
                # Increase size for emphasis (pulsating size)
                size_multiplier = 1.0 + 0.5 * pulse_intensity
                target_font_size = matrix_symbol.size * size_multiplier
            else:
                # Normal symbol
                painter.setPen(matrix_symbol.color)
            
            # Only update font if size changed (optimization)
            if cached_font_size != target_font_size:
                base_font.setPointSizeF(target_font_size)
                painter.setFont(base_font)
                cached_font_size = target_font_size
            
            # Draw the symbol
            painter.drawText(matrix_symbol.pos, matrix_symbol.symbol)

    def showEvent(self, event):
        """Handle window show event for initializing window layer settings.
        
        Args:
            event: The show event object.
        """
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
        """Configure advanced window layering using pywin32.
        
        Sets up the window to be:
        - Transparent (WS_EX_LAYERED)
        - Click-through (WS_EX_TRANSPARENT)
        - Always on top (HWND_TOPMOST)
        """
        try:
            print(f"Attempting to set styles for HWND: {self.hwnd}")
            # Get current extended style
            window_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
            # Add WS_EX_LAYERED for transparency effects
            # Add WS_EX_TRANSPARENT to make it click-through
            window_style = window_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, window_style)

            # Set position to be topmost - above all other windows
            win32gui.SetWindowPos(self.hwnd,
                                  win32con.HWND_TOPMOST,  # Changed from NOTOPMOST to TOPMOST
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

            print("Applied WS_EX_LAYERED | WS_EX_TRANSPARENT and set HWND_TOPMOST.")

        except Exception as error:
            print(f"Error applying window styles/position via pywin32: {error}")

    def closeEvent(self, event):
        """Handle window close event for cleanup.
        
        Args:
            event: The close event object.
        """
        if self.monitoring_timer:
            self.monitoring_timer.stop()
        super().closeEvent(event)


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    overlay = MatrixWindow()
    overlay.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()