#fuck xxxmoe
import os
import zipfile
from bs4 import BeautifulSoup
# import ebooklib
# from ebooklib import epub
import tkinter as tk
from tkinter import filedialog
import re

#定义图形界面

def mkdir(path):
    folder = os.path.exists(path)
    if not folder:                   #判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)            #makedirs 创建文件时如果路径不存在会创建这个路径
    if folder:
        pass

def has_number_in_filename(filename):
    filename_without_ext, ext = os.path.splitext(filename)

    # 使用正则表达式判断
    return bool(re.search(r'\d', filename_without_ext))




def epubextract(selected_files):
    for file in selected_files:

        file_name = os.path.basename(file)
        file_dictionary = directory_path +"/"+ file_name[:-5]
        mkdir(file_dictionary)

        num = 1
        try:
            with zipfile.ZipFile(file, 'r') as epubfile:

                # 列出EPUB文件中的所有文件
                file_list = epubfile.namelist()

                # 提取目录中的opf文件
                for f in file_list:
                    if os.path.splitext(f)[1] == ".opf":
                        file_opf = f
                
                #读取vol.opf文件
                catalog = epubfile.read(file_opf)
                catalog_xml = BeautifulSoup(catalog, features='xml')
                # print(catalog_xml)

                #按顺序提取html文件
                html_list = catalog_xml.find_all('item', href=lambda href: href and '.html' in href) #筛选item标签下href属性的html
                html_filter = [item['href'] for item in html_list]                                   #按顺序保存到list中
                # print("html_filter:",html_filter)

                image_list = []
                image_manga = []
                image_cover = []

                for html_filted in html_filter:
                    html = epubfile.read(html_filted)
                    html_xml = BeautifulSoup(html, features='xml')

                    for img in html_xml.find_all('img'):                
                        image_list.append(img['src'][3:])

                for i in image_list:
                    if has_number_in_filename(i) == 1:
                        image_manga.append(i)
                    else:
                        image_cover.append(i)

                manga_dict ={}
                manga_dict = {item: index for index, item in enumerate(image_manga, start=1)}  #生成一个漫画对应的序号

                for image in image_list:
                    epubfile.extract(image, path = file_dictionary)

                for image in os.listdir(file_dictionary + "/image"):
                    image_without_ext, extension = os.path.splitext(image)
                    try:        
                        os.rename((file_dictionary + "/image/" + image), (file_dictionary + "/" + f"{str(manga_dict["image/" + image]).zfill(4)}"+ extension))
                        # print("1",(file_dictionary + "/image/" + image)," ",(file_dictionary + "/" + f"{str(manga_dict["image/" + image]).zfill(4)}"+ extension))
                    except KeyError:
                        os.rename((file_dictionary + "/image/" + image), (file_dictionary + "/" + image))
                        # print("0",(file_dictionary + "/image/" + image)," ",(file_dictionary + "/" + image))                    

                os.rmdir(file_dictionary + "/image")

        except zipfile.BadZipFile:
            label_file.config(text="错误: 该文件不是有效的xxxmoe EPUB文件或已损坏。")



def select_file():
    global selected_files
    file_path = filedialog.askopenfilenames(
        title="选择要处理的epub文件",
        filetypes=[("epub", "*.epub*")]  # 可以根据需要设置文件类型过滤器
    )
    if file_path:
        selected_files = list(file_path)
        # 显示选中文件的路径和文件名
        files_display = "\n".join(file_path)
        # 显示选中的文件路径，每个文件另起一行
        label_file.config(text=f"已选择epub文件:\n{files_display}",justify=tk.LEFT, anchor="w")
        # 激活运行按钮
        # run_button.config(state=tk.NORMAL)
        select_dir_button.config(state=tk.NORMAL)

def select_directory():
    global directory_path
    directory_path = filedialog.askdirectory(
        title="选择文件输出目录"
    )
    if directory_path:
        label_dictionary.config(text=f"已选择文件输出目录:\n{directory_path}",justify=tk.LEFT, anchor="w")
        # run_button.config(state=tk.NORMAL)
        run_button.config(state=tk.NORMAL)

def process_file():
    file_path = label_file.cget("text").replace("已选择文件: ", "")
    epubextract(selected_files)
    # 这里添加处理文件的代码
    # print(f"正在处理文件: {file_path}")
    label_file.config(text=f"文件处理完成: {file_path}")



# 创建主窗口
root = tk.Tk()
root.title("fuck-xxxmoe工具V3编译时间2024-08-20：本工具完全免费，欢迎到本项目github主页提出使用建议")
root.geometry("400x300")  # 设置窗口的大小

# 创建一个 Frame 容器来放置按钮
frame_buttons = tk.Frame(root)
frame_buttons.pack(side=tk.TOP, pady=10)

# 创建“选择文件”按钮并放在左边
select_file_button = tk.Button(frame_buttons, text="选择文件", command=select_file)
select_file_button.pack(side=tk.LEFT, padx=10)

# 创建“选择目录”按钮并放在中间
select_dir_button = tk.Button(frame_buttons, text="选择目录", state=tk.DISABLED, command=select_directory)
select_dir_button.pack(side=tk.LEFT, padx=10)

# 创建“运行”按钮并放在右边
run_button = tk.Button(frame_buttons, text="运行", state=tk.DISABLED, command=process_file)
run_button.pack(side=tk.LEFT, padx=10)

# 创建“退出”按钮
quit_button = tk.Button(frame_buttons, text="退出程序", command=root.destroy)
quit_button.pack(side=tk.LEFT, padx=10)

# 显示文件路径和名称的标签在下面
label_file = tk.Label(root, text="未选择文件")
label_file.pack(side=tk.TOP, pady=10, fill="both", expand=True)

# 显示文件路径和名称的标签在下面
label_dictionary = tk.Label(root, text="未选择目录")
label_dictionary.pack(side=tk.TOP, pady=10, fill="both", expand=True)

# 运行主循环
root.mainloop()