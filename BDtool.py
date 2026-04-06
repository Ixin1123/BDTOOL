import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os


# --- 物理路径加载字体，彻底解决中文乱码 ---
def get_chinese_font_prop():
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
    ]
    for path in font_paths:
        if os.path.exists(path):
            return fm.FontProperties(fname=path, size=11)
    return fm.FontProperties(family='sans-serif', size=11)


CH_FONT_PROP = get_chinese_font_prop()


class BeidouSmartEvidence:
    def __init__(self, root):
        self.root = root
        # 优化：更具专业质检风格的窗口标题
        self.root.title("北斗定位报文智能取证系统 v1")
        self.root.geometry("450x300")
        self.file_path = ""

        # 优化：更大气的主界面标题
        tk.Label(root, text="北斗定位报文自动识别", font=('微软雅黑', 13, 'bold')).pack(pady=15)

        # 1. 文件载入
        tk.Button(root, text="载入 NMEA 日志文件", command=self.select_file, width=25).pack()
        self.label_file = tk.Label(root, text="等待导入...", fg="gray")
        self.label_file.pack(pady=5)

        # 2. 时间输入
        tk.Label(root, text="目标时刻 (可留空):").pack(pady=5)
        self.entry_time = tk.Entry(root, font=('Consolas', 14), justify='center', width=15)
        self.entry_time.pack()

        # 3. 执行按钮
        tk.Button(root, text="生成报文截图", command=self.process,
                  bg="#1a1a1a", fg="white", font=('微软雅黑', 10, 'bold'), width=25).pack(pady=20)

    def select_file(self):
        self.file_path = filedialog.askopenfilename()
        if self.file_path:
            self.label_file.config(text=os.path.basename(self.file_path), fg="#004a99")

    def process(self):
        if not self.file_path:
            messagebox.showwarning("提示", "请先导入报文文件！")
            return

        t_input = self.entry_time.get().strip()

        # 获取导入文件所在的同级目录路径
        base_dir = os.path.dirname(self.file_path)

        try:
            with open(self.file_path, 'rb') as f:
                raw = f.readlines()

            # 解码处理
            lines = [l.decode('utf-8', 'ignore').strip() if b'\x00' not in l else l.decode('gbk', 'ignore').strip() for
                     l in raw]

            target_time = ""
            label = ""

            # --- 逻辑优化：全兼容前缀检索失败时刻 ---
            if t_input:
                target_time = t_input
                label = "定位成功"
            else:
                fail_times = []
                for l in lines:
                    # 关键修改：不再判断 $GN/$BD，只要包含 RMC 且状态为 V (无效定位)
                    if "RMC" in l.upper() and ",V," in l.upper():
                        parts = l.split(',')
                        if len(parts) > 1 and parts[1]:
                            time_val = parts[1].split('.')[0]
                            if time_val not in fail_times:
                                fail_times.append(time_val)

                if not fail_times:
                    messagebox.showerror("错误", "日志中未发现任何‘定位失败(V)’的状态报文！")
                    return

                # 自动挑选中间时刻
                target_time = fail_times[len(fail_times) // 2] if len(fail_times) >= 3 else fail_times[0]
                label = "定位失败"

            # --- 逻辑优化：全兼容提取包含目标时间的所有 GGA/RMC 报文 ---
            indices = []
            for i, l in enumerate(lines):
                upper_l = l.upper()
                # 只要这一行包含目标时间戳，并且是定位核心报文 (不论是 $GN/$BD/$GB 开头)
                if target_time in upper_l and ("RMC" in upper_l or "GGA" in upper_l):
                    indices.append(i)

            if not indices:
                messagebox.showerror("失败", f"未找到时刻 {target_time} 的核心定位报文")
                return

            start, end = min(indices), max(indices)
            target_block = lines[start: end + 1]

            # 传入 base_dir 以便保存在同一路径
            self.draw_pure_img(target_time, target_block, label, base_dir)

        except Exception as e:
            messagebox.showerror("异常", str(e))

    def draw_pure_img(self, t, block, label, base_dir):
        # 画板高度适当增加，确保左下角判定与报文距离
        fig, ax = plt.subplots(figsize=(11, 4))
        ax.axis('off')

        content = []
        sep_line = "-" * 95

        content.append(sep_line)
        for line in block:
            content.append(line)
        content.append(sep_line)

        # 增加空行，使结论与报文产生距离感
        content.append("")
        content.append("")
        content.append("")

        content.append(f"核查时间：{t}")
        content.append(f"判定结论：{label}")

        final_text = "\n".join(content)

        # 严格左对齐
        plt.text(0.01, 0.95, final_text,
                 fontproperties=CH_FONT_PROP,
                 va='top',
                 ha='left',
                 linespacing=1.7)

        plt.tight_layout(pad=0)

        file_name = f"BD_{t}_{label}.png"

        # 核心修改：将文件名拼接到同级目录下
        img_save_path = os.path.join(base_dir, file_name)

        plt.savefig(img_save_path, bbox_inches='tight', dpi=150, pad_inches=0.1, facecolor='white')
        plt.close()

        messagebox.showinfo("完成", f"已生成定点报文截图：\n{img_save_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = BeidouSmartEvidence(root)
    root.mainloop()
