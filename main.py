from fall_detect.fall_detector import FallDetectionWorker
from conversation.chatbot import ChatBot
from depression_measure import depressionProcessor
from springsocket import SpringData
from fall_detect.sender import Sender
import queue
import time
import threading

BASE_URL = "http://10.138.18.185:8080"
VIDEO_URL = "http://10.138.18.178:8080/?action=stream"
WEB_SERVER_URL = "ws://10.138.18.185:8080"

def HElloCare():
    sender = Sender(url=BASE_URL + "/api/events/conversation")
    fall_detect = FallDetectionWorker(base_url=BASE_URL, video_source=VIDEO_URL)
    chatbot = ChatBot(sender=sender)
    depression = depressionProcessor(queue.Queue(), url=BASE_URL)
    spring_remind = SpringData(chatbot.llm.reply_queue, depression.depression_queue, url = WEB_SERVER_URL + "/ws/remind")
    #spring_depression = SpringData(chatbot.llm.reply_queue, depression.depression_queue, url = WEB_SERVER_URL + "/ws/depression")
    #spring_remind = SpringData(host = "0.0.0.0", port = 8000, replyqueue = chatbot.llm.reply_queue, depression_queue = depression.depression_queue)
    all_workers = [
        chatbot,      # ChatBot (내부 4개 스레드 시작)
        fall_detect,         # 낙상 감지 및 보행 분석
        depression,   # 우울증 분석
        spring_remind,
        #spring_depression # 웹소켓 리스너
    ]
    
    # 3. 모든 스레드 시작
    print("--- 모든 서비스 워커 스레드 시작 중 ---")
    for worker in all_workers:
        # ChatBot은 내부적으로 start()가 모든 서브 스레드를 실행합니다.
        # FallWorker, DepressionProcessor, SpingData는 Thread를 상속받거나 내부에 Thread를 관리합니다.
        worker.start()
        print(f"✅ {worker.__class__.__name__} 스레드 시작 완료.")
        
    # 4. 메인 루프 유지 및 종료 처리
    try:
        print("\n--- 시스템 실행 중. Ctrl+C로 종료하세요. ---")
        # 주요 스레드 중 하나라도 실행 중이면 메인 스레드는 대기
        while any(worker.is_alive() for worker in all_workers):
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n--- 사용자 요청: 서비스 종료 시작 ---")
        
    finally:
        # 5. 모든 스레드 안전하게 종료 (Stop)
        # 🚨 ChatBot 내부에 stop_event를 설정하는 것이 가장 중요합니다.
        
        # ChatBot의 stop_event를 설정하여 내부 STT/LLM/TTS/AudioRecorder 스레드를 먼저 종료 요청
        chatbot.stop_event.set()
        
        for worker in all_workers:
            if hasattr(worker, 'stop'):
                worker.stop()
            if hasattr(worker, 'thread') and worker.thread:
                # SpingData처럼 내부 스레드를 쓰는 경우를 대비
                worker.thread.join(timeout=5)
            elif isinstance(worker, threading.Thread):
                worker.join(timeout=5) # Thread 상속 클래스 종료 대기
            
        print("--- 모든 서비스가 안전하게 종료되었습니다. ---")
        
        
if __name__ == "__main__":
    HElloCare()