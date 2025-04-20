import os
import re
import time

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36'
}


class Scraper:
    def __init__(self, base_url, save_dir, retry_times=3, headers=None):
        self.headers = HEADERS if headers is None else headers
        self.base_url = base_url
        self.save_dir = save_dir
        self.file_name: str = ""
        self.retry_times: int = retry_times

    def find_pdf_links(self) -> list:
        """查找页面中的所有PDF链接"""
        try:
            response = requests.get(self.base_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            pdf_links = []

            # 查找所有包含.pdf的链接（可能需要根据网站结构调整）
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if href.lower().endswith('.pdf'):
                    full_url = urljoin(self.base_url, href)  # 处理相对路径
                    pdf_links.append(full_url)
            return pdf_links
        except Exception as e:
            print(f"获取页面失败: {str(e)}")
            return []

    def extract_filename(self, url, response):
        """从URL中提取安全的文件名"""
        # 解析URL路径
        path = urlparse(url).path
        # 获取基础文件名
        self.file_name = os.path.basename(path)
        # 处理无后缀的情况（有些网站通过重定向提供PDF）
        if not self.file_name.lower().endswith('.pdf'):
            # 尝试从Content-Disposition获取（需要实际下载时获取）
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                self.file_name = re.findall('filename=(.+)', content_disposition)[0].strip('"')
            # self.file_name += ".pdf"
        self.file_name = re.sub(r'[\\/*?:"<>|]', '_', self.file_name).strip(" .")
        # 清理特殊字符

    def download_pdf(self, url):
        """下载并保存PDF文件"""
        try:
            with requests.get(url, headers=self.headers, stream=True, timeout=20) as response:
                response.raise_for_status()

                # 优先从URL获取文件名
                self.extract_filename(url, response)

                # 最终生成的保存路径
                save_path = f"{SAVE_DIR}/{self.file_name}"

                # 避免覆盖已有文件
                if os.path.exists(save_path):
                    print(f"文件已存在，跳过: {self.file_name}")
                    return

                # 开始下载
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            # 显示进度（当知道总大小时）
                            if total_size > 0:
                                percent = downloaded_size / total_size * 100
                                print(f"\r下载中: {self.file_name} - {percent:.1f}%", end='')

                # 完整性校验
                if 0 < total_size != downloaded_size:
                    raise Exception(f"文件大小不完整（预期 {total_size}，实际 {downloaded_size}）")

                print(f"\n✅ 成功保存: {self.file_name}")
                return
        except Exception as e:
            raise e

    def run(self):
        os.makedirs(self.save_dir, exist_ok=True)
        # 获取PDF链接（可能需要处理分页/多个页面）
        pdf_urls = self.find_pdf_links()

        print(f"找到 {len(pdf_urls)} 个PDF文件")
        # 遍历下载
        for idx, url in enumerate(pdf_urls, 1):
            print(f"\n[{idx}/{len(pdf_urls)}] 处理: {url}")
            for attempt in range(self.retry_times):
                try:
                    self.download_pdf(url)
                    break
                except Exception as e:
                    print(f"\n❌ 下载失败（第{attempt + 1}次尝试）: {str(e)}")
                    time.sleep(2)
                if attempt + 1 == self.retry_times:
                    print(f"永久失败: {url}")
            time.sleep(1.5)  # 降低服务器压力


if __name__ == "__main__":
    # 目标网站URL（需要替换成实际地址）
    BASE_URL = ""  #  目标地址
    # 保存PDF的目录
    SAVE_DIR = "download/pdf_downloads_2_class_test3"
    crawler = Scraper(BASE_URL, SAVE_DIR)
    crawler.run()
