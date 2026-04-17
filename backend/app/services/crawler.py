"""
Douban Movie Crawler Service
豆瓣电影爬虫服务
"""
import asyncio
import aiohttp
import re
import time
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd

from ..config import settings
from ..models.movie import Movie, DataSource
from ..models.task import Task, TaskType, TaskStatus
from ..database import SessionLocal


class DoubanCrawler:
    """
    豆瓣电影爬虫
    支持爬取电影基础信息和评论数据
    """

    def __init__(self):
        self.base_url = "https://movie.douban.com"
        self.delay = settings.CRAWL_DELAY
        self.timeout = settings.CRAWL_TIMEOUT
        self.max_retries = settings.CRAWL_MAX_RETRIES

        # 用户代理池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        ]

        # 代理IP池（示例，实际需要配置）
        self.proxies = []

    def _get_headers(self) -> Dict[str, str]:
        """获取随机请求头"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    async def _fetch(self, session: aiohttp.ClientSession, url: str, retry: int = 0) -> Optional[str]:
        """
        异步获取网页内容

        Args:
            session: aiohttp会话
            url: 目标URL
            retry: 重试次数

        Returns:
            网页HTML内容
        """
        try:
            # 随机延迟
            await asyncio.sleep(self.delay + random.uniform(0, 1))

            headers = self._get_headers()
            kwargs = {'headers': headers, 'timeout': aiohttp.ClientTimeout(total=self.timeout)}

            # 如果有代理池，随机选择代理
            if self.proxies:
                kwargs['proxy'] = random.choice(self.proxies)

            async with session.get(url, **kwargs) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 403:
                    # 可能被封禁，增加延迟
                    await asyncio.sleep(10)
                    if retry < self.max_retries:
                        return await self._fetch(session, url, retry + 1)
                else:
                    print(f"请求失败: {url}, 状态码: {response.status}")
                    return None

        except asyncio.TimeoutError:
            if retry < self.max_retries:
                await asyncio.sleep(5)
                return await self._fetch(session, url, retry + 1)
            else:
                print(f"请求超时: {url}")
                return None
        except Exception as e:
            print(f"请求异常: {url}, 错误: {e}")
            if retry < self.max_retries:
                await asyncio.sleep(5)
                return await self._fetch(session, url, retry + 1)
            return None

    def parse_movie_info(self, html: str) -> Optional[Dict[str, Any]]:
        """
        解析电影详情页HTML

        Args:
            html: 电影详情页HTML

        Returns:
            电影信息字典
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 电影名称
            title = soup.find('h1')
            title_span = title.find('span') if title else None
            movie_title = title_span.text.strip() if title_span else (title.text.strip() if title else "")

            # 年份
            year = None
            year_elem = soup.find('span', class_='year')
            if year_elem:
                year_match = re.search(r'(\d{4})', year_elem.text)
                if year_match:
                    year = int(year_match.group(1))

            # 评分
            rating = None
            rating_elem = soup.find('strong', class_='ll rating_num')
            if rating_elem:
                try:
                    rating = float(rating_elem.text.strip())
                except:
                    pass

            # 评分人数
            rating_count = None
            count_elem = soup.find('span', property='v:votes')
            if count_elem:
                try:
                    rating_count = int(count_elem.text.strip().replace(',', ''))
                except:
                    pass

            # 想看人数
            wish_count = None
            wish_elem = soup.find('div', class_='rating_bump')
            if wish_elem:
                wish_text = wish_elem.find('span', class_='rating_people')
                if wish_text:
                    try:
                        wish_count = int(wish_text.text.strip().replace(',', ''))
                    except:
                        pass

            # 类型标签
            genres = []
            genre_elems = soup.find_all('span', property='v:genre')
            for elem in genre_elems:
                genre = elem.text.strip()
                if genre:
                    genres.append(genre)

            # 导演和主演（从info中提取）
            info = soup.find('div', id='info')
            director = None
            cast = None
            if info:
                info_text = info.text.strip()

            # 上映日期
            release_date = None
            release_elem = soup.find('span', property='v:initialReleaseDate')
            if release_elem:
                date_str = release_elem.text.strip()
                # 提取第一个日期
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
                if date_match:
                    release_date = date_match.group(1)

            # 豆瓣ID（从页面链接提取）
            douban_id = None
            link_elem = soup.find('link', rel='canonical')
            if link_elem and link_elem.get('href'):
                id_match = re.search(r'/subject/(\d+)/', link_elem['href'])
                if id_match:
                    douban_id = id_match.group(1)

            # 话题热度（评论数作为替代）
            topic_heat = rating_count if rating_count else 0

            return {
                'douban_id': douban_id,
                'title': movie_title,
                'type': genres[0] if genres else None,
                'tags': genres,
                'release_year': year,
                'release_date': release_date,
                'rating': rating,
                'rating_count': rating_count,
                'wish_count': wish_count,
                'topic_heat': topic_heat,
                'data_source': 'crawl'
            }

        except Exception as e:
            print(f"解析电影信息失败: {e}")
            return None

    async def search_movies(
        self,
        session: aiohttp.ClientSession,
        keyword: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索电影

        Args:
            session: aiohttp会话
            keyword: 搜索关键词
            max_results: 最大结果数

        Returns:
            电影列表
        """
        search_url = f"{self.base_url}/subject_search?search_text={keyword}"
        html = await self._fetch(session, search_url)

        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        results = []

        # 解析搜索结果
        item_divs = soup.find_all('div', class_='item')
        for div in item_divs[:max_results]:
            try:
                # 获取电影链接
                link = div.find('a', class_='cover-link')
                if not link:
                    continue

                movie_url = link.get('href', '')
                id_match = re.search(r'/subject/(\d+)/', movie_url)
                if not id_match:
                    continue

                douban_id = id_match.group(1)

                # 获取标题
                title_span = div.find('span', class_='title')
                title = title_span.text.strip() if title_span else ""

                # 获取评分
                rating_span = div.find('span', class_='rating_nums')
                rating = None
                if rating_span:
                    try:
                        rating = float(rating_span.text.strip())
                    except:
                        pass

                # 获取评分人数
                people_span = div.find('span', class_='rating_people')
                rating_count = None
                if people_span:
                    try:
                        rating_count = int(people_span.text.strip().replace(',', ''))
                    except:
                        pass

                results.append({
                    'douban_id': douban_id,
                    'title': title,
                    'rating': rating,
                    'rating_count': rating_count,
                    'url': movie_url
                })

            except Exception as e:
                print(f"解析搜索结果失败: {e}")
                continue

        return results

    async def get_movie_detail(self, session: aiohttp.ClientSession, douban_id: str) -> Optional[Dict[str, Any]]:
        """
        获取电影详情

        Args:
            session: aiohttp会话
            douban_id: 豆瓣电影ID

        Returns:
            电影详情
        """
        url = f"{self.base_url}/subject/{douban_id}/"
        html = await self._fetch(session, url)

        if not html:
            return None

        return self.parse_movie_info(html)

    async def crawl_by_year(
        self,
        year_start: int,
        year_end: int,
        min_rating: float = 5.0,
        max_movies: int = 5000,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        按年份范围爬取电影

        Args:
            year_start: 起始年份
            year_end: 结束年份
            min_rating: 最低评分
            max_movies: 最大爬取数量
            progress_callback: 进度回调函数

        Returns:
            爬取的电影列表
        """
        movies = []
        total = 0

        async with aiohttp.ClientSession() as session:
            for year in range(year_start, year_end + 1):
                if total >= max_movies:
                    break

                # 按标签页爬取（豆瓣按年份排序的URL）
                # 使用豆瓣的标签分类页面
                tags = ['剧情', '喜剧', '动作', '爱情', '科幻', '动画', '悬疑', '犯罪']

                for tag in tags:
                    if total >= max_movies:
                        break

                    page = 0
                    while total < max_movies:
                        try:
                            # 豆瓣标签页URL
                            url = f"{self.base_url}/tag/{encodeURIComponent(tag)}?start={page * 20}&type=S"

                            html = await self._fetch(session, url)
                            if not html:
                                break

                            soup = BeautifulSoup(html, 'html.parser')
                            movie_list = soup.find('div', class_='list-wp')
                            if not movie_list:
                                break

                            items = movie_list.find_all('a', class_='item')
                            if not items:
                                break

                            for item in items:
                                if total >= max_movies:
                                    break

                                try:
                                    # 获取电影ID
                                    href = item.get('href', '')
                                    id_match = re.search(r'/subject/(\d+)/', href)
                                    if not id_match:
                                        continue

                                    douban_id = id_match.group(1)

                                    # 获取电影详情
                                    movie_data = await self.get_movie_detail(session, douban_id)

                                    if movie_data and movie_data.get('release_year') == year:
                                        if movie_data.get('rating', 0) >= min_rating:
                                            movies.append(movie_data)
                                            total += 1

                                            if progress_callback:
                                                await progress_callback(total, max_movies, f"已爬取: {movie_data['title']}")

                                except Exception as e:
                                    print(f"处理电影失败: {e}")
                                    continue

                            page += 1
                            await asyncio.sleep(random.uniform(1, 3))

                        except Exception as e:
                            print(f"爬取页面失败: year={year}, tag={tag}, page={page}, error={e}")
                            break

        return movies

    async def crawl_by_id_list(
        self,
        douban_ids: List[str],
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        根据豆瓣ID列表爬取电影

        Args:
            douban_ids: 豆瓣电影ID列表
            progress_callback: 进度回调函数

        Returns:
            爬取的电影列表
        """
        movies = []
        total = len(douban_ids)

        async with aiohttp.ClientSession() as session:
            for i, douban_id in enumerate(douban_ids):
                try:
                    movie_data = await self.get_movie_detail(session, douban_id)
                    if movie_data:
                        movies.append(movie_data)

                    if progress_callback:
                        await progress_callback(i + 1, total, f"已爬取: {douban_id}")

                except Exception as e:
                    print(f"爬取电影失败: {douban_id}, error={e}")
                    continue

        return movies


def encodeURIComponent(text: str) -> str:
    """URL编码"""
    import urllib.parse
    return urllib.parse.quote(text)


# 爬虫任务管理
class CrawlerTaskManager:
    """爬虫任务管理器"""

    def __init__(self):
        self.crawler = DoubanCrawler()
        self.running_tasks = {}

    async def run_crawl_task(
        self,
        task_id: int,
        year_start: int,
        year_end: int,
        min_rating: float,
        max_movies: int
    ):
        """
        执行爬取任务

        Args:
            task_id: 任务ID
            year_start: 起始年份
            year_end: 结束年份
            min_rating: 最低评分
            max_movies: 最大爬取数量
        """
        db = SessionLocal()
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            return

        try:
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.current_step = "开始爬取..."
            task.progress = 0
            db.commit()

            # 进度回调
            async def progress_callback(current: int, total: int, message: str):
                task.progress = int(current / total * 100)
                task.current_step = message
                db.commit()

            # 开始爬取
            movies = await self.crawler.crawl_by_year(
                year_start=year_start,
                year_end=year_end,
                min_rating=min_rating,
                max_movies=max_movies,
                progress_callback=progress_callback
            )

            # 保存到数据库
            saved_count = 0
            for movie_data in movies:
                try:
                    # 检查是否已存在
                    existing = db.query(Movie).filter(
                        Movie.douban_id == movie_data.get('douban_id')
                    ).first()

                    if not existing:
                        movie = Movie(**movie_data)
                        if movie_data.get('tags'):
                            movie.tags_list = movie_data['tags']
                        db.add(movie)
                        saved_count += 1

                except Exception as e:
                    print(f"保存电影失败: {movie_data.get('title')}, error={e}")
                    continue

            db.commit()

            # 更新任务状态
            task.status = TaskStatus.SUCCESS
            task.progress = 100
            task.current_step = "爬取完成"
            task.result_dict = {
                "total_crawled": len(movies),
                "saved_count": saved_count,
                "year_start": year_start,
                "year_end": year_end
            }

        except Exception as e:
            db.rollback()
            task.status = TaskStatus.FAILED
            task.error_msg = str(e)

        finally:
            db.commit()
            db.close()


# 全局任务管理器
crawler_task_manager = CrawlerTaskManager()
