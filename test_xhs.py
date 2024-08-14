'''
CreateTime: 2024-08-11 23:40:23
Author: lizhanbo
LastEditors: lizhanbo
LastEditTime: 2024-08-14 23:02:30
FilePath: \test_xhs.py
Description: 
'''
# -*- coding: utf-8 -*-
import asyncio
import sys
import os
import random
import config
import logging
from tools import utils
from typing import Dict, List, Optional, Tuple
from var import crawler_type_var
from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)
from media_platform.xhs.client import XiaoHongShuClient
from media_platform.xhs.login import XiaoHongShuLogin
from media_platform.xhs.field import SearchSortType, SearchNoteType, FeedType

class TestXiaoHongShuClient():
    context_page: Page
    xhs_client: XiaoHongShuClient
    browser_context: BrowserContext
    def __init__(self) -> None:
        self.index_url = "https://www.xiaohongshu.com"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"        

    async def create_xhs_client(self, httpx_proxy: Optional[str]) -> XiaoHongShuClient:
        """Create xhs client"""
        utils.logger.info("[XiaoHongShuCrawler.create_xhs_client] Begin create xiaohongshu API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        xhs_client_obj = XiaoHongShuClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.xiaohongshu.com",
                "Referer": "https://www.xiaohongshu.com",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return xhs_client_obj
    
    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[XiaoHongShuCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            # we will save login state to avoid login every time
            user_data_dir = os.path.join(os.getcwd(), "browser_data",
                                         config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context
    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None

        async with async_playwright() as playwright:
            # Launch a browser context.
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium,
                None,
                self.user_agent,
                headless=config.HEADLESS
            )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            # add a cookie attribute webId to avoid the appearance of a sliding captcha on the webpage
            await self.browser_context.add_cookies([{
                'name': "webId",
                'value': "xxx123",  # any value
                'domain': ".xiaohongshu.com",
                'path': "/"
            }])
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            # Create a client to interact with the xiaohongshu website.
            self.xhs_client = await self.create_xhs_client(httpx_proxy_format)
            if not await self.xhs_client.pong():
                login_obj = XiaoHongShuLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # input your phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.xhs_client.update_cookies(browser_context=self.browser_context)
            
            crawler_type_var.set(config.CRAWLER_TYPE)
            # await self.search('喜德盛')
            # await self.test_comment()
            await self.test_publish_note()
            utils.logger.info("[TestXiaoHongShuClient.start] Xhs Client finished ...")
    async def search(self, keyword):
        notes_res = await self.xhs_client.get_note_by_keyword(
                        keyword=keyword,
                        page=1,
                        sort=SearchSortType(config.SORT_TYPE) if config.SORT_TYPE != '' else SearchSortType.GENERAL,
                    )
        print(notes_res)

    async def test_comment(self):
        response = await self.xhs_client.post_comment_by_note_id('66ba1f44000000001e0196cb', '这是虫子发来的贺电')
        print(response)
    
    async def test_publish_note(self):
        await self.xhs_client.pos_sns_note("C:/Users/Administrator/Downloads/00022-1487445918.png", "SD生成的图片", "还是挺有意思的")
        return
    

                

async def main():
    cli = TestXiaoHongShuClient()
    await cli.start()
    return

if __name__ == '__main__':
    try:
        logging.basicConfig(level=logging.DEBUG)
        # asyncio.run(main())
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        sys.exit()