import cv2
import mediapipe as mp
import numpy as np

# Webcam
cap = cv2.VideoCapture(0)

# Better resolution
cap.set(3, 1280)
cap.set(4, 720)

# MediaPipe
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.45,
    min_tracking_confidence=0.45
)

# Previous cursor point for smoothing
prev_cursor = None

# Previous drawing point for continuous strokes
prev_draw = None

# Canvas
canvas = None

draw_color = (255, 0, 255)
cursor_color = (90, 255, 170)
move_color = (180, 180, 180)
smoothing = 0.45
brush_size = 8
max_jump = 120
missed_frames = 0
max_missed_frames = 8
pinch_ratio = 0.55
eraser_button = (25, 25, 180, 85)


def draw_eraser_button(frame):
    x1, y1, x2, y2 = eraser_button

    cv2.rectangle(frame, (x1, y1), (x2, y2), (40, 40, 40), cv2.FILLED)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (90, 255, 170), 2)
    cv2.putText(
        frame,
        "ERASE",
        (x1 + 28, y1 + 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (90, 255, 170),
        2
    )


def is_inside_button(point):
    x, y = point
    x1, y1, x2, y2 = eraser_button
    return x1 <= x <= x2 and y1 <= y <= y2

while True:

    success, frame = cap.read()

    if not success:
        break

    # Mirror view
    frame = cv2.flip(frame, 1)

    # Create canvas
    if canvas is None:
        canvas = np.zeros_like(frame)

    # RGB conversion
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Hand detection
    results = hands.process(rgb_frame)

    draw_eraser_button(frame)

    if results.multi_hand_landmarks:
        missed_frames = 0

        for hand_landmarks in results.multi_hand_landmarks:
            # Draw complete hand tracing
            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            # Finger landmarks
            index_tip = hand_landmarks.landmark[8]
            thumb_tip = hand_landmarks.landmark[4]
            wrist = hand_landmarks.landmark[0]
            middle_mcp = hand_landmarks.landmark[9]

            h, w, c = frame.shape

            # Current finger coordinates
            tip_x = int(index_tip.x * w)
            tip_y = int(index_tip.y * h)
            thumb_x = int(thumb_tip.x * w)
            thumb_y = int(thumb_tip.y * h)
            wrist_x = int(wrist.x * w)
            wrist_y = int(wrist.y * h)
            middle_mcp_x = int(middle_mcp.x * w)
            middle_mcp_y = int(middle_mcp.y * h)

            # Smoothing
            if prev_cursor is None:
                smooth_x, smooth_y = tip_x, tip_y
            else:
                prev_cursor_x, prev_cursor_y = prev_cursor
                smooth_x = int(prev_cursor_x + (tip_x - prev_cursor_x) * smoothing)
                smooth_y = int(prev_cursor_y + (tip_y - prev_cursor_y) * smoothing)

            prev_cursor = (smooth_x, smooth_y)

            pinch_distance = np.hypot(tip_x - thumb_x, tip_y - thumb_y)
            hand_size = np.hypot(middle_mcp_x - wrist_x, middle_mcp_y - wrist_y)
            draw_mode = pinch_distance < hand_size * pinch_ratio

            if is_inside_button((smooth_x, smooth_y)):
                canvas = np.zeros_like(frame)
                prev_draw = None
                draw_mode = False

            active_cursor_color = cursor_color if draw_mode else move_color

            # Cursor
            cv2.circle(
                frame,
                (smooth_x, smooth_y),
                brush_size + 4,
                active_cursor_color,
                cv2.FILLED
            )

            if draw_mode:
                # Start a new stroke
                if prev_draw is None:
                    prev_draw = (smooth_x, smooth_y)
                else:
                    jump = np.hypot(smooth_x - prev_draw[0], smooth_y - prev_draw[1])

                    # Draw only natural movements, not sudden tracking jumps
                    if jump < max_jump:
                        cv2.line(
                            canvas,
                            prev_draw,
                            (smooth_x, smooth_y),
                            draw_color,
                            brush_size
                        )
                    else:
                        cv2.circle(
                            canvas,
                            (smooth_x, smooth_y),
                            brush_size // 2,
                            draw_color,
                            cv2.FILLED
                        )

                    prev_draw = (smooth_x, smooth_y)
            else:
                prev_draw = None
    else:
        missed_frames += 1

        if missed_frames > max_missed_frames:
            prev_cursor = None
            prev_draw = None

    # Merge
    final_output = cv2.add(frame, canvas)

    # Show
    cv2.imshow("Air Draw", final_output)

    key = cv2.waitKey(1) & 0xFF

    # Clear canvas
    if key == ord('c'):
        canvas = np.zeros_like(frame)

    # Quit
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
