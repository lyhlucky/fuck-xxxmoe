# fuck xxxmoe
import os, shutil, zipfile, re
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import filedialog


# 用于标注哪些文件属于封面
cover_img_list = [
    'cover.jpg',
    'createby.png'
]

def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def has_number_in_filename(filename):
    return bool(re.search(r'\d', os.path.splitext(filename)[0]))

def epubextract(selected_files):
    for file in selected_files:

        file_name = os.path.basename(file)
        file_dictionary = os.path.join(directory_path, file_name[:-5])
        mkdir(file_dictionary)

        num = 1
        try:
            with zipfile.ZipFile(file, 'r') as epubfile:
                file_list = epubfile.namelist() # 列出EPUB文件中的所有文件
                file_opf = next((f for f in file_list if f.endswith('.opf')), None) # 提取目录中的opf文件
                catalog_xml = BeautifulSoup(epubfile.read(file_opf), features='xml') # 读取vol.opf文件

                # 按顺序提取html文件
                html_list = catalog_xml.find_all('item', href=lambda href: href and '.html' in href) # 筛选item标签下href属性的html
                html_filter = [item['href'] for item in html_list] # 按顺序保存到list中

                image_list = [img['src'][3:] for html_filted in html_filter for img in BeautifulSoup(epubfile.read(html_filted), features='xml').find_all('img')]
                image_manga = [i for i in image_list if has_number_in_filename(i)]
                # image_cover = [i for i in image_list if not has_number_in_filename(i)]

                manga_dict = {item: index for index, item in enumerate(image_manga, start=1)}  # 生成一个漫画对应的序号

                for image in image_list:
                    epubfile.extract(image, path = file_dictionary)

                for image in os.listdir(os.path.join(file_dictionary, "image")):
                    global delete_cover
                    if delete_cover.get():
                        if image in cover_img_list:
                            continue
                    image_without_ext, extension = os.path.splitext(image)
                    try:        
                        os.rename(os.path.join(file_dictionary, "image", image), os.path.join(file_dictionary, f"{str(manga_dict['image/' + image]).zfill(4)}{extension}"))
                    except KeyError:
                        os.rename(os.path.join(file_dictionary, "image", image), os.path.join(file_dictionary, image))                   

                shutil.rmtree(os.path.join(file_dictionary, "image"))

                global output_zip
                if output_zip.get():
                    zip_filename = os.path.join(directory_path, f"{file_name[:-5]}.zip")
                    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipdir(file_dictionary, zipf)

        except zipfile.BadZipFile:
            label_file.config(text="错误: 该文件不是有效的EPUB文件或已损坏。")

def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            relative_path = os.path.relpath(os.path.join(root, file), os.path.join(path, '..'))
            ziph.write(os.path.join(root, file), relative_path)

line_height = 0
def select_file():
    global selected_files, line_height
    file_path = filedialog.askopenfilenames(title="选择要处理的epub文件", filetypes=[("epub", "*.epub")])
    if file_path:
        selected_files = list(file_path)
        label_file.config(text=f"EPUB文件:\n{'\n'.join(file_path)}", justify=tk.LEFT, anchor="w") # 显示选中的文件路径，每个文件另起一行
        add_window_height(17 * len(selected_files) - line_height)
        line_height = 17 * len(selected_files)
        select_dir_button.config(state=tk.NORMAL)

def select_directory():
    global directory_path
    directory_path = filedialog.askdirectory(title="选择文件输出目录")
    if directory_path:
        label_dictionary.config(text=f"输出目录:\n{directory_path}", justify=tk.LEFT, anchor="w")
        add_window_height(17)
        run_button.config(state=tk.NORMAL)

def process_file():
    file_path = label_file.cget("text").replace("EPUB文件:", "")
    epubextract(selected_files)
    label_file.config(text=f"EPUB文件处理完成:{file_path}")

def add_window_height(height):
    global window_height
    window_height += height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) / 2
    y = (screen_height - window_height) / 2
    root.geometry(f"{window_width}x{window_height}+{int(x)}+{int(y)}")

# 创建主窗口
root = tk.Tk()
window_width = 400
window_height = 120
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - window_width) / 2
y = (screen_height - window_height) / 2
root.title("fuck-xxxmoe工具V4")
root.geometry(f"{window_width}x{window_height}+{int(x)}+{int(y)}")  # 设置窗口的大小和位置

# 创建主窗口
frame_root = tk.Frame(root)
frame_root.pack(side=tk.TOP, fill="x", padx=5, pady=8)

# 创建按钮
frame_buttons = tk.Frame(frame_root)
frame_buttons.pack(side=tk.TOP, fill="x", padx=0, pady=0)
select_file_button = tk.Button(frame_buttons, text="1.选择EPUB文件", command=select_file)
select_file_button.pack(side=tk.LEFT, expand=True, fill="x", padx=2)
select_dir_button = tk.Button(frame_buttons, text="2.选择输出目录", state=tk.DISABLED, command=select_directory)
select_dir_button.pack(side=tk.LEFT, expand=True, fill="x", padx=2)
run_button = tk.Button(frame_buttons, text="3.运行", state=tk.DISABLED, command=process_file)
run_button.pack(side=tk.LEFT, expand=True, fill="x", padx=2)
quit_button = tk.Button(frame_buttons, text="退出", command=root.destroy)
quit_button.pack(side=tk.LEFT, expand=True, fill="x", padx=2)

# 创建复选框
frame_checks = tk.Frame(frame_root)
frame_checks.pack(side=tk.TOP, fill="x", padx=0, pady=0)
delete_cover = tk.IntVar()
delete_cover.set(0)
delete_cover_check = tk.Checkbutton(frame_checks, text="删除封面", variable=delete_cover)
delete_cover_check.pack(side=tk.LEFT, anchor="w")
output_zip = tk.IntVar()
output_zip.set(0)
output_zip_check = tk.Checkbutton(frame_checks, text="压缩为ZIP", variable=output_zip)
output_zip_check.pack(side=tk.LEFT, anchor="w", padx=5)

# 显示文件路径和名称的标签在下面
label_file = tk.Label(frame_root, text="未选择文件")
label_file.pack(side=tk.TOP, pady=0, fill="x", expand=True, anchor="w")
label_file.config(text=f"EPUB文件: 未选择", justify=tk.LEFT, anchor="w")

# 显示文件路径和名称的标签在下面
label_dictionary = tk.Label(frame_root, text="未选择目录")
label_dictionary.pack(side=tk.TOP, pady=0, fill="x", expand=True, anchor="w")
label_dictionary.config(text=f"输出目录: 未选择", justify=tk.LEFT, anchor="w")

# 运行主循环
root.mainloop()