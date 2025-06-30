from abc import ABC, abstractmethod
import requests
from selenium.webdriver.common.by import By

class ChatProvider(ABC):
    @abstractmethod
    def fetch_messages(self):
        pass

class BigoLiveXHRChatProvider(ChatProvider):
    def __init__(self, url, headers=None):
        self.url = url
        self.headers = headers or {}
        self.last_msg_id = None
    def fetch_messages(self):
        resp = requests.get(self.url, headers=self.headers)
        data = resp.json()
        new_msgs = []
        for msg in data.get('messages', []):
            msg_id = msg.get('id')
            if self.last_msg_id is None or msg_id > self.last_msg_id:
                new_msgs.append(msg)
        if new_msgs:
            self.last_msg_id = new_msgs[-1]['id']
        return new_msgs

class BigoLiveDOMChatProvider(ChatProvider):
    def __init__(self, driver, selector):
        self.driver = driver
        self.selector = selector
        self.prev_dom_msgs = []
    def fetch_messages(self):
        elements = self.driver.find_elements(By.CSS_SELECTOR, self.selector)
        messages = [el.text.strip() for el in elements if el.text.strip()]
        new_msgs = [msg for msg in messages if msg not in self.prev_dom_msgs]
        if new_msgs:
            self.prev_dom_msgs = messages.copy()
        return new_msgs
