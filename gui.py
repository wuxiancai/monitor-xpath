import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import yaml
import threading
import time
from monitor import WebsiteMonitor
import logging

class MonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("XPath监控器")
        self.root.geometry("1100x800")  # 加宽窗口以适应新列
        
        # 创建监控状态变量
        self.is_monitoring = False
        self.monitor_thread = None
        self.check_interval = 600  # 10分钟检查一次
        
        # 创建主框架
        self.create_main_frame()
        
        # 加载默认配置
        self.load_config()
        
    def create_main_frame(self):
        # URL输入框
        url_frame = ttk.Frame(self.root)
        url_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(url_frame, text="监控网址:").pack(side=tk.LEFT, padx=(0, 5))
        self.url_entry = ttk.Entry(url_frame, width=100)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 设置默认URL
        default_url = "https://polymarket.com/event/bitcoin-above-100000-on-december-20?tid=1734657960491"
        self.url_entry.insert(0, default_url)
        
        # 控制按钮
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.start_btn = ttk.Button(btn_frame, text="开始监控", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="停止监控", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="重载配置", command=self.load_config).pack(side=tk.LEFT, padx=5)
        
        # XPath配置表格
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建表格
        columns = ("描述", "XPath", "上次内容", "状态")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        # 设置列标题和宽度
        self.tree.heading("描述", text="描述")
        self.tree.heading("XPath", text="XPath")
        self.tree.heading("上次内容", text="上次内容")
        self.tree.heading("状态", text="状态")
        
        self.tree.column("描述", width=150)
        self.tree.column("XPath", width=300)
        self.tree.column("上次内容", width=100)
        self.tree.column("状态", width=50)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 双击编辑功能
        self.tree.bind("<Double-1>", self.edit_item)
        
        # 日志显示区域
        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置日志处理
        self.setup_logging()
        
    def setup_logging(self):
        # 创建自定义日志处理器
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
                
            def emit(self, record):
                msg = self.format(record)
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.see(tk.END)
                
        # 配置日志
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(gui_handler)
        
    def load_config(self):
        try:
            with open('xpath_store.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # 清空现有项
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            # 添加配置项
            for xpath in config['xpaths']:
                self.tree.insert('', tk.END, values=(
                    xpath['description'],
                    xpath['path'],
                    xpath['content'],
                    "未匹配"
                ))
                
            logging.info("配置加载成功")
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {str(e)}")
            logging.error(f"加载配置失败: {str(e)}")
            
    def save_config(self):
        try:
            config = {'xpaths': []}
            
            # 获取所有配置项
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                config['xpaths'].append({
                    'description': values[0],
                    'path': values[1],
                    'content': values[2] if values[2] else ''
                })
                
            # 保存到文件
            with open('xpath_store.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True)
                
            logging.info("配置保存成功")
            messagebox.showinfo("成功", "配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")
            logging.error(f"保存配置失败: {str(e)}")
            
    def edit_item(self, event):
        # 获取选中的项
        item = self.tree.selection()[0]
        column = self.tree.identify_column(event.x)
        
        # 创建编辑窗口
        dialog = tk.Toplevel(self.root)
        dialog.title("编辑项")
        
        # 获取当前值
        values = self.tree.item(item)['values']
        
        # 创建输入框
        ttk.Label(dialog, text="描述:").grid(row=0, column=0, padx=5, pady=5)
        desc_entry = ttk.Entry(dialog)
        desc_entry.insert(0, values[0])
        desc_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="XPath:").grid(row=1, column=0, padx=5, pady=5)
        xpath_entry = ttk.Entry(dialog)
        xpath_entry.insert(0, values[1])
        xpath_entry.grid(row=1, column=1, padx=5, pady=5)
        
        def save_changes():
            # 更新表格
            self.tree.item(item, values=(
                desc_entry.get(),
                xpath_entry.get(),
                values[2],
                values[3]
            ))
            dialog.destroy()
            
        ttk.Button(dialog, text="保存", command=save_changes).grid(row=2, column=0, columnspan=2, pady=10)
        
    def start_monitoring(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入监控网址")
            return
            
        self.is_monitoring = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 创建监控器实例
        self.monitor = WebsiteMonitor(url)
        
        # 立即执行第一次检查
        try:
            statuses = self.monitor.check_all_xpath_status()
            for i, status_info in enumerate(statuses):
                self.update_xpath_status(i, status_info)
        except Exception as e:
            logging.error(f"初始检查时出错: {str(e)}")
        
        # 创建并启动监控线程
        self.monitor_thread = threading.Thread(
            target=self.run_monitor,
            daemon=True
        )
        self.monitor_thread.start()
        
        # 启动定时检查
        self.schedule_next_check()
        
        logging.info("开始监控...")
        
    def stop_monitoring(self):
        self.is_monitoring = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        logging.info("停止监控")
        
    def schedule_next_check(self):
        """安排下一次检查"""
        if self.is_monitoring:
            try:
                statuses = self.monitor.check_all_xpath_status()
                for i, status_info in enumerate(statuses):
                    self.update_xpath_status(i, status_info)
            except Exception as e:
                logging.error(f"定时检查时出错: {str(e)}")
            finally:
                # 安排下一次检查
                self.root.after(self.check_interval * 1000, self.schedule_next_check)
        
    def update_xpath_status(self, index, status_info):
        """更新XPath状态显示"""
        try:
            item = self.tree.get_children()[index]
            values = list(self.tree.item(item)['values'])
            status, content = status_info
            values[3] = content  # 直接显示匹配到的内容
            self.tree.item(item, values=values)
        except Exception as e:
            logging.error(f"更新状态显示失败: {str(e)}")
            
    def run_monitor(self):
        """监控线程的执行函数"""
        try:
            while self.is_monitoring:
                time.sleep(self.check_interval)  # 先等待间隔时间
                if not self.is_monitoring:  # 再次检查是否还在监控
                    break
                try:
                    # 获取所有XPath的状态
                    statuses = self.monitor.check_all_xpath_status()
                    # 在主线程中更新UI
                    for i, status_info in enumerate(statuses):
                        self.root.after(0, self.update_xpath_status, i, status_info)
                except Exception as e:
                    logging.error(f"检查更新时出错: {str(e)}")
        except Exception as e:
            logging.error(f"监控线程出错: {str(e)}")
            self.root.after(0, self.handle_monitor_error)
            
    def handle_monitor_error(self):
        """处理监控错误"""
        self.stop_monitoring()
        messagebox.showerror("错误", "监控过程出错，已停止监控")

def main():
    root = tk.Tk()
    app = MonitorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 