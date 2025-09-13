import cv2
import numpy as np
import math
import sys

# -------------------------------------------------------------------------------------------------------
#                                           SECTION 1: SETUP
# -------------------------------------------------------------------------------------------------------

# Using your saved port for the video stream.
video_url = "http://192.168.0.155:8080/video"

# Initialize the video capture object.
cap = cv2.VideoCapture(video_url)

# Check if the video stream was opened successfully.
if not cap.isOpened():
    sys.exit("Error: Could not open video stream.")

# Define the lower and upper bounds for each color in the HSV color space.
color_ranges = {
    'red': {
        'lower1': np.array([0, 120, 70]),
        'upper1': np.array([10, 255, 255]),
        'lower2': np.array([170, 120, 70]),
        'upper2': np.array([180, 255, 255])
    },
    'green': {
        'lower': np.array([36, 100, 100]),
        'upper': np.array([86, 255, 255])
    },
    'blue': {
        'lower': np.array([94, 120, 100]),
        'upper': np.array([126, 255, 255])
    }
}

# -------------------------------------------------------------------------------------------------------
#                                SECTION 2: SHAPE DETECTION FUNCTION
# -------------------------------------------------------------------------------------------------------

def detect_shape(contour):
    """
    Analyzes a contour and returns its shape as a string.
    Identifies 'triangle', 'square', 'rectangle', or 'circle'.
    """
    shape = "unknown"
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
    
    if len(approx) == 3:
        shape = "triangle"
    elif len(approx) == 4:
        (x, y, w, h) = cv2.boundingRect(approx)
        aspect_ratio = float(w) / h
        if 0.90 <= aspect_ratio <= 1.10:
            shape = "square"
        else:
            shape = "rectangle"
    else:
        area = cv2.contourArea(contour)
        (x, y), radius = cv2.minEnclosingCircle(contour)
        if radius > 0:
            circle_area = np.pi * (radius**2)
            circularity = area / circle_area
            if 0.75 < circularity < 1.2:
                shape = "circle"
                
    return shape

# -------------------------------------------------------------------------------------------------------
#                       SECTION 3: CORE VIDEO PROCESSING (Performance MODE)
# -------------------------------------------------------------------------------------------------------

def main_obstacle_detection():
    """Main video processing loop for obstacle detection and avoidance - Performance mode"""
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        height, width, _ = frame.shape
        frame_center_x, frame_center_y = width // 2, height // 2
        
        dangerous_obstacles = []  # Stores (cX, cY) of Red Triangles

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

# -------------------------------------------------------------------------------------------------------
#                        SECTION 4: OBJECT DETECTION AND CLASSIFICATION
# -------------------------------------------------------------------------------------------------------
        
        for color_name, ranges in color_ranges.items():
            mask = None
            if color_name == 'red':
                mask1 = cv2.inRange(hsv, ranges['lower1'], ranges['upper1'])
                mask2 = cv2.inRange(hsv, ranges['lower2'], ranges['upper2'])
                mask = cv2.bitwise_or(mask1, mask2)
            else:
                mask = cv2.inRange(hsv, ranges['lower'], ranges['upper'])
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                if cv2.contourArea(contour) < 400:
                    continue

                shape = detect_shape(contour)
                
                M = cv2.moments(contour)
                cX = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
                cY = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0

                classification = ""
                if color_name == 'red' and shape == 'triangle':
                    classification = "Dangerous obstacle"
                    dangerous_obstacles.append((cX, cY)) 
                    cv2.drawContours(frame, [contour], -1, (0, 0, 255), 3)
                elif color_name == 'blue' and shape == 'square':
                    classification = "Boundary marker"
                    cv2.drawContours(frame, [contour], -1, (255, 0, 0), 3)
                elif color_name == 'green' and shape == 'circle':
                    classification = "Safe zone"
                    cv2.drawContours(frame, [contour], -1, (0, 255, 0), 3)
                
                if classification:
                    cv2.putText(frame, classification, (cX - 50, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

# -------------------------------------------------------------------------------------------------------
#                               SECTION 5: OBSTACLE AVOIDANCE LOGIC
# -------------------------------------------------------------------------------------------------------
        
        command = "Clear"

        if dangerous_obstacles:
            closest_obstacle = min(dangerous_obstacles, 
                                   key=lambda pos: math.sqrt((pos[0] - frame_center_x)**2 + (pos[1] - frame_center_y)**2))
            
            closest_obs_x, closest_obs_y = closest_obstacle
            cv2.circle(frame, (closest_obs_x, closest_obs_y), 30, (0, 255, 255), 3)

            dx = closest_obs_x - frame_center_x
            dy = closest_obs_y - frame_center_y

            if abs(dx) > abs(dy):
                if dx > 0:
                    command = "Roll Left"
                else:
                    command = "Roll Right"
            else:
                if dy > 0:
                    command = "Pitch Up"
                else:
                    command = "Pitch Down"

# -------------------------------------------------------------------------------------------------------
#                            SECTION 6: DISPLAY COMMAND AND VISUAL AIDS
# -------------------------------------------------------------------------------------------------------
        
        # Display the final command
        cv2.putText(frame, f"COMMAND: {command}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
        
        # Draw precise center lines for even quadrant distribution
        cv2.line(frame, (frame_center_x, 0), (frame_center_x, height), (128, 128, 128), 2)
        cv2.line(frame, (0, frame_center_y), (width, frame_center_y), (128, 128, 128), 2)
        
        # Draw additional quadrant lines for better visualization
        quarter_width = width // 4
        quarter_height = height // 4
        cv2.line(frame, (quarter_width, 0), (quarter_width, height), (64, 64, 64), 1)
        cv2.line(frame, (3 * quarter_width, 0), (3 * quarter_width, height), (64, 64, 64), 1)
        cv2.line(frame, (0, quarter_height), (width, quarter_height), (64, 64, 64), 1)
        cv2.line(frame, (0, 3 * quarter_height), (width, 3 * quarter_height), (64, 64, 64), 1)

        # --- NEW: Draw a sniper-style marker at the center ---
        marker_color = (0, 255, 255)  # Bright Yellow
        # Draw the central circle
        cv2.circle(frame, (frame_center_x, frame_center_y), 25, marker_color, 1)
        # Draw the crosshairs
        cv2.line(frame, (frame_center_x - 35, frame_center_y), (frame_center_x + 35, frame_center_y), marker_color, 1)
        cv2.line(frame, (frame_center_x, frame_center_y - 35), (frame_center_x, frame_center_y + 35), marker_color, 1)

        # Resize the final frame for a consistent window size
        display_width = 1200
        aspect_ratio = height / width
        display_height = int(display_width * aspect_ratio)
        display_frame = cv2.resize(frame, (display_width, display_height))

        # Show the final frame
        cv2.imshow("Avoidance System", display_frame)
        
        # Exit loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# -------------------------------------------------------------------------------------------------------
#            SECTION 7: AIRPLANE ANIMATION IMPORTS (COMMENT THIS SECTION TO DISABLE)
# -------------------------------------------------------------------------------------------------------
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
import threading
import time

# Global variables for airplane animation
airplane_roll = 0.0  # Roll angle in degrees
airplane_pitch = 0.0  # Pitch offset (vertical movement)
elevator_angle = 0.0  # Elevator deflection angle
current_command = "Clear"
animation_speed = 2.0  # Speed of animation
target_roll = 0.0
target_pitch = 0.0
target_elevator = 0.0

# -------------------------------------------------------------------------------------------------------
#               SECTION 8: AIRPLANE GUI CLASS (COMMENT THIS SECTION TO DISABLE)
# -------------------------------------------------------------------------------------------------------

class AirplaneGUI:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        self.ax.set_xlim(-120, 120)
        self.ax.set_ylim(-90, 90)
        self.ax.set_aspect('equal')
        self.ax.set_facecolor('skyblue')
        self.ax.set_title('Airplane Back View - Avoidance System', fontsize=16, fontweight='bold')
        
        # Remove axis ticks and labels for cleaner look
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        # Initialize airplane parts
        self.fuselage = None
        self.left_wing = None
        self.right_wing = None
        self.vertical_stabilizer = None
        self.horizontal_stabilizer_left = None
        self.horizontal_stabilizer_right = None
        self.elevator_left = None
        self.elevator_right = None
        self.rudder = None
        self.cockpit = None
        self.left_aileron = None
        self.right_aileron = None
        self.command_text = None
        
        self.setup_airplane()
        
    def setup_airplane(self):
        """Initialize the airplane parts with enhanced design"""
        # Fuselage (main body) - more realistic shape
        self.fuselage = patches.Rectangle((-12, -40), 24, 80, 
                                        facecolor='lightgray', 
                                        edgecolor='black', 
                                        linewidth=2)
        self.ax.add_patch(self.fuselage)
        
        # Cockpit/nose section
        self.cockpit = patches.Rectangle((-8, -45), 16, 10, 
                                       facecolor='darkblue', 
                                       edgecolor='black', 
                                       linewidth=2)
        self.ax.add_patch(self.cockpit)
        
        # Main wings - larger and more realistic
        self.left_wing = patches.Rectangle((-80, -8), 65, 16, 
                                         facecolor='silver', 
                                         edgecolor='black', 
                                         linewidth=2)
        self.right_wing = patches.Rectangle((15, -8), 65, 16, 
                                          facecolor='silver', 
                                          edgecolor='black', 
                                          linewidth=2)
        
        # Ailerons (wing control surfaces)
        self.left_aileron = patches.Rectangle((-75, -6), 25, 4, 
                                            facecolor='darkgray', 
                                            edgecolor='black', 
                                            linewidth=1)
        self.right_aileron = patches.Rectangle((50, -6), 25, 4, 
                                             facecolor='darkgray', 
                                             edgecolor='black', 
                                             linewidth=1)
        
        self.ax.add_patch(self.left_wing)
        self.ax.add_patch(self.right_wing)
        self.ax.add_patch(self.left_aileron)
        self.ax.add_patch(self.right_aileron)
        
        # Vertical stabilizer (tail fin)
        self.vertical_stabilizer = patches.Rectangle((-6, 35), 12, 25, 
                                                   facecolor='lightgray', 
                                                   edgecolor='black', 
                                                   linewidth=2)
        self.ax.add_patch(self.vertical_stabilizer)
        
        # Rudder (vertical control surface)
        self.rudder = patches.Rectangle((-4, 45), 8, 15, 
                                      facecolor='darkgray', 
                                      edgecolor='black', 
                                      linewidth=1)
        self.ax.add_patch(self.rudder)
        
        # Horizontal stabilizers
        self.horizontal_stabilizer_left = patches.Rectangle((-35, 30), 25, 8, 
                                                           facecolor='lightgray', 
                                                           edgecolor='black', 
                                                           linewidth=2)
        self.horizontal_stabilizer_right = patches.Rectangle((10, 30), 25, 8, 
                                                            facecolor='lightgray', 
                                                            edgecolor='black', 
                                                            linewidth=2)
        
        # Elevators (horizontal control surfaces) - these will move for pitch
        self.elevator_left = patches.Rectangle((-30, 32), 15, 4, 
                                             facecolor='red', 
                                             edgecolor='black', 
                                             linewidth=1)
        self.elevator_right = patches.Rectangle((15, 32), 15, 4, 
                                              facecolor='red', 
                                              edgecolor='black', 
                                              linewidth=1)
        
        self.ax.add_patch(self.horizontal_stabilizer_left)
        self.ax.add_patch(self.horizontal_stabilizer_right)
        self.ax.add_patch(self.elevator_left)
        self.ax.add_patch(self.elevator_right)
        
        # Command display
        self.command_text = self.ax.text(0, -75, 'COMMAND: Clear', 
                                       horizontalalignment='center',
                                       fontsize=14, 
                                       fontweight='bold',
                                       bbox=dict(boxstyle='round', 
                                               facecolor='yellow', 
                                               alpha=0.9))
        
        # Add reference lines for center alignment
        self.ax.axhline(y=0, color='brown', linestyle='--', alpha=0.7, linewidth=1)
        self.ax.axvline(x=0, color='brown', linestyle='--', alpha=0.7, linewidth=1)
        self.ax.text(105, 2, 'Horizon', fontsize=10, alpha=0.8)
        self.ax.text(2, 85, 'Center', fontsize=10, alpha=0.8)
        
        # Add quadrant grid for better visualization
        self.ax.axhline(y=45, color='gray', linestyle=':', alpha=0.3)
        self.ax.axhline(y=-45, color='gray', linestyle=':', alpha=0.3)
        self.ax.axvline(x=60, color='gray', linestyle=':', alpha=0.3)
        self.ax.axvline(x=-60, color='gray', linestyle=':', alpha=0.3)
        
    def update_airplane(self, frame):
        """Update airplane position and rotation based on current command"""
        global airplane_roll, airplane_pitch, elevator_angle, current_command, target_roll, target_pitch, target_elevator
        
        # Smooth animation towards target positions
        roll_diff = target_roll - airplane_roll
        pitch_diff = target_pitch - airplane_pitch
        elevator_diff = target_elevator - elevator_angle
        
        airplane_roll += roll_diff * 0.12  # Smooth interpolation
        airplane_pitch += pitch_diff * 0.12
        elevator_angle += elevator_diff * 0.15  # Faster elevator response
        
        # Apply pitch (vertical movement of entire aircraft)
        fuselage_y = airplane_pitch
        
        # Calculate wing positions based on roll
        roll_rad = math.radians(airplane_roll)
        
        # Wing positions with roll direction
        # For "Roll Left" command (target_roll = -35), left wing should go down (positive y)
        # For "Roll Right" command (target_roll = +35), right wing should go down (positive y)
        left_wing_y = -8 + airplane_pitch + 25 * math.sin(roll_rad)   # CHANGED: + instead of -
        right_wing_y = -8 + airplane_pitch - 25 * math.sin(roll_rad)  # CHANGED: - instead of +
        
        # Aileron positions (move opposite to each other during roll)
        left_aileron_y = -6 + airplane_pitch + 25 * math.sin(roll_rad) - 2 * math.sin(roll_rad)  
        right_aileron_y = -6 + airplane_pitch - 25 * math.sin(roll_rad) + 2 * math.sin(roll_rad)  
        
        # Update main aircraft components with pitch
        self.fuselage.set_y(-40 + fuselage_y)
        self.cockpit.set_y(-45 + fuselage_y)
        self.vertical_stabilizer.set_y(35 + fuselage_y)
        self.rudder.set_y(45 + fuselage_y)
        
        # Update wings with roll and pitch
        self.left_wing.set_y(left_wing_y)
        self.right_wing.set_y(right_wing_y)
        self.left_aileron.set_y(left_aileron_y)
        self.right_aileron.set_y(right_aileron_y)
        
        # Update horizontal stabilizers
        h_stab_y = 30 + airplane_pitch
        self.horizontal_stabilizer_left.set_y(h_stab_y)
        self.horizontal_stabilizer_right.set_y(h_stab_y)
        
        # Update elevators with deflection angle for pitch control
        elevator_deflection = elevator_angle * 0.3  # Scale the deflection
        self.elevator_left.set_y(32 + airplane_pitch + elevator_deflection)
        self.elevator_right.set_y(32 + airplane_pitch + elevator_deflection)
        
        # Create rotation transforms for wings during roll
        wing_roll_angle = -airplane_roll  
        left_transform = plt.matplotlib.transforms.Affine2D().rotate_deg_around(
            -47.5, left_wing_y + 8, wing_roll_angle) + self.ax.transData
        right_transform = plt.matplotlib.transforms.Affine2D().rotate_deg_around(
            47.5, right_wing_y + 8, wing_roll_angle) + self.ax.transData
        
        # Apply transforms
        self.left_wing.set_transform(left_transform)
        self.right_wing.set_transform(right_transform)
        
        # Aileron transforms 
        left_aileron_angle = wing_roll_angle + 5 * math.sin(roll_rad)   
        right_aileron_angle = wing_roll_angle - 5 * math.sin(roll_rad)  
        
        left_aileron_transform = plt.matplotlib.transforms.Affine2D().rotate_deg_around(
            -62.5, left_aileron_y + 2, left_aileron_angle) + self.ax.transData
        right_aileron_transform = plt.matplotlib.transforms.Affine2D().rotate_deg_around(
            62.5, right_aileron_y + 2, right_aileron_angle) + self.ax.transData
        
        self.left_aileron.set_transform(left_aileron_transform)
        self.right_aileron.set_transform(right_aileron_transform)
        
        # Update command text
        self.command_text.set_text(f'COMMAND: {current_command}')
        
        # Color coding for commands with more detailed feedback
        if current_command == "Clear":
            self.command_text.set_bbox(dict(boxstyle='round', facecolor='lightgreen', alpha=0.9))
        elif "Roll" in current_command:
            self.command_text.set_bbox(dict(boxstyle='round', facecolor='orange', alpha=0.9))
        elif "Pitch" in current_command:
            self.command_text.set_bbox(dict(boxstyle='round', facecolor='red', alpha=0.9))
        
        return [self.fuselage, self.cockpit, self.left_wing, self.right_wing, 
                self.left_aileron, self.right_aileron, self.vertical_stabilizer, 
                self.rudder, self.horizontal_stabilizer_left, self.horizontal_stabilizer_right,
                self.elevator_left, self.elevator_right, self.command_text]

# -------------------------------------------------------------------------------------------------------
#            SECTION 9: VIDEO PROCESSING WITH ANIMATION (COMMENT THIS SECTION TO DISABLE)
# -------------------------------------------------------------------------------------------------------

def video_processing_thread():
    """Process video stream and update airplane commands with threading for GUI"""
    global current_command, target_roll, target_pitch, target_elevator
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        height, width, _ = frame.shape
        frame_center_x, frame_center_y = width // 2, height // 2
        
        dangerous_obstacles = []  # Stores (cX, cY) of Red Triangles

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # --------------------------------------------------------------------------
        #                   OBJECT DETECTION AND CLASSIFICATION
        # --------------------------------------------------------------------------
        
        for color_name, ranges in color_ranges.items():
            mask = None
            if color_name == 'red':
                mask1 = cv2.inRange(hsv, ranges['lower1'], ranges['upper1'])
                mask2 = cv2.inRange(hsv, ranges['lower2'], ranges['upper2'])
                mask = cv2.bitwise_or(mask1, mask2)
            else:
                mask = cv2.inRange(hsv, ranges['lower'], ranges['upper'])
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                if cv2.contourArea(contour) < 400:
                    continue

                shape = detect_shape(contour)
                
                M = cv2.moments(contour)
                cX = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
                cY = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0

                classification = ""
                if color_name == 'red' and shape == 'triangle':
                    classification = "Dangerous obstacle"
                    dangerous_obstacles.append((cX, cY)) 
                    cv2.drawContours(frame, [contour], -1, (0, 0, 255), 3)
                elif color_name == 'blue' and shape == 'square':
                    classification = "Boundary marker"
                    cv2.drawContours(frame, [contour], -1, (255, 0, 0), 3)
                elif color_name == 'green' and shape == 'circle':
                    classification = "Safe zone"
                    cv2.drawContours(frame, [contour], -1, (0, 255, 0), 3)
                
                if classification:
                    cv2.putText(frame, classification, (cX - 50, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # --------------------------------------------------------------------------
        #                       OBSTACLE AVOIDANCE LOGIC
        # --------------------------------------------------------------------------
        
        command = "Clear"
        new_target_roll = 0.0
        new_target_pitch = 0.0
        new_target_elevator = 0.0

        if dangerous_obstacles:
            closest_obstacle = min(dangerous_obstacles, 
                                   key=lambda pos: math.sqrt((pos[0] - frame_center_x)**2 + (pos[1] - frame_center_y)**2))
            
            closest_obs_x, closest_obs_y = closest_obstacle
            cv2.circle(frame, (closest_obs_x, closest_obs_y), 30, (0, 255, 255), 3)

            dx = closest_obs_x - frame_center_x
            dy = closest_obs_y - frame_center_y

            if abs(dx) > abs(dy):
                if dx > 0:
                    command = "Roll Left"
                    new_target_roll = -35  # Roll left
                else:
                    command = "Roll Right"
                    new_target_roll = 35   # Roll right
            else:
                if dy > 0:
                    command = "Pitch Up"
                    new_target_pitch = 20   # Pitch up (climb)
                    new_target_elevator = -15  # Elevator up (negative deflection)
                else:
                    command = "Pitch Down"
                    new_target_pitch = -20  # Pitch down (dive)
                    new_target_elevator = 15   # Elevator down (positive deflection)
        
        # Update global variables for airplane animation
        current_command = command
        target_roll = new_target_roll
        target_pitch = new_target_pitch
        target_elevator = new_target_elevator

        # --------------------------------------------------------------------------
        #                       DISPLAY COMMAND AND VISUAL AIDS
        # --------------------------------------------------------------------------
        
        # Display the final command
        cv2.putText(frame, f"COMMAND: {command}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
        
        # Draw precise center lines for even quadrant distribution
        cv2.line(frame, (frame_center_x, 0), (frame_center_x, height), (128, 128, 128), 2)
        cv2.line(frame, (0, frame_center_y), (width, frame_center_y), (128, 128, 128), 2)
        
        # Draw additional quadrant lines for better visualization
        quarter_width = width // 4
        quarter_height = height // 4
        cv2.line(frame, (quarter_width, 0), (quarter_width, height), (64, 64, 64), 1)
        cv2.line(frame, (3 * quarter_width, 0), (3 * quarter_width, height), (64, 64, 64), 1)
        cv2.line(frame, (0, quarter_height), (width, quarter_height), (64, 64, 64), 1)
        cv2.line(frame, (0, 3 * quarter_height), (width, 3 * quarter_height), (64, 64, 64), 1)

        # --- Draw a sniper-style marker at the center ---
        marker_color = (0, 255, 255)  # Bright Yellow
        # Draw the central circle
        cv2.circle(frame, (frame_center_x, frame_center_y), 25, marker_color, 1)
        # Draw the crosshairs
        cv2.line(frame, (frame_center_x - 35, frame_center_y), (frame_center_x + 35, frame_center_y), marker_color, 1)
        cv2.line(frame, (frame_center_x, frame_center_y - 35), (frame_center_x, frame_center_y + 35), marker_color, 1)

        # Resize the final frame for display (smaller when GUI is active)
        display_width = 800  # Smaller width to fit alongside GUI
        aspect_ratio = height / width
        display_height = int(display_width * aspect_ratio)
        display_frame = cv2.resize(frame, (display_width, display_height))

        # Show the final frame
        cv2.imshow("Avoidance System", display_frame)
        
        # Exit loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        time.sleep(0.033)  # ~30 FPS

# -------------------------------------------------------------------------------------------------------
#                                SECTION 10: MAIN EXECUTION CONTROLLER
# -------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    # CHOOSE EXECUTION MODE:
        # Set to True for GUI animation + video processing
        # Set to False for video processing only (better performance)
    ENABLE_ANIMATION = True
    
    try:
        if ENABLE_ANIMATION:
            # --------------------------------------------------------------------------
            #       ANIMATION MODE: Run both video processing & airplane GUI
            # --------------------------------------------------------------------------
            print("Starting with airplane animation GUI...")
            
            # Create airplane GUI
            airplane_gui = AirplaneGUI()
            
            # Start video processing in a separate thread
            video_thread = threading.Thread(target=video_processing_thread, daemon=True)
            video_thread.start()
            
            # Start airplane animation
            anim = FuncAnimation(airplane_gui.fig, airplane_gui.update_airplane, 
                                interval=50, blit=False, cache_frame_data=False)
            
            # Show the matplotlib GUI
            plt.show()
            
        else:
            # --------------------------------------------------------------------------
            #   PERFORMANCE MODE: Run only core obstacle detection (no animation)
            # --------------------------------------------------------------------------
            print("Starting in performance mode (no animation)...")
            main_obstacle_detection()
            
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
# -------------------------------------------------------------------------------------------------------
#                                       SECTION 11: CLEANUP
# -------------------------------------------------------------------------------------------------------
        print("Cleaning up...")
        cap.release()
        cv2.destroyAllWindows()
        if 'plt' in globals():
            plt.close('all')
        print("Program ended successfully")