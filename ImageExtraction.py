import argparse
import json
import os
import re
import cv2
from pyzbar.pyzbar import decode
import requests
from urllib.parse import urlparse, parse_qs



ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18362"

BROWSER_HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Microsoft Edge";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': ua,
}

API_HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'cache-control': 'no-cache',
    'origin': 'https://www.bilibili.com',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.bilibili.com/',
    'sec-ch-ua': '"Microsoft Edge";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': ua,
}


def identify_qrcode(img_path):
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    decoded = decode(gray)
    url = ""
    for d in decoded:
        url += d.data.decode()
    return url


def sanitize_filename(name):
    """去除 Windows 文件名中的非法字符，避免创建目录/写文件失败"""
    return re.sub(r'[\\/:*?"<>|\r\n]+', '_', str(name)).strip()


def extract_params(url):
    """从单个 URL 的查询参数中提取 act_id 与 lottery_id"""
    try:
        params = parse_qs(urlparse(url).query)
    except Exception:
        return None, None
    act_id = params.get('act_id', [None])[0]
    lottery_id = params.get('lottery_id', [None])[0]
    return act_id, lottery_id


def resolve_act_info(url):
    """
    解析收藏集链接，支持：
      1. 直接带 act_id 的完整分享链接
         如 https://www.bilibili.com/h5/mall/digital-card/home?...&act_id=282&lottery_id=347&...
      2. b23.tv 短链及其他会 302 跳转到收藏集页面的链接
    返回 (act_id, lottery_id)，lottery_id 可能为 None
    """
    act_id, lottery_id = extract_params(url)
    if act_id:
        return act_id, lottery_id

    print("链接中未直接包含 act_id，尝试跟随重定向解析...")
    response = requests.get(
        url=url,
        headers=BROWSER_HEADERS,
        allow_redirects=True,
        timeout=15
    )
    # 依次检查重定向链中的每一跳以及最终落地页的 URL
    for resp in list(response.history) + [response]:
        a, l = extract_params(resp.url)
        act_id = act_id or a
        lottery_id = lottery_id or l
    if not act_id:
        raise RuntimeError(f"无法从链接中解析 act_id，请检查链接是否正确：{url}")
    return act_id, lottery_id


def save_json(data, file_path):
    """把接口返回的原始数据保存到文件，方便查看还有哪些字段可以提取"""
    with open(file_path, mode="w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"原始数据已保存: {file_path}")


def get_video_urls(card_info):
    """
    提取卡牌的视频地址列表，按URL路径去重（同一张卡的多个地址通常只是CDN镜像）。
    优先使用无水印的 video_list，为空时回退到带水印的 video_list_download。
    """
    for key in ("video_list", "video_list_download"):
        urls = card_info.get(key) or []
        unique = []
        seen = set()
        for u in urls:
            path = urlparse(u).path
            if path not in seen:
                seen.add(path)
                unique.append(u)
        if unique:
            return unique
    return []


def download_video(video_url, save_path):
    """流式下载视频文件（bilivideo.com 需要带 Referer，API_HEADERS 中已包含）"""
    with requests.get(video_url, headers=API_HEADERS, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(save_path, mode="wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)


def get_lottery_list(act_id, root_path):
    params = {
        'act_id': act_id,
    }

    response = requests.get('https://api.bilibili.com/x/vas/dlc_act/act/basic', params=params, headers=API_HEADERS)
    json_data = response.json()
    if json_data.get("code") != 0:
        raise RuntimeError(f"act/basic 接口返回错误: {json_data.get('message')}")

    if not os.path.exists(root_path):
        os.makedirs(root_path)
    # 保存活动基础信息（含 lottery_list、活动标题、封面等全部字段）
    save_json(json_data, os.path.join(root_path, "act_basic.json"))

    lottery_list = json_data["data"]["lottery_list"]
    return lottery_list


def get_lottery_detail(act_id, lottery_id, root_path, download=True, download_video_flag=False):
    params = {
        'act_id': act_id,
        'lottery_id': lottery_id,
    }

    response = requests.get(
        'https://api.bilibili.com/x/vas/dlc_act/lottery_home_detail',
        params=params,
        headers=API_HEADERS,
    )

    json_data = response.json()
    if json_data.get("code") != 0:
        raise RuntimeError(f"lottery_home_detail 接口返回错误: {json_data.get('message')}")

    item_list = json_data["data"]["item_list"]
    name = sanitize_filename(json_data["data"]["name"])
    lottery_path = os.path.join(root_path, name)
    if not os.path.exists(lottery_path):
        os.makedirs(lottery_path)

    # 保存该收藏集详情的完整原始数据（含每张卡牌的全部字段）
    save_json(json_data, os.path.join(lottery_path, "lottery_detail.json"))

    if not download:
        print(f"收藏集：{name} 数据已导出（--only-data 模式，跳过图片下载）")
        return

    print(f"收藏集：{name}开始下载！")
    for item in item_list:
        card_info = item["card_info"]
        card_name = sanitize_filename(card_info["card_name"])
        card_img = card_info["card_img"]
        print(f"{card_name}图片开始下载！")
        print(f"图片路径:{card_img}")
        img_response = requests.get(card_img, headers=API_HEADERS)
        with open(os.path.join(lottery_path, f"{card_name}.png"), mode="wb") as f:
            f.write(img_response.content)
        print(f"{card_name}图下载成功！")

        # 动态卡视频下载（默认开启，--no-video 关闭）
        if download_video_flag:
            video_urls = get_video_urls(card_info)
            for idx, video_url in enumerate(video_urls, start=1):
                suffix = "" if len(video_urls) == 1 else f"_{idx}"
                video_path = os.path.join(lottery_path, f"{card_name}{suffix}.mp4")
                print(f"{card_name}视频开始下载！")
                print(f"视频路径:{video_url}")
                try:
                    download_video(video_url, video_path)
                    print(f"{card_name}视频下载成功！")
                except Exception as e:
                    print(f"{card_name}视频下载失败，已跳过：{e}")


def main():
    author = "创生R"
    version = "1.3.0"
    github_url = "https://github.com/ChuangSR/BilibiliCollectionExtraction"
    description = f"""
        一个B站的收藏集图片下载器
        作者：{author}
        version: {version}
        {github_url}
    """
    parser = argparse.ArgumentParser(description=description)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", help="一个包含收藏集二维码的图片，用于提取收藏集的url链接")
    group.add_argument("-u", help="直接输入收藏集的URL链接（支持完整分享链接和b23.tv短链，注意用引号包裹整个URL）")
    parser.add_argument("-p", help="指定一个图片的输出路径，默认为为./img")
    parser.add_argument("--only-data", action="store_true", help="只把接口返回的数据导出为JSON文件，不下载图片")
    parser.add_argument("-v", "--video", action=argparse.BooleanOptionalAction, default=True,
                        help="下载动态卡的视频（保存为mp4，文件较大，默认开启，可用 --no-video 关闭）")
    args = parser.parse_args()
    rootpath = "./img"
    if args.p:
        rootpath = args.p

    if args.u:
        url = args.u.strip().strip('"').strip("'")
    else:
        path = args.f
        url = identify_qrcode(path)
        print("url解析成功！")
    print(description)

    act_id, lottery_id = resolve_act_info(url)
    print(f"必要参数解析完成！act_id={act_id}" + (f"，lottery_id={lottery_id}" if lottery_id else ""))

    if lottery_id:
        print(f"检测到特定收藏集ID: {lottery_id}")
        get_lottery_detail(act_id, lottery_id, rootpath, download=not args.only_data, download_video_flag=args.video)
    else:
        lottery_list = get_lottery_list(act_id, rootpath)
        print("图片列表获取完成！")
        print("由于b站服务器问题，下载速度可能会偏慢，请耐心等待！")
        for item in lottery_list:
            lottery_id = item["lottery_id"]
            get_lottery_detail(act_id, lottery_id, rootpath, download=not args.only_data, download_video_flag=args.video)


if __name__ == "__main__":
    main()
    """
     pyinstaller -F -w --hidden-import PIL --hidden-import tkinter --hidden-import pyperclip --hidden-import pyzbar -i logo.ico --add-data=logo.ico:. --add-data=libiconv.dll:./pyzbar/ --add-data=libzbar-64.dll:./pyzbar/ ImageExtraction.py

    """
