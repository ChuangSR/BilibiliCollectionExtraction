# 关于本项目：

​	这是一个B站收藏集图片的下载器，支持下载收藏集内所有卡牌的图片，也可以选择导出接口返回的原始数据或下载动态卡视频。

​	下载速度较慢（与B站服务器有关，没有报错就是可以正常运行）。

## 功能特性：

- 支持两种方式输入收藏集链接：二维码图片识别 或 直接输入URL
- 支持完整分享链接和 b23.tv 短链（自动跟随重定向解析）
- 链接中包含 lottery_id 时只下载对应的收藏集，否则下载活动下的全部收藏集
- 默认同时下载动态卡的视频（mp4，可用 `--no-video` 关闭）
- 下载时在控制台输出图片和视频的直链
- 自动保存接口返回的原始 JSON 数据，方便查看还有哪些字段可以提取
- 自动处理 Windows 文件名中的非法字符

## 参数说明：

使用 pyinstaller 对项目进行打包后可执行文件为 `ImageExtraction.exe`，支持以下参数：

| 参数 | 说明 |
| --- | --- |
| `-f` | 一个包含收藏集二维码的图片，用于提取收藏集的url链接（与 `-u` 二选一，必填其一） |
| `-u` | 直接输入收藏集的URL链接，支持完整分享链接和b23.tv短链（与 `-f` 二选一，必填其一，注意用引号包裹整个URL） |
| `-p` | 指定图片的输出路径，默认为 `./img` |
| `--only-data` | 只把接口返回的数据导出为JSON文件，不下载图片 |
| `-v` / `--video` | 下载动态卡的视频（保存为mp4，文件较大，默认开启；可用 `--no-video` 关闭） |

## 使用示例：

​	通过二维码图片下载：

```
ImageExtraction.exe -f xxx.jpg -p xxx
```

​	-f 的参数为以图片形式分享的包含收藏集链接的二维码，如
![8B82CD34F1F95B5BCC34171BC24E90BA](https://github.com/user-attachments/assets/f1325a70-5f66-4110-95d1-b267736beb88)

​	直接通过链接下载（完整分享链接）：

```
ImageExtraction.exe -u "https://www.bilibili.com/h5/mall/digital-card/home?...&act_id=282&lottery_id=347&..."
```

​	通过 b23.tv 短链下载（视频默认一并下载）：

```
ImageExtraction.exe -u "https://b23.tv/xxxxxx"
```

​	只下载图片、不下载视频：

```
ImageExtraction.exe -u "https://b23.tv/xxxxxx" --no-video
```

​	只导出数据不下载图片：

```
ImageExtraction.exe -f xxx.jpg --only-data
```

![4EEB861FFFB73908986BE29D1450459F](https://github.com/user-attachments/assets/2ba42270-cb1d-417a-8488-5afcf5286857)

## 输出目录结构：

```
./img（或 -p 指定的路径）
├── act_basic.json            # 活动基础信息（含 lottery_list 等全部字段）
├── 收藏集名称1/
│   ├── lottery_detail.json   # 该收藏集详情的完整原始数据
│   ├── 卡牌名称1.png
│   ├── 卡牌名称2.png
│   └── 卡牌名称2.mp4         # 使用 -v 时下载的动态卡视频
└── 收藏集名称2/
    └── ...
```

## 从源码运行：

​	安装依赖（pyzbar 在 Windows 下还需要 libiconv.dll 和 libzbar-64.dll）：

```
pip install -r requirements.txt
python ImageExtraction.py -u "收藏集链接"
```

## 打包：

```
pyinstaller -F -w --hidden-import PIL --hidden-import tkinter --hidden-import pyperclip --hidden-import pyzbar -i logo.ico --add-data=logo.ico:. --add-data=libiconv.dll:./pyzbar/ --add-data=libzbar-64.dll:./pyzbar/ ImageExtraction.py
```
