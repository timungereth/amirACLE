import sys
import ctypes
from ctypes import wintypes, Structure, POINTER, c_int
import win32gui
import win32con
import win32api
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                            QWidget, QPushButton, QHBoxLayout, QFrame,
                            QSystemTrayIcon, QMenu, QAction, QToolTip, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, QObject, QPoint, pyqtSignal
from PyQt5.QtGui import QIcon, QCursor, QFont
import keyboard
import logging
import os
import time
import threading
from pynput import mouse
from PyQt5.QtWidgets import QGraphicsOpacityEffect  


# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Suppress Qt warnings
os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts.systemfont=false"

# Windows structures for SendInput
WHEEL_DELTA = 120

# Long press duration in seconds
LONG_PRESS_DURATION = 0.5


class Communicate(QObject):
    startStopSignal = pyqtSignal(bool)

class TitleBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        """
        self.title_label = QLabel("Scroll Control for AMIR (Esc to quit)")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        """
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QLabel {
                color: white;
                font-family: Arial;
                font-size: 8px;
                padding: 5px;
            }
        """)

class MouseLongPressHandler:
    def __init__(self, communicate):
        self.communicate = communicate
        self.listener = mouse.Listener(
            on_click=self.on_click,
            on_move=self.on_move
        )
        self.listener.start()
        self.pressed = False
        self.current_pos = (0, 0)

    def on_move(self, x, y):
        self.current_pos = (x, y)
        self.communicate.startStopSignal.emit(False)

    def on_click(self, x, y, button, pressed):
        if button == mouse.Button.left:
            if pressed and not self.pressed:
                self.pressed = True
                self.communicate.startStopSignal.emit(True)
            elif not pressed and self.pressed:
                self.communicate.startStopSignal.emit(False)
                self.pressed = False

    def stop(self):
        self.listener.stop()

    def get_current_pos(self):
        return self.current_pos

class FloatingControlWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logging.info("Initializing FloatingControlWindow")
        self.scroll_amount = WHEEL_DELTA
        self.target_window = None
        self.target_window_title = ""
        self.buttons = []  

        self.activate_right_click = False  
        self.click_check_timer = QTimer()  
        self.click_check_timer.timeout.connect(self.check_for_click)
        self.click_check_timer.start(10) 

        self.initUI()
        self.setupSystemTray()
        self.setupQuitKey()

        self.communicate = Communicate()
        self.communicate.startStopSignal.connect(self.trigger_timer)
        
        self.long_press_handler = MouseLongPressHandler(self.communicate)
        
        # self.update_timer = QTimer()
        # self.update_timer.timeout.connect(self.update_window_position)
        
        self.summon_timer = QTimer()
        self.summon_timer.timeout.connect(self.capture_target_window)
        self.summon_timer.setSingleShot(True)
        
        self.setWindowOpacity(0.7)

    def get_display_scaling(self):
        """Get the scaling factor for the current display"""
        try:
            cursor_pos = win32gui.GetCursorPos()
            monitor = win32api.MonitorFromPoint(cursor_pos)
            info = win32api.GetMonitorInfo(monitor)
            
            # Get the monitor's physical and logical dimensions
            physical_width = abs(info['Monitor'][2] - info['Monitor'][0])
            logical_width = abs(info['Work'][2] - info['Work'][0])

            
            # Calculate scaling factor

            scaling_factor = logical_width / 1920
            return scaling_factor
        except Exception:
            print('error in get_display_scaling')
            return 1.0  # Default to no scaling if there's an error

    def create_circular_button(self, text, special_button=None):
        scaling = self.get_display_scaling()
        #print('For creating buttons, scaling:', scaling)  
        
        # Scale base sizes
        base_button_size = 80
        base_font_size = 16
        
        # Apply scaling
        button_size = int(base_button_size * scaling)
        font_size = int(base_font_size * scaling)
        
        button = QPushButton(text)
        button.setFixedSize(button_size, button_size)
        button.setFont(QFont("Arial", font_size))
        
        # Adjust border radius to maintain circular shape
        border_radius = button_size // 2
        
        # Set button style based on type
        if special_button == "left":
            button_style = f"""
                QPushButton {{
                    background-color: #9A2B2B;
                    color: white;
                    border: none;
                    border-radius: {border_radius}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #A92E2E;
                }}
                QPushButton:pressed {{
                    background-color: #6F1E1E;
                }}
                QPushButton:disabled {{
                    background-color: #666666;
                    color: #CCCCCC;
                }}
            """
        elif special_button == "right":
            button_style = f"""
                QPushButton {{
                    background-color: #2B9A2B;
                    color: white;
                    border: none;
                    border-radius: {border_radius}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #2EA92E;
                }}
                QPushButton:pressed {{
                    background-color: #1E6F1E;
                }}
            """
        else:
            button_style = f"""
                QPushButton {{
                    background-color: #2B579A;
                    color: white;
                    border: none;
                    border-radius: {border_radius}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #2E5FA9;
                }}
                QPushButton:pressed {{
                    background-color: #1E3F6F;
                }}
            """
        button.setStyleSheet(button_style)
        
        return button


    def update_button_radius(self, button, new_radius):
        """Update only the border radius while preserving all other styles"""
        current_style = button.styleSheet()
        
        
        # Replace existing border-radius value
        import re
        updated_style = re.sub(
            r'border-radius:\s*\d+px',
            f'border-radius: {new_radius}px',
            current_style
        )
        
        
        button.setStyleSheet(updated_style)

    # def update_window_position(self):
    #     try:
    #         cursor_pos = QCursor.pos()
    #         print('For updating window pos, cursor_pos:', cursor_pos)
    #         window_size = self.size()
            
    #         # Calculate position to center window around cursor
    #         new_x = cursor_pos.x() - (window_size.width() // 2)
    #         new_y = cursor_pos.y() - (window_size.height() // 2)
            
    #         # Ensure window stays within screen boundaries
    #         screen = QApplication.primaryScreen().geometry()
            
    #         #Adjust x position if window would go off screen
    #         if new_x < 0:
    #             new_x = 0
    #         elif new_x + window_size.width() > screen.width():
    #             new_x = screen.width() - window_size.width()
            
    #         # Adjust y position if window would go off screen
    #         if new_y < 0:
    #             new_y = 0
    #         elif new_y + window_size.height() > screen.height():
    #             new_y = screen.height() - window_size.height()
            
    #         self.move(new_x, new_y)
            
    #     except Exception as e:
    #         logging.error(f"Error updating window position: {str(e)}")

    def trigger_timer(self, start):
        if not start:
            self.summon_timer.stop()
        else:
            if not self.summon_timer.isActive():
                self.summon_timer.start(500)

    def capture_target_window(self):
        """Capture the currently focused window as the scroll target and center the control window"""
        (x, y) = self.long_press_handler.get_current_pos()
        try:
            self.target_window = win32gui.GetForegroundWindow()
            self.target_window_title = win32gui.GetWindowText(self.target_window)
            self.status_label.setText(f"Target: {self.target_window_title[:20]}...")
            logging.info(f"Captured target window: {self.target_window_title}")
            
            # Update window and button size based on scaling
            scaling = self.get_display_scaling()

            window_size = self.size()
            base_button_size = 80
            base_window_height = 400
            
            scaled_button_size = int(base_button_size * scaling)
            for button in self.buttons:
                button.setFixedSize(scaled_button_size, scaled_button_size)
                #self.update_button_radius(button, scaled_button_size // 2) 

            scaled_window_height = int(base_window_height * scaling)
            self.setFixedSize(scaled_button_size + int(30*scaling), scaled_window_height)
            

            # Center the window around the cursor position
            # Calculate centered position
            cursor_pos = QCursor.pos()
            new_x = cursor_pos.x() - (window_size.width() // 2)
            new_y = cursor_pos.y() - (window_size.height() // 2)
            
            # Ensure window stays within screen boundaries
            screen = QApplication.primaryScreen().geometry()
            
            # Adjust x position if window would go off screen
            # if new_x < 0:
            #     new_x = 0
            # elif new_x + window_size.width() > screen.width():
            #     new_x = screen.width() - window_size.width()
            
            # # Adjust y position if window would go off screen
            # if new_y < 0:
            #     new_y = 0
            # elif new_y + window_size.height() > screen.height():
            #     new_y = screen.height() - window_size.height()
            
            self.move(new_x, new_y)
            
        except Exception as e:
            logging.error(f"Error capturing window: {str(e)}")
            self.status_label.setText("Error capturing window!")

    def send_win_shift_k(self):
        """Send Win+Shift+K key combination"""
        self.send_keys(['windows', 'shift', 'k'])

    def send_win_tab(self):
        """Send Win+tab key combination"""
        self.send_keys(['windows', 'tab'])

    def send_keys(self, keys):
        """Send key combination"""
        try:
            for key in keys:
                keyboard.press(key)

            time.sleep(0.1)

            for key in reversed(keys):
                keyboard.release(key)
            
            self.status_label.setText(f"Sent {'+'.join(keys)}")
            logging.info(f"Sent {'+'.join(keys)} combination")
        except Exception as e:
            self.status_label.setText("Error sending keys!")
            logging.error(f"Error sending key combination: {str(e)}")

    def initUI(self):
        try:
            # Make the window transparent and frameless
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)

            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            
            # Set up main layout for the widget
            main_layout = QVBoxLayout(main_widget)
            main_layout.setContentsMargins(0, 0, 0, 0)  # No margins to keep layout tight around buttons

            # Make the main widget background fully transparent
            main_widget.setStyleSheet("""
                QWidget {
                    background-color: transparent;
                    border: none;
                }
            """)

            # Set up the grid layout for buttons in a single column§
            button_grid = QGridLayout()
            button_grid.setSpacing(5)

            # Configure the button layout and behavior
            button_configs = [
                ("↑", 0, 0, lambda: self.scroll_action(True)),
                ("↓", 1, 0, lambda: self.scroll_action(False)),
                ("jump", 2, 0, self.send_win_shift_k, "right"),  # Right button for jump action
                ("R", 3, 0, self.activate_invert_click, "left"), # Left button for invert click
                ("Win", 4, 0, self.send_win_tab),                # New button for Win+Tab action
            ]

            for text, row, col, callback, *args in button_configs:
                special_button = args[0] if args else None
                button = self.create_circular_button(text, special_button)
                if special_button == "left":
                    self.left_button = button
                elif special_button == "right":
                    self.right_button = button
                button.clicked.connect(callback)
                button_grid.addWidget(button, row, col)
                self.buttons.append(button)

            # Add the grid layout with buttons to the main layout
            main_layout.addLayout(button_grid)

            # Optional: Status label (currently commented out)
            self.status_label = QLabel("No target window set")
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setWordWrap(True)
            self.status_label.setFont(QFont("Arial", 10))
            self.status_label.setStyleSheet("color: white;")
            # main_layout.addWidget(self.status_label)

            # Update window size based on scaling
            scaling = self.get_display_scaling()
            base_button_size = 80
            base_window_height = 400
            
            scaled_button_size = int(base_button_size * scaling)
            scaled_window_height = int(base_window_height * scaling)
            
            self.setFixedSize(scaled_button_size + 30, scaled_window_height)
            logging.info("UI initialization completed successfully")

        except Exception as e:
            logging.error(f"Error in initUI: {str(e)}")
            raise




    def scroll_action(self, scroll_up):
        try:
            if not self.target_window:
                self.status_label.setText("No target window set!")
                return
                
            if not win32gui.IsWindow(self.target_window):
                self.status_label.setText("Target window no longer exists!")
                self.target_window = None
                return

            #print('scrolling up' if scroll_up else 'scrolling down')
            
            # Get the target window's position
            rect = win32gui.GetWindowRect(self.target_window)
            x = rect[0] + (rect[2] - rect[0]) // 2  # Center of the window
            y = rect[1] + (rect[3] - rect[1]) // 2
            
            # Store current cursor position
            current_pos = win32gui.GetCursorPos()
            
            # Move cursor to target window, scroll, and restore position
            win32api.SetCursorPos((x, y))
            win32gui.SetForegroundWindow(self.target_window)
            scroll_amount = self.scroll_amount if scroll_up else -self.scroll_amount
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, scroll_amount, 0)
            win32api.SetCursorPos(current_pos)
            
            direction = "up" if scroll_up else "down"
            self.status_label.setText(f"Scrolled {direction}")
            logging.debug(f"Scroll {direction} triggered")
            
        except Exception as e:
            self.status_label.setText("Error!")
            logging.error(f"Error in scroll_action: {str(e)}")

    def activate_invert_click(self):
        """Activate the one-time invert click functionality"""
        self.activate_right_click = True
        self.left_button.setEnabled(False)  # Disable the button while invert is active
        self.status_label.setText("Next left click will be a right click")
        logging.info("Invert click activated for next click")

    def check_for_click(self):
        """Check for left clicks and invert them if activated"""
        if self.activate_right_click and win32api.GetAsyncKeyState(win32con.VK_LBUTTON) < 0:
            # Store current cursor position
            original_pos = win32api.GetCursorPos()
            
            # Move cursor temporarily off-screen
            win32api.SetCursorPos((0, 0))
            
            # Perform right-click at original position
            win32api.SetCursorPos(original_pos)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, original_pos[0], original_pos[1], 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, original_pos[0], original_pos[1], 0, 0)
            
            # Reset the invert click state and update UI
            self.activate_right_click = False
            self.left_button.setEnabled(True)  # Re-enable the button
            self.status_label.setText("Right click performed")
            logging.info("Right click performed through inversion")

    def quit_application(self):
        logging.info("Quitting application")
        self.long_press_handler.stop()
        self.click_check_timer.stop()  # Stop the click check timer
        keyboard.unhook_all()
        QApplication.quit()
    
    def setupSystemTray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme("application-exit"))
        
        tray_menu = QMenu()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def setupQuitKey(self):
        keyboard.on_press_key('esc', lambda _: self.quit_application())
        logging.info("Quit key (Esc) registered")

    def quit_application(self):
        logging.info("Quitting application")
        self.long_press_handler.stop()
        keyboard.unhook_all()
        QApplication.quit()

    def closeEvent(self, event):
        self.quit_application()

def main():
    try:
        app = QApplication(sys.argv)
        window = FloatingControlWindow()
        window.show()
        logging.info("Application started successfully")
        sys.exit(app.exec_())
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        raise

if __name__ == '__main__':
    main()