import argparse
import os
import cv2
from pyzbar.pyzbar import decode
from fake_useragent import UserAgent
import requests



ua = UserAgent(os=["windows"])


def identify_qrcode(img_path):
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    decoded = decode(gray)
    url = ""
    for d in decoded:
        url += d.data.decode()
    return url

def get_act_id(url):
    headers = {
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
        'user-agent': ua.random,
    }

    response = requests.get(
        url=url,
        headers=headers,
        allow_redirects=False
    )
    act_id = response.headers["Location"].split("act_id=")[-1].split("&")[0]
    return act_id

def get_lottery_list(act_id):
    headers = {
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
        'user-agent': ua.random,
    }

    params = {
        'act_id': act_id,
    }

    response = requests.get('https://api.bilibili.com/x/vas/dlc_act/act/basic', params=params, headers=headers)
    json_data = response.json()
    lottery_list = json_data["data"]["lottery_list"]
    return lottery_list

def get_lottery_detail(act_id,lottery_id,root_path):
    headers = {
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
        'user-agent': ua.random,
    }

    params = {
        'act_id': act_id,
        'lottery_id': lottery_id,
    }

    response = requests.get(
        'https://api.bilibili.com/x/vas/dlc_act/lottery_home_detail',
        params=params,
        headers=headers,
    )

    json_data = response.json()
    item_list = json_data["data"]["item_list"]
    name = json_data["data"]["name"]
    root_path = f"{root_path}/{name}"
    if not os.path.exists(root_path):
        os.makedirs(root_path)
    print(f"收藏集：{name}开始下载！")
    for item in item_list:
        card_info = item["card_info"]
        card_name = card_info["card_name"]
        card_img = card_info["card_img"]
        print(f"{card_name}图片开始下载！")
        print(f"图片路径:{card_img}")
        img_response = requests.get(card_img, headers=headers)
        with open(f"{root_path}/{card_name}.png", mode="wb") as f:
            f.write(img_response.content)
        print(f"{card_name}图下载成功！")
def main():
    author = "创生R"
    version = "1.0.0"
    github_url = "https://github.com/ChuangSR/BilibiliCollectionExtraction"
    description = f"""
        一个B站的收藏集图片下载器
        作者：{author}
        version: {version}
        {github_url}
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-f", help="一个包含收藏集二维码的图片，用于提取收藏集的url链接",required=True)
    parser.add_argument("-p", help="指定一个图片的输出路径，默认为为./img",required=True)
    args = parser.parse_args()
    rootpath = "./img"
    if args.p:
        rootpath = args.p
    path = args.f
    url = identify_qrcode(path)
    print("url解析成功！")
    act_id = get_act_id(url)
    print("必要参数解析完成！")
    lottery_list = get_lottery_list(act_id)
    print("图片列表获取完成！")
    print("由于b站服务器问题，下载速度可能会偏慢，请耐心等待！")
    for item in lottery_list:
        lottery_id = item["lottery_id"]
        get_lottery_detail(act_id,lottery_id,rootpath)
if __name__ == "__main__":
    main()
