import cv2
import time
import numpy as np
from Foundation import NSUserNotification, NSUserNotificationCenter

# Load the Haar cascade model for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

def show_notification(title, subtitle, text):
    # Create a notification
    notification = NSUserNotification.alloc().init()
    notification.setTitle_(title)
    notification.setSubtitle_(subtitle)
    notification.setInformativeText_(text)

    # Display the notification
    notification_center = NSUserNotificationCenter.defaultUserNotificationCenter()
    notification_center.deliverNotification_(notification)

EAR_THRESHOLD = 0.25
def calculate_ear(eye):
    # Calculate the coordinates of the top and bottom points of the eye
    (x, y, w, h) = eye
    top_y = y + h // 4
    bottom_y = y + h * 3 // 4

    # Calculate the distance between the top and bottom points of the eye
    eye_height = bottom_y - top_y

    # Calculate the distance between the left and right points of the eye
    eye_width = w

    # Return the ratio of height to width
    return eye_height / eye_width

def detect_face_and_lighting():
    # Capture video from the webcam
    cap = cv2.VideoCapture(0)

    previous_distance = None
    base_ear = None
    blink_counter = 0
    prev_ear_time = time.time()
    prev_blink_reset_time = time.time()
    notification_shown = False  # Add a flag to indicate whether a notification has been shown

    while True:
        # Read a frame
        ret, frame = cap.read()

        if not ret:
            break

        # Convert the frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces in the frame
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces) > 0:
            # Calculate the distance from the face to the screen (simple approximation)
            face_size = faces[0][2] * faces[0][3]
            distance = 60 / (face_size ** 0.5)  # 60 is an empirical constant

            # If the distance is less than or equal to the given threshold
            if distance <= 0.09:  # 15 is an empirical constant
                # Display a macOS notification
                show_notification('Предупреждение', ' Недопустимое расстояние от экрана до глаз', 'Отдалитесь')
            elif distance > 0.09 and distance < 0.12:
                show_notification('Предупреждение', 'Расстояние от экрана на грани', 'В таком положении ваши глаза устают быстрее')

            previous_distance = distance

        # Check lighting
        avg_intensity = np.average(gray)
        if avg_intensity < 50:
            show_notification('Предупреждение', 'Освещенность помещения', 'Включите свет')

        if len(faces) == 1:
            (x, y, w, h) = faces[0]

            # Define regions around the eyes
            left_eye_region = gray[y:y+h//2, x:x+w//2]
            right_eye_region = gray[y:y+h//2, x+w//2:x+w]

            # Detect eyes
            left_eyes = eye_cascade.detectMultiScale(left_eye_region, 1.1, 3)
            right_eyes = eye_cascade.detectMultiScale(right_eye_region, 1.1, 3)

            # If both eyes are detected, calculate EAR
            if len(left_eyes) == 1 and len(right_eyes) == 1:
                (left_eye_x, left_eye_y, left_eye_w, left_eye_h) = left_eyes[0]
                (right_eye_x, right_eye_y, right_eye_w, right_eye_h) = right_eyes[0]

                # Calculate the width and height of the eyes
                left_eye_width = left_eye_w
                left_eye_height = left_eye_h
                right_eye_width = right_eye_w
                right_eye_height = right_eye_h

                # Calculate the distance between the eyes
                eye_center_x = x + w // 2
                eye_center_y = y + h // 4
                eye_distance = np.sqrt((left_eye_x + left_eye_w // 2 - eye_center_x)**2 + (left_eye_y + left_eye_h // 2 - eye_center_y)**2)

                # Calculate points on the upper and lower eyelids
                left_eye_top = (left_eye_x + left_eye_w // 4, left_eye_y)
                left_eye_bottom = (left_eye_x + left_eye_w // 4 * 3, left_eye_y + left_eye_h)
                right_eye_top = (right_eye_x + right_eye_w // 4, right_eye_y)
                right_eye_bottom = (right_eye_x + right_eye_w // 4 * 3, right_eye_y + right_eye_h)

                # Calculate distances between points on the upper and lower eyelids
                left_eye_vertical = np.sqrt((left_eye_top[0] - left_eye_bottom[0])**2 + (left_eye_top[1] - left_eye_bottom[1])**2)
                right_eye_vertical = np.sqrt((right_eye_top[0] - right_eye_bottom[0])**2 + (right_eye_top[1] - right_eye_bottom[1])**2)

                # Calculate EAR
                left_ear = left_eye_vertical / (2.0 * eye_distance)
                right_ear = right_eye_vertical / (2.0 * eye_distance)
                ear = (left_ear + right_ear) / 2.0

                # Determine the base EAR value
                if base_ear is None:
                    base_ear = ear

                # Determine blinking
                if ear < base_ear * 0.95 or ear > base_ear * 1.05:
                    blink_counter += 1

                # Display EAR every second
                if time.time() - prev_ear_time >= 1:
                    prev_ear_time = time.time()
                    print("EAR: {:.2f}".format(ear))

            # If the left eye is not detected, consider it a blink
            elif len(left_eyes) == 0:
                blink_counter += 1

            # If the right eye is not detected, consider it a blink
            elif len(right_eyes) == 0:
                blink_counter += 1

        # Exit the loop if the 'q' key is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Reset the blink counter every 30 seconds
        if time.time() - prev_blink_reset_time >= 30:
            prev_blink_reset_time = time.time()
            blink_counter = 0
            notification_shown = False  # Reset the notification flag after 30 seconds

        # Display a notification if the number of blinks exceeds the threshold and a notification has not been shown yet
        #if blink_counter > 50 and not notification_shown:
            #show_notification("Усталось глаз", "Сделайте перерыв", "У вас повышенное количество морганий в минуту. Советую сделать перерыв")
            #blink_counter = 0
            #notification_shown = True  # Set the notification flag to True

            # Pause for 1 second between iterations
            time.sleep(5)

    # Release resources
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    detect_face_and_lighting()
