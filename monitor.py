import requests
from lxml import html
import schedule
import time
import smtplib
from email.mime.text import MIMEText
from config import Config
import logging
import yaml
from xpath_finder import XPathFinder
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class WebsiteMonitor:
    def __init__(self, url):
        self.url = url
        self.xpath_data = self.load_xpaths()
        self.driver = None
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # 初始化Selenium
        self.init_selenium()
        
    def init_selenium(self):
        """初始化Selenium WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logging.info("Selenium WebDriver初始化成功")
        except Exception as e:
            logging.error(f"初始化Selenium失败: {str(e)}")
            
    def load_xpaths(self):
        """加载XPath配置"""
        with open('xpath_store.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
            
    def save_xpaths(self):
        """保存XPath配置"""
        with open('xpath_store.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(self.xpath_data, f, allow_unicode=True)
            
    def get_page_content(self):
        """获取页面内容"""
        try:
            if not self.driver:
                self.init_selenium()
                
            logging.info(f"正在加载页面: {self.url}")
            self.driver.get(self.url)
            
            # 等待页面加载完成（等待body元素出现）
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 等待特定元素出现（比如等待Sell按钮）
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Sell')]"))
                )
                logging.info("关键元素已加载")
            except Exception as e:
                logging.warning(f"等待关键元素超时: {str(e)}")
            
            # 额外等待以确保JavaScript完全执行
            time.sleep(10)  # 增加等待时间
            
            logging.info("页面加载完成")
            page_source = self.driver.page_source
            
            # 打印页面内容以供调试
            logging.debug(f"页面内容: {page_source[:500]}...")
            
            # 检查页面源码中是否包含关键内容
            if 'Sell' in page_source:
                logging.info("页面源码中找到'Sell'按钮")
            else:
                logging.warning("页面源码中未找到'Sell'按钮")
            
            return html.fromstring(page_source)
        except Exception as e:
            logging.error(f"获取页面失败: {str(e)}")
            return None
            
    def find_new_xpath(self, tree, old_content):
        """查找新的XPath"""
        finder = XPathFinder(tree)
        element = finder.find_similar_element(old_content)
        if element is not None:
            return finder.generate_xpath(element)
        return None
        
    def send_notification(self, changes):
        """发送变更通知"""
        try:
            message = "监控到以下变化:\n\n"
            for change in changes:
                message += f"描述: {change['description']}\n"
                message += f"原内容: {change['old_content']}\n"
                message += f"新内容: {change['new_content']}\n"
                if change.get('new_xpath'):
                    message += f"新XPath: {change['new_xpath']}\n"
                message += "-" * 50 + "\n"
                
            msg = MIMEText(message)
            msg['Subject'] = '网站内容变化通知'
            msg['From'] = Config.SMTP_USER
            msg['To'] = Config.RECIPIENT_EMAIL
            
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.send_message(msg)
                
            logging.info("通知邮件发送成功")
        except Exception as e:
            logging.error(f"发送通知失败: {str(e)}")
            
    def check_changes(self):
        tree = self.get_page_content()
        if tree is None:
            return
            
        changes = []
        
        for xpath_item in self.xpath_data['xpaths']:
            try:
                elements = tree.xpath(xpath_item['path'])
                current_content = elements[0].text_content().strip() if elements else None
                
                # 首次运行
                if not xpath_item['content']:
                    xpath_item['content'] = current_content
                    continue
                    
                # XPath失效或内容变化
                if current_content is None or current_content != xpath_item['content']:
                    change = {
                        'description': xpath_item['description'],
                        'old_content': xpath_item['content'],
                        'new_content': current_content
                    }
                    
                    # 如果XPath失效,尝试��找的XPath
                    if current_content is None:
                        new_xpath = self.find_new_xpath(tree, xpath_item['content'])
                        if new_xpath:
                            change['new_xpath'] = new_xpath
                            xpath_item['path'] = new_xpath
                            # 使用新XPath获取内容
                            elements = tree.xpath(new_xpath)
                            change['new_content'] = elements[0].text_content().strip() if elements else None
                            
                    changes.append(change)
                    xpath_item['content'] = change['new_content']
                    
            except Exception as e:
                logging.error(f"处理XPath {xpath_item['path']} 时出错: {str(e)}")
                
        if changes:
            self.send_notification(changes)
            self.save_xpaths()
            
    def start(self):
        logging.info("开始监控...")
        self.check_changes()  # 首次运行
        schedule.every(10).minutes.do(self.check_changes)
        
        while True:
            schedule.run_pending()
            time.sleep(1)

    def check_xpath_exists(self, tree, xpath):
        """检查XPath是否能匹配到元素，返回匹配到的内容"""
        try:
            # 确保XPath中的引号格式正确
            xpath = xpath.replace('"', "'")
            logging.info(f"正在检查XPath: {xpath}")
            
            # 先尝试使用Selenium直接查找
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                content = element.text.strip() or element.get_attribute('textContent').strip()
                logging.info(f"Selenium直接找到元素，内容: {content}")
                return True, content
            except Exception as e:
                logging.warning(f"Selenium直接查找失败: {str(e)}")
            
            # 如果Selenium直接查找失败，使用lxml解析
            elements = tree.xpath(xpath)
            
            if elements:
                logging.info(f"XPath匹配成功，找到{len(elements)}个元素")
                # 获取元素内容
                content = elements[0].text_content().strip() if hasattr(elements[0], 'text_content') else str(elements[0])
                logging.info(f"匹配到的内容: {content}")
                return True, content
            else:
                logging.info(f"XPath未匹配到任何元素")
                return False, "未匹配"
                
        except Exception as e:
            logging.error(f"检查XPath时出错: {str(e)}")
            return False, f"错误: {str(e)}"

    def check_all_xpath_status(self):
        """检查所有XPath的状态"""
        try:
            tree = self.get_page_content()
            if tree is None:
                logging.error("无法获取页面内容")
                return [(False, "页面获取失败")] * len(self.xpath_data['xpaths'])
            
            statuses = []
            for xpath_item in self.xpath_data['xpaths']:
                logging.info(f"检查XPath项: {xpath_item['description']}")
                status, content = self.check_xpath_exists(tree, xpath_item['path'])
                statuses.append((status, content))
                
                # 如果状态发生变化，发送通知
                if 'last_status' not in xpath_item:
                    xpath_item['last_status'] = status
                    xpath_item['last_content'] = content
                elif xpath_item['last_status'] != status or xpath_item['last_content'] != content:
                    self.send_status_notification(
                        xpath_item['description'], 
                        xpath_item['last_status'],
                        status,
                        xpath_item['last_content'],
                        content
                    )
                    xpath_item['last_status'] = status
                    xpath_item['last_content'] = content
                    
            logging.info(f"所有XPath检查完成，状态: {statuses}")
            return statuses
        except Exception as e:
            logging.error(f"检查XPath状态时出错: {str(e)}")
            return [(False, f"错误: {str(e)}")] * len(self.xpath_data['xpaths'])

    def send_status_notification(self, description, old_status, new_status, old_content, new_content):
        """发送状态变化通知"""
        try:
            message = f"XPath状态变化通知:\n\n"
            message += f"描述: {description}\n"
            message += f"原状态: {'匹配' if old_status else '未匹配'}\n"
            message += f"新状态: {'匹配' if new_status else '未匹配'}\n"
            message += f"原内容: {old_content}\n"
            message += f"新内容: {new_content}\n"
            
            msg = MIMEText(message)
            msg['Subject'] = 'XPath状态变化通知'
            msg['From'] = Config.SMTP_USER
            msg['To'] = Config.RECIPIENT_EMAIL
            
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.send_message(msg)
                
            logging.info(f"状态变化通知发送成功: {description}")
        except Exception as e:
            logging.error(f"发送状态变化通知失败: {str(e)}")

    def __del__(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

if __name__ == "__main__":
    url = input("请输入要监控的网址: ")
    monitor = WebsiteMonitor(url)
    monitor.start() 