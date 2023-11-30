import pytest
from playwright.sync_api import (
    Browser,
    BrowserType,
    BrowserContext,
    Page,
    Locator,
    Playwright,
    sync_playwright
)
from typing import Any, Callable, Dict, Generator, List, Optional


@pytest.fixture(scope="session")
def playwright(pytestconfig) -> Generator[Playwright, None, None]:
    test_id = pytestconfig.getoption("--output")
    pw = sync_playwright().start()
    if test_id:
        pw.selectors.set_test_id_attribute(test_id)
    yield pw
    pw.stop()


@pytest.fixture(scope="session")
def browser_type(playwright: Playwright, browser_name: str) -> BrowserType:
    return getattr(playwright, browser_name)


@pytest.fixture(scope="session")
def launch_browser(
        browser_type_launch_args: Dict,
        browser_type: BrowserType
) -> Callable[..., Browser]:
    def launch(**kwargs: Dict) -> Browser:
        launch_options = {**browser_type_launch_args, **kwargs}
        browser = browser_type.launch(**launch_options)
        return browser

    return launch


@pytest.fixture(scope="session")
def browser(launch_browser: Callable[[], Browser]) -> Generator[Browser, None, None]:
    browser = launch_browser()
    yield browser
    browser.close()


def context_generator(browser):
    ...


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("playwright", "Playwright")
    group.addoption(
        "--baseUrl",
        help="指定Playwright page.goto默认域名.",
    )
    group.addoption(
        "--browser",
        action="append",
        default=["chromium"],
        help="指定用例执行所使用浏览器.",
        choices=["chromium", "firefox", "webkit"],
    )
    group.addoption(
        "--actionTimeout",
        help="click及fill等操作的超时时间.\n"
             "https://playwright.dev/python/docs/api/class-browsercontext#browser-context-set-default-timeout",
        default=30 * 1000,
        type=int
    )
    group.addoption(
        "--navigationTimeout",
        help="page.goto及page.reload等操作超时时间.\n"
             "https://playwright.dev/python/docs/api/class-browsercontext#browser-context-set-default-navigation-timeout",
        default=60 * 1000,
        type=int
    )
    group.addoption(
        "--testIdAttribute",
        help="自定义test id.\n"
             "https://playwright.dev/python/docs/api/class-selectors#selectors-set-test-id-attribute",
        default="data-tester-id",
        type=str
    )
    group.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="使用headed模式执行用例.",
    )
    group.addoption(
        "--slowmo",
        default=0,
        type=int,
        help="使用slow mo执行用例",
    )
    group.addoption(
        "--output",
        default="test-results",
        help="存储video等playwright临时文件的目录.",
    )
    group.addoption(
        "--trace",
        default="off",
        choices=["on", "off", "retain-on-failure"],
        help="是否生成tracing.",
    )
    group.addoption(
        "--video",
        default="off",
        choices=["on", "off", "retain-on-failure"],
        help="是否生成video.",
    )
    group.addoption(
        "--viewportWidth",
        default=1580,
        type=int,
        help="浏览器窗口宽度.",
    )
    group.addoption(
        "--viewportHeight",
        default=740,
        type=int,
        help="浏览器窗口高度.",
    )
