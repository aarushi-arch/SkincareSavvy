import mediapipe as mp
print("MediaPipe file:", mp.__file__)
print("Attributes:", dir(mp))
try:
    print("Solutions available:", mp.solutions)
except AttributeError as e:
    print("Error accessing solutions:", e)
