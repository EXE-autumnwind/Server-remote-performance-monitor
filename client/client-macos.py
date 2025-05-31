import socket
import json
import tkinter as tk
from tkinter import ttk
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import configparser
import os
from matplotlib.animation import FuncAnimation
import matplotlib
matplotlib.use('TkAgg')

class ServerMonitorApp:
    CONFIG_FILE = "codewaves.stats.ipcfg"
    
    def __init__(self, root):
        self.root = root
        self.root.title("服务器监控工具")
        self.root.geometry("1300x850")
        if os.name == 'posix':
            self.root.attributes('-fullscreen', False)
            self.root.overrideredirect(False)
            self.root.configure(bg='#FFFFFF')
        else:
            self.root.configure(bg='#222222')
        self.data = {
            'cpu': {'percent': 0, 'per_cpu': [], 'freq': 0},
            'memory': {'used': 0, 'total': 0, 'percent': 0},
            'network': {'bytes_sent': 0, 'bytes_recv': 0, 'upload_speed': 0, 'download_speed': 0}
        }
        self.history = {
            'cpu': [],
            'memory': [],
            'network': {'upload': [], 'download': []}
        }
        self.config = configparser.ConfigParser()
        self.load_config()
        if os.name == 'posix':
            self.font = ('SF Pro Text', 10)
            self.title_font = ('SF Pro Display', 16, 'bold')
        else:
            self.font = ('Microsoft YaHei', 10)
            self.title_font = ('Microsoft YaHei', 16, 'bold')
        self.create_main_layout()
        self.create_cpu_page()
        self.create_memory_page()
        self.create_network_page()
        self.create_settings_page()
        self.show_page("cpu")
        self.running = True
        self.thread = threading.Thread(target=self.update_data)
        self.thread.daemon = True
        self.thread.start()
        self.init_all_charts()
        self.ani_cpu = FuncAnimation(
            self.cpu_fig,
            self.update_cpu_chart,
            interval=500,
            cache_frame_data=False,
            save_count=100
        )
        self.ani_mem = FuncAnimation(
            self.mem_fig,
            self.update_mem_chart,
            interval=500,
            cache_frame_data=False,
            save_count=100
        )
        self.ani_net = FuncAnimation(
            self.net_fig,
            self.update_net_chart,
            interval=500,
            cache_frame_data=False,
            save_count=100
        )
        self.update_ui()

    def init_all_charts(self):
        self.cpu_ax1.clear()
        self.cpu_ax2.clear()
        self.cpu_ax1.set_facecolor('#333333')
        self.cpu_ax2.set_facecolor('#333333')
        self.cpu_ax1.set_ylabel('总使用率 (%)', color='white')
        self.cpu_ax2.set_ylabel('使用率 (%)', color='white')
        self.cpu_ax1.set_ylim(0, 100)
        self.cpu_ax2.set_ylim(0, 100)
        self.mem_ax.clear()
        self.mem_ax.set_facecolor('#333333')
        self.mem_ax.set_ylabel('内存 (GB)', color='white')
        self.mem_ax.set_xlabel('时间', color='white')
        self.net_ax.clear()
        self.net_ax.set_facecolor('#333333')
        self.net_ax.set_ylabel('速度 (KB/s)', color='white')
        for ax in [self.cpu_ax1, self.cpu_ax2, self.mem_ax, self.net_ax]:
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
        self.cpu_canvas.draw()
        self.mem_canvas.draw()
        self.net_canvas.draw()

    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            self.config.read(self.CONFIG_FILE)
            self.server_host = self.config.get('SERVER', 'host', fallback="localhost")
            self.server_port = self.config.getint('SERVER', 'port', fallback=5021)
        else:
            self.server_host = "localhost"
            self.server_port = 5021

    def save_config(self):
        self.config['SERVER'] = {
            'host': self.server_host,
            'port': str(self.server_port)
        }
        with open(self.CONFIG_FILE, 'w') as f:
            self.config.write(f)

    def create_main_layout(self):
        self.nav_frame = tk.Frame(self.root, bg='#333333', width=120)
        self.nav_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.nav_frame.pack_propagate(False)
        self.title_label = tk.Label(
            self.nav_frame,
            text="服务器监控工具",
            bg='#333333',
            fg='white',
            font=self.title_font,
            wraplength=120
        )
        self.title_label.pack(pady=30)
        self.buttons = {}
        for i, (text, page) in enumerate([("CPU", "cpu"), ("内存", "memory"), ("网络", "network"), ("设置", "settings")], 1):
            btn_frame = tk.Frame(self.nav_frame, bg='#333333')
            btn_frame.pack(pady=15)
            self.buttons[page] = {
                'frame': btn_frame,
                'indicator': tk.Frame(btn_frame, bg='#333333', width=5, height=40, bd=0, highlightthickness=0),
                'button': tk.Button(
                    btn_frame,
                    text=text,
                    bg='#0066CC',
                    fg='white',
                    font=('Microsoft YaHei', 12),
                    width=10,
                    relief=tk.FLAT,
                    command=lambda p=page: self.show_page(p)
                )
            }
            self.buttons[page]['indicator'].pack(side=tk.LEFT, padx=(5,0))
            self.buttons[page]['button'].pack(side=tk.LEFT)
        self.content_frame = tk.Frame(self.root, bg='#222222')
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.page_title = tk.Label(
            self.content_frame,
            text="",
            bg='#222222',
            fg='white',
            font=self.title_font
        )
        self.page_title.pack(pady=20)
        self.page_container = tk.Frame(self.content_frame, bg='#222222')
        self.page_container.pack(fill=tk.BOTH, expand=True)
        self.status_var = tk.StringVar()
        self.status_var.set("正在连接服务器...")
        self.status_bar = tk.Label(
            self.content_frame,
            textvariable=self.status_var,
            bg='#222222',
            fg='white',
            font=self.font
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def show_page(self, page):
        for btn in self.buttons.values():
            btn['button'].config(bg='#0066CC')
            btn['indicator'].config(bg='#333333')
        self.buttons[page]['button'].config(bg='#0099FF')
        titles = {
            "cpu": "CPU",
            "memory": "内存",
            "network": "网络",
            "settings": "设置"
        }
        self.page_title.config(text=titles[page])

        for widget in self.page_container.winfo_children():
            widget.pack_forget()

        target_page = None
        if page == "cpu":
            target_page = self.cpu_page
            self.is_cpu_current = True
            self.is_memory_current = False
            self.is_network_current = False
        elif page == "memory":
            target_page = self.memory_page
            self.is_cpu_current = False
            self.is_memory_current = True
            self.is_network_current = False
        elif page == "network":
            target_page = self.network_page
            self.is_cpu_current = False
            self.is_memory_current = False
            self.is_network_current = True
        elif page == "settings":
            target_page = self.settings_page
            self.is_cpu_current = False
            self.is_memory_current = False
            self.is_network_current = False

        if target_page:
            target_page.pack(fill=tk.BOTH, expand=True)
            target_page.lower()
            self.fade_in(target_page)

        self.current_page = page

        if page == "cpu" and hasattr(self, 'ani_cpu'):
            self.ani_cpu.event_source.start()
        elif page == "memory" and hasattr(self, 'ani_mem'):
            self.ani_mem.event_source.start()
        elif page == "network" and hasattr(self, 'ani_net'):
            self.ani_net.event_source.start()

    def fade_in(self, widget, count=0):
        max_count = 10
        if count < max_count:
            widget.lift()
            self.root.after(50, self.fade_in, widget, count + 1)

    def create_cpu_page(self):
        self.cpu_page = tk.Frame(self.page_container, bg='#222222')
        top_frame = tk.Frame(self.cpu_page, bg='#222222')
        top_frame.pack(fill=tk.X, padx=20, pady=10)
        overall_frame = tk.LabelFrame(
            top_frame, 
            text="概览", 
            bg='#333333', 
            fg='white',
            font=self.font,
            padx=10,
            pady=10,
            bd=2,
            relief=tk.GROOVE
        )
        overall_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cpu_percent_var = tk.StringVar()
        self.cpu_freq_var = tk.StringVar()
        tk.Label(
            overall_frame, 
            text="总占用:", 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        tk.Label(
            overall_frame, 
            textvariable=self.cpu_percent_var, 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        tk.Label(
            overall_frame, 
            text="当前频率:", 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        tk.Label(
            overall_frame, 
            textvariable=self.cpu_freq_var, 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        chart_frame = tk.LabelFrame(
            self.cpu_page, 
            text="核心占用率", 
            bg='#333333', 
            fg='white',
            font=self.font,
            padx=10,
            pady=10,
            bd=2,
            relief=tk.GROOVE
        )
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        plt.rcParams['font.family'] = 'Microsoft YaHei'
        self.cpu_fig, (self.cpu_ax1, self.cpu_ax2) = plt.subplots(2, 1, figsize=(10, 6), facecolor='#333333', gridspec_kw={'height_ratios': [1, 2]})
        self.cpu_ax1.set_facecolor('#333333')
        self.cpu_ax2.set_facecolor('#333333')
        
        self.cpu_canvas = FigureCanvasTkAgg(self.cpu_fig, master=chart_frame)
        self.cpu_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def create_memory_page(self):
        self.memory_page = tk.Frame(self.page_container, bg='#222222')
    
        top_frame = tk.Frame(self.memory_page, bg='#222222')
        top_frame.pack(fill=tk.X, padx=20, pady=10)

        info_frame = tk.LabelFrame(
            top_frame,
            text="内存使用情况",
            bg='#333333',
            fg='white',
            font=self.font,
            padx=10,
            pady=10,
            bd=2,
            relief=tk.GROOVE
        )
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
        self.mem_percent_var = tk.StringVar()
        self.mem_used_var = tk.StringVar()
        self.mem_total_var = tk.StringVar()
    
        tk.Label(
            info_frame, 
            text="占用率:", 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        tk.Label(
            info_frame, 
            textvariable=self.mem_percent_var, 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
    
        tk.Label(
            info_frame, 
            text="已使用:", 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        tk.Label(
            info_frame, 
            textvariable=self.mem_used_var, 
            bg='#333333',
            fg='white',
            font=self.font
        ).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        tk.Label(
            info_frame, 
            text="总内存:", 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        tk.Label(
            info_frame, 
            textvariable=self.mem_total_var, 
            bg='#333333',
            fg='white',
            font=self.font
        ).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        chart_frame = tk.LabelFrame(
            self.memory_page, 
            text="内存使用趋势", 
            bg='#333333', 
            fg='white',
            font=self.font,
            padx=10,
            pady=10,
            bd=2,
            relief=tk.GROOVE
        )
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.mem_fig, self.mem_ax = plt.subplots(figsize=(10, 5), facecolor='#333333')
        
        self.mem_canvas = FigureCanvasTkAgg(self.mem_fig, master=chart_frame)
        self.mem_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_network_page(self):
        self.network_page = tk.Frame(self.page_container, bg='#222222')
        
        top_frame = tk.Frame(self.network_page, bg='#222222')
        top_frame.pack(fill=tk.X, padx=20, pady=10)
        
        info_frame = tk.LabelFrame(
            top_frame, 
            text="网络流量", 
            bg='#333333', 
            fg='white',
            font=self.font,
            padx=10,
            pady=10,
            bd=2,
            relief=tk.GROOVE
        )
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.upload_var = tk.StringVar()
        self.download_var = tk.StringVar()
        
        tk.Label(
            info_frame, 
            text="上传速度:", 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        tk.Label(
            info_frame, 
            textvariable=self.upload_var, 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        tk.Label(
            info_frame, 
            text="下载速度:", 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        tk.Label(
            info_frame, 
            textvariable=self.download_var, 
            bg='#333333', 
            fg='white',
            font=self.font
        ).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        chart_frame = tk.LabelFrame(
            self.network_page, 
            text="网络传输趋势", 
            bg='#333333', 
            fg='white',
            font=self.font,
            padx=10,
            pady=10,
            bd=2,
            relief=tk.GROOVE
        )
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.net_fig, self.net_ax = plt.subplots(figsize=(10, 5), facecolor='#333333')
        self.net_ax.set_facecolor('#333333')
        
        self.net_canvas = FigureCanvasTkAgg(self.net_fig, master=chart_frame)
        self.net_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def create_settings_page(self):
        self.settings_page = tk.Frame(self.page_container, bg='#222222')
        
        form_frame = tk.LabelFrame(
            self.settings_page, 
            text="服务器设置", 
            bg='#333333', 
            fg='white',
            font=self.font,
            padx=10,
            pady=10,
            bd=2,
            relief=tk.GROOVE
        )
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        host_frame = tk.Frame(form_frame, bg='#333333')
        host_frame.pack(fill=tk.X, pady=5)
        tk.Label(
            host_frame, 
            text="服务器地址:", 
            bg='#333333', 
            fg='white',
            font=self.font
        ).pack(side=tk.LEFT, padx=(0, 10))
        self.host_entry = tk.Entry(host_frame, bg='#555555', fg='white', insertbackground='white')
        self.host_entry.insert(0, self.server_host)
        self.host_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        port_frame = tk.Frame(form_frame, bg='#333333')
        port_frame.pack(fill=tk.X, pady=5)
        tk.Label(
            port_frame, 
            text="服务器端口:", 
            bg='#333333', 
            fg='white',
            font=self.font
        ).pack(side=tk.LEFT, padx=(5, 10))
        self.port_entry = tk.Entry(port_frame, bg='#555555', fg='white', insertbackground='white')
        self.port_entry.insert(0, str(self.server_port))
        self.port_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        btn_frame = tk.Frame(form_frame, bg='#333333')
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        test_btn = tk.Button(
            btn_frame,
            text="测试连接",
            bg='#0066CC',
            fg='white',
            font=self.font,
            command=self.test_connection
        )
        test_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        save_btn = tk.Button(
            btn_frame,
            text="保存设置",
            bg='#0066CC',
            fg='white',
            font=self.font,
            command=self.save_settings
        )
        save_btn.pack(side=tk.RIGHT)
    
    def save_settings(self):
        try:
            self.server_host = self.host_entry.get()
            self.server_port = int(self.port_entry.get())
            self.save_config()
            self.status_var.set("设置已保存")
            
            if self.thread.is_alive():
                self.running = False
                self.thread.join(timeout=1)
            
            self.running = True
            self.thread = threading.Thread(target=self.update_data)
            self.thread.daemon = True
            self.thread.start()
            
        except ValueError:
            self.status_var.set("错误: 端口必须是数字")
    
    def test_connection(self):
        try:
            host = self.host_entry.get()
            port = int(self.port_entry.get())
            ip = socket.gethostbyname(host)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((ip, port))
                self.status_var.set("连接测试成功!")
        except Exception as e:
            self.status_var.set(f"连接测试失败: {str(e)}")
    
    def update_data(self):
        last_update_time = None
        last_bytes_sent = 0
        last_bytes_recv = 0
        
        while self.running:
            try:
                ip = socket.gethostbyname(self.server_host)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((ip, self.server_port))
                    self.status_var.set(f"已连接到 {self.server_host} ({ip}):{self.server_port}")
                    
                    buffer = b''
                    while self.running:
                        data = s.recv(4096)
                        if not data:
                            break
                            
                        buffer += data
                        while b'\n' in buffer:
                            line, buffer = buffer.split(b'\n', 1)
                            current_time = time.perf_counter()
                            new_data = json.loads(line.decode('utf-8'))
                            
                            current_bytes_sent = new_data['network']['bytes_sent']
                            current_bytes_recv = new_data['network']['bytes_recv']
                            
                            if last_update_time is None:
                                last_update_time = current_time
                                last_bytes_sent = current_bytes_sent
                                last_bytes_recv = current_bytes_recv
                                continue
                            
                            time_elapsed = current_time - last_update_time
                            
                            max_counter = 2**32
                            if current_bytes_sent < last_bytes_sent:
                                sent_diff = (max_counter - last_bytes_sent) + current_bytes_sent
                            else:
                                sent_diff = current_bytes_sent - last_bytes_sent
                            if current_bytes_recv < last_bytes_recv:
                                recv_diff = (max_counter - last_bytes_recv) + current_bytes_recv
                            else:
                                recv_diff = current_bytes_recv - last_bytes_recv
                            
                            if time_elapsed >= 0.1:
                                upload_speed = (sent_diff / 1024) / time_elapsed
                                download_speed = (recv_diff / 1024) / time_elapsed
                                
                                max_speed = 1024 * 1024
                                upload_speed = min(upload_speed, max_speed)
                                download_speed = min(download_speed, max_speed)
                                
                                new_data['network']['upload_speed'] = upload_speed
                                new_data['network']['download_speed'] = download_speed
                        
                            last_update_time = current_time
                            last_bytes_sent = current_bytes_sent
                            last_bytes_recv = current_bytes_recv
                            
                            self.data = new_data
                            self.update_history_data(new_data)
                            
            except (ConnectionRefusedError, ConnectionResetError) as e:
                self.status_var.set(f"连接错误: {str(e)}. 5秒后重试...")
                time.sleep(5)
            except Exception as e:
                self.status_var.set(f"错误: {str(e)}")
            time.sleep(0.5)

    def update_history_data(self, new_data):
        self.history['cpu'].append(new_data['cpu']['percent'])
        if len(self.history['cpu']) > 60:
            self.history['cpu'].pop(0)
        
        self.history['memory'].append(new_data['memory']['used'] / (1024**3))
        if len(self.history['memory']) > 60:
            self.history['memory'].pop(0)
        
        if 'upload_speed' in new_data['network']:
            self.history['network']['upload'].append(new_data['network']['upload_speed'])
            self.history['network']['download'].append(new_data['network']['download_speed'])
            if len(self.history['network']['upload']) > 60:
                self.history['network']['upload'].pop(0)
            if len(self.history['network']['download']) > 60:
                self.history['network']['download'].pop(0)
                    
    def update_mem_chart(self, i):
        if not self.running:
            return []
        artists = []
        mem_data = self.data['memory']
        self.mem_ax.clear()
        if self.history['memory']:
            line2, = self.mem_ax.plot(self.history['memory'], color='#00CC99', linewidth=2)
            self.mem_ax.set_ylabel('内存 (GB)', color='white')
            self.mem_ax.set_xlabel('时间', color='white')
            self.mem_ax.tick_params(colors='white')
            for spine in self.mem_ax.spines.values():
                spine.set_color('white')
            artists.append(line2)
            fill = self.mem_ax.fill_between(range(len(self.history['memory'])), self.history['memory'], color='#90EE90', alpha=0.5)
            artists.append(fill)
            total_memory_gb = mem_data['total'] / (1024 ** 3)
            self.mem_ax.set_ylim(0, total_memory_gb * 1.1)
        if self.is_memory_current:
            self.mem_canvas.draw()
        return artists

    def update_cpu_chart(self, i):
        if not self.running:
            return []
        artists = []
        cpu_data = self.data['cpu']
        self.cpu_ax1.clear()
        self.cpu_ax2.clear()
        if cpu_data['per_cpu']:
            cores = len(cpu_data['per_cpu'])
            self.cpu_ax2.bar(range(cores), cpu_data['per_cpu'], color='#0099FF')
            self.cpu_ax2.set_xticks(range(cores))
            self.cpu_ax2.set_xticklabels([f"Core {i}" for i in range(cores)], color='white')
            self.cpu_ax2.set_ylim(0, 100)
            self.cpu_ax2.set_ylabel('使用率 (%)', color='white')
            self.cpu_ax2.tick_params(colors='white')
            for spine in self.cpu_ax2.spines.values():
                spine.set_color('white')
            artists.extend(self.cpu_ax2.patches)
        if self.history['cpu']:
            line1, = self.cpu_ax1.plot(self.history['cpu'], color='#0099FF', linewidth=2)
            self.cpu_ax1.set_ylim(0, 100)
            self.cpu_ax1.set_ylabel('总使用率 (%)', color='white')
            self.cpu_ax1.tick_params(colors='white')
            for spine in self.cpu_ax1.spines.values():
                spine.set_color('white')
            artists.append(line1)
            fill = self.cpu_ax1.fill_between(range(len(self.history['cpu'])), self.history['cpu'], color='#87CEFA', alpha=0.5)
            artists.append(fill)
        if self.is_cpu_current:
            self.cpu_canvas.draw()
        return artists

    def update_net_chart(self, i):
        if not self.running:
            return []
    
        artists = []
        net_data = self.data['network']
        
        self.net_ax.clear()
        
        upload = net_data.get('upload_speed', 0)
        download = net_data.get('download_speed', 0)
    
        upload_history = self.history['network'].get('upload', [])
        download_history = self.history['network'].get('download', [])
        
        max_value = max(max(upload_history or [0]), max(download_history or [0]), upload, download)
        min_value = min(min(upload_history or [0]), min(download_history or [0]), upload, download) if upload_history and download_history else 0
        
        if max_value >= 1024 * 1024:
            unit = 'GB/s'
            upload /= 1024 * 1024
            download /= 1024 * 1024
            upload_history = [x/(1024 * 1024) for x in upload_history]
            download_history = [x/(1024 * 1024) for x in download_history]
        elif max_value >= 1024:
            unit = 'MB/s'
            upload /= 1024
            download /= 1024
            upload_history = [x/1024 for x in upload_history]
            download_history = [x/1024 for x in download_history]
        elif min_value < 1 and max_value < 1024:
            unit = 'B/s'
            upload_history = [x for x in upload_history]
            download_history = [x for x in download_history]
        else:
            unit = 'KB/s'
            upload /= 1024 if max_value >= 1024 else 1
            download /= 1024 if max_value >= 1024 else 1
            upload_history = [x/1024 if max_value >= 1024 else x for x in upload_history]
            download_history = [x/1024 if max_value >= 1024 else x for x in download_history]
        
        if upload_history and download_history:
            line3, = self.net_ax.plot(upload_history, color='#0099FF', linewidth=2, label=f'上传 ({unit})')
            line4, = self.net_ax.plot(download_history, color='#00CC99', linewidth=2, label=f'下载 ({unit})')
            artists.extend([line3, line4])
            fill_upload = self.net_ax.fill_between(range(len(upload_history)), upload_history, color='#87CEFA', alpha=0.5)
            artists.append(fill_upload)
            fill_download = self.net_ax.fill_between(range(len(download_history)), download_history, color='#90EE90', alpha=0.5)
            artists.append(fill_download)
        
        self.net_ax.set_ylabel(f'速度 ({unit})', color='white')
        self.net_ax.set_title('网络传输趋势', color='white', pad=20)
        self.net_ax.tick_params(colors='white')
        for spine in self.net_ax.spines.values():
            spine.set_color('white')
        
        leg = self.net_ax.legend(facecolor='#333333', labelcolor='white')
        artists.append(leg)
        self.net_canvas.draw()
        return artists

    def update_ui(self):
        if not self.running:
            return

        cpu_data = self.data['cpu']
        mem_data = self.data['memory']
        net_data = self.data['network']

        if cpu_data['percent'] is not None and cpu_data['percent'] >= 0:
            self.cpu_percent_var.set(f"{cpu_data['percent']:.1f}%")
        else:
            self.cpu_percent_var.set("N/A")

        if cpu_data['freq'] is not None and cpu_data['freq'] > 0:
            self.cpu_freq_var.set(f"{cpu_data['freq'] / 1000:.2f} GHz")
        else:
            self.cpu_freq_var.set("N/A")

        if mem_data['percent'] is not None and mem_data['percent'] >= 0:
            self.mem_percent_var.set(f"{mem_data['percent']:.1f}%")
        else:
            self.mem_percent_var.set("N/A")

        if mem_data['used'] is not None and mem_data['used'] >= 0:
            self.mem_used_var.set(f"{mem_data['used'] / (1024**3):.2f} GB")
        else:
            self.mem_used_var.set("N/A")

        if mem_data['total'] is not None and mem_data['total'] >= 0:
            self.mem_total_var.set(f"{mem_data['total'] / (1024**3):.2f} GB")
        else:
            self.mem_total_var.set("N/A")

        def convert_speed(speed):
            if speed is None or speed < 0:
                return "N/A", ""
            if speed >= 1024 * 1024:
                return f"{speed / (1024 * 1024):.2f}", "GB/s"
            elif speed >= 1024:
                return f"{speed / 1024:.2f}", "MB/s"
            else:
                return f"{speed:.2f}", "KB/s"

        upload_speed = net_data.get('upload_speed')
        upload_value, upload_unit = convert_speed(upload_speed)
        self.upload_var.set(f"{upload_value} {upload_unit}")

        download_speed = net_data.get('download_speed')
        download_value, download_unit = convert_speed(download_speed)
        self.download_var.set(f"{download_value} {download_unit}")

        if cpu_data['percent'] is not None and cpu_data['percent'] >= 80:
            self.buttons['cpu']['indicator'].config(bg='#FF0000')
        elif cpu_data['percent'] is not None and cpu_data['percent'] >= 60:
            self.buttons['cpu']['indicator'].config(bg='#FFA500')
        else:
            self.buttons['cpu']['indicator'].config(bg='#333333')

        if mem_data['percent'] is not None and mem_data['percent'] >= 80:
            self.buttons['memory']['indicator'].config(bg='#FF0000')
        elif mem_data['percent'] is not None and mem_data['percent'] >= 60:
            self.buttons['memory']['indicator'].config(bg='#FFA500')
        else:
            self.buttons['memory']['indicator'].config(bg='#333333')

        self.root.after(500, self.update_ui)
    
    def on_close(self):
        self.running = False
        if hasattr(self, 'ani_cpu'):
            self.ani_cpu.event_source.stop()
        if hasattr(self, 'ani_mem'):
            self.ani_mem.event_source.stop()
        if hasattr(self, 'ani_net'):
            self.ani_net.event_source.stop()
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=1)
        plt.close('all')
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()