"""
@Author: obstacle
@Time: 20/01/25 15:16
@Description:  
"""
import time
import threading
from tasks import add


class Producer:
    def __init__(self, interval=5):
        self.interval = interval

    def produce_task(self):
        while True:
            result = add.apply_async((10, 20))
            print(f"Task produced: {result}")
            time.sleep(self.interval)

    def start(self):
        producer_thread = threading.Thread(target=self.produce_task)
        producer_thread.daemon = True  # 守护线程
        producer_thread.start()
