import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("카메라 열기 실패")
    exit()

ret, frame = cap.read()

if not ret:
    print("프레임 읽기 실패")
    exit()

cv2.imwrite("test.jpg", frame)
print("test.jpg 저장 완료")

cap.release()