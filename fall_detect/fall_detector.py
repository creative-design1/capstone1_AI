import time
import cv2
from pathlib import Path
from .extractor import PoseExtractor
from .sender import Sender
from .fall import Fall_Detector
from .features import compute_features
from .walking import WalkingDetector
import threading


"""
BASE_DIR = Path.cwd().parent

model_path = BASE_DIR / "models" / "best_fall_model.pth"
scaler_path = BASE_DIR / "src" / "scaler.save"
video_source = 0

fall_api_path = url + "/api/events/fall-detection"
stride_api_path = url + "/api/events/features"
audio_source = None #url + "/audio.opus"

detector = Fall_Detector(model_path=model_path, scaler_path=scaler_path, device='cpu')
extractor = PoseExtractor()
#fall_sender = Sender(url=fall_api_path)
#stride_sender = Sender(url=stride_api_path)
walk = WalkingDetector()
#chatbot = ChatBot(rstp_url=audio_source)

cap = cv2.VideoCapture("http://10.93.152.178:8080/?action=stream")

if not cap.isOpened():
    print("Error: Unable to open video source.")
    exit(1)
    
print("starting fall detection!")

#chatbot.start()
#print("ChatBot started.")

sent_fall = False
missing_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Unable to read frame from video source.")
        break
    
    features = None
    keypoints = extractor.extract_keypoints(frame)
    if not walk.detect_person(keypoints) or keypoints is None:
        #print("No person detected.")
        missing_count += 1
        if missing_count >= 10:
            detector.buffer.clear()
            walk.reset()
            sent_fall = False
            
        continue
    else:
        missing_count = 0
        #print("Person detected.")
        
    walking = walk.update(keypoints)
    detector.update_sequence(keypoints)
    
    fall_detected, fall_prob = detector.predict()
    
    #if len(detector.buffer) == detector.buffer.maxlen:
    #    features = compute_features(list(detector.buffer), fps=30)
    #else:
    #    features = {}
    
    data = {
            "elderlyUserId": 1,
            "fall_prob": fall_prob,
            "fall_detected": fall_detected,
            #"detectedAt": "2024-06-01 12:00:00"
            "detectedAt": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        }
    
    #print(data)
    if fall_detected:
        if not sent_fall:
            data = {
                "elderlyUserId": 1,
                "fall_prob": fall_prob,
                "fall_detected": fall_detected,
                "detectedAt": "2024-06-01 12:00:00"
                #"detectedAt": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            }
                #"stride_mean": features.get("stride_mean", 0.0),
                #"stride_std": features.get("stride_std", 0.0),
                #"velocity": features.get("velocity", 0.0),
            #fall_sender.send(data)
            print(f"Fall detected! Probability: {fall_prob:.2f}, Data sent.")
            sent_fall = True
        
        walk.reset()
        
    else:
        sent_fall = False

    if not fall_detected and walking is not None:
        features = compute_features(list(walking), fps=30)
        print(features)
        features = {
            "elderyUserId": 1,
            "stride_mean": features["stride_mean"],
            "stride_std": features["stride_std"],
            "velocity": features["velocity"]
        }
        #stride_sender.send(features)
        
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    

cap.release()
cv2.destroyAllWindows()
print("Fall detection stopped.")
"""

class FallDetectionWorker(threading.Thread):
    
    def __init__(self, base_url=None, video_source=None):
        super().__init__()
        self._stop = threading.Event()
        self.daemon = True
        
        # 1. 경로 및 API 설정
        # BASE_DIR을 현재 파일 경로가 아닌, 프로젝트 구조에 맞게 다시 정의
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        
        self.model_path = self.BASE_DIR / "models" / "best_fall_model.pth"
        self.scaler_path = self.BASE_DIR / "src" / "scaler.save" # 실제 경로에 맞게 조정 필요
        
        self.fall_api_path = base_url + "/api/events/fall-detection"
        self.stride_api_path = base_url + "/api/events/features"
        
        # 2. 모듈 인스턴스화
        self.detector = Fall_Detector(model_path=self.model_path, scaler_path=self.scaler_path, device='cpu')
        self.extractor = PoseExtractor()
        self.fall_sender = Sender(url=self.fall_api_path)
        self.stride_sender = Sender(url=self.stride_api_path)
        self.walk = WalkingDetector()
        
        # 3. 비디오 캡처 설정
        self.cap = cv2.VideoCapture(video_source)
        if not self.cap.isOpened():
            print(f"Error: Unable to open video source at {video_source}.")
            self._stop.set() # 에러 발생 시 스레드 실행 방지
            
        print("FallDetectionWorker initialized.")
        
    def run(self):
        if self._stop.is_set():
            return
            
        print("[FallWorker] Starting fall detection loop!")

        sent_fall = False
        missing_count = 0

        while not self._stop.is_set():
            ret, frame = self.cap.read()
            if not ret:
                print("[FallWorker] Error: Unable to read frame. Restarting stream...")
                # 스트림 재연결 시도 로직 (필요 시 추가)
                time.sleep(1)
                continue
            
            # --- 1. 키포인트 추출 및 사람 감지 ---
            keypoints = self.extractor.extract_keypoints(frame)
            
            if not self.walk.detect_person(keypoints) or keypoints is None:
                missing_count += 1
                if missing_count >= 10:
                    self.detector.buffer.clear()
                    self.walk.reset()
                    sent_fall = False
                continue
            else:
                missing_count = 0
            
            # --- 2. 상태 업데이트 ---
            walking = self.walk.update(keypoints)
            self.detector.update_sequence(keypoints)
            
            # --- 3. 낙상 예측 ---
            fall_detected, fall_prob = self.detector.predict()
            
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            
            # --- 4. 낙상 감지 시 처리 ---
            if fall_detected:
                if not sent_fall:
                    data = {
                        "elderlyUserId": 4,
                        "fall_prob": fall_prob,
                        "fall_detected": fall_detected,
                        "detectedAt": current_time
                    }
                    self.fall_sender.send(data) # 실제 전송 로직 활성화
                    print(f"[FallWorker] 🚨 Fall detected! Prob: {fall_prob:.2f}. Data prepared: {data}")
                    sent_fall = True
                
                self.walk.reset()
                
            # --- 5. 보행 분석 (낙상 미감지 시) ---
            elif walking is not None: # fall_detected == False
                features = compute_features(list(walking), fps=30)
                
                # features 딕셔너리가 유효한지 확인하고 전송
                if "stride_mean" in features:
                    stride_features = {
                        "elderlyUserId": 4,
                        "stride_mean": features["stride_mean"],
                        "stride_std": features["stride_std"],
                        "velocity": features["velocity"]
                    }
                    self.stride_sender.send(stride_features) # 실제 전송 로직 활성화
                    print(f"[FallWorker] Walking analysis: mean: {features["stride_mean"]:.2f} Velocity: {features['velocity']:.2f}")
                sent_fall = False
            # cv2.waitKey는 GUI가 필요하며 스레드 내에서는 생략하거나 최소화해야 합니다.
            # 하지만 영상 스트리밍 속도 조절을 위해 time.sleep()을 사용할 수 있습니다.
            # time.sleep(0.01) # 프레임 처리 속도 조절 (필요 시)

        # 루프 종료 후 정리 작업
        self.cap.release()
        print("[FallWorker] Fall detection thread stopped.")

    def stop(self):
        self._stop.set()
        
    def join(self, timeout=None):
        self.stop()
        super().join(timeout)