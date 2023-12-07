import pytest
import sys
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

#
# @pytest.fixture(scope="session")
# def browser_context_args(
#     pytestconfig: Any,
#     playwright: Playwright,
#     device: Optional[str],
#     base_url: Optional[str],
# ) -> Dict:
#     context_args = {}
#     if device:
#         context_args.update(playwright.devices[device])
#     if base_url:
#         context_args["base_url"] = base_url
#
#     video_option = pytestconfig.getoption("--video")
#     capture_video = video_option in ["on", "retain-on-failure"]
#     if capture_video:
#         context_args["record_video_dir"] = artifacts_folder.name
#
#     return context_args


@pytest.fixture(scope="session")
def is_webkit(browser_name: str) -> bool:
    return browser_name == "webkit"


@pytest.fixture(scope="session")
def is_firefox(browser_name: str) -> bool:
    return browser_name == "firefox"


@pytest.fixture(scope="session")
def is_chromium(browser_name: str) -> bool:
    return browser_name == "chromium"


@pytest.fixture(scope="session")
def browser_name(pytestconfig: Any) -> Optional[str]:
    # When using unittest.TestCase it won't use pytest_generate_tests
    # For that we still try to give the user a slightly less feature-rich experience
    yield pytestconfig.getoption("--browser")


@pytest.fixture(scope="session")
def browser(pytestconfig,
            browser_name,
            browser_type_launch_args) -> Generator[Browser, None, None]:
    test_id = pytestconfig.getoption("--testIdAttribute")
    pw = sync_playwright().start()
    if test_id:
        pw.selectors.set_test_id_attribute(test_id)
    browser_launch_options = {}
    headed_option = pytestconfig.getoption("--headed")
    if headed_option:
        browser_launch_options["headless"] = False
    elif sys.gettrace():
        # When debugger is attached, then launch the browser headed by default
        browser_launch_options["headless"] = False
    slowmo_option = pytestconfig.getoption("--slowmo")
    if slowmo_option:
        browser_launch_options["slow_mo"] = slowmo_option
    browser = getattr(pw, browser_name).launch(**browser_type_launch_args)
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture
def context(
    browser: Browser,
    browser_context_args: Dict,
    pytestconfig: Any,
    request: pytest.FixtureRequest,
) -> Generator[BrowserContext, None, None]:
    pages: List[Page] = []

    browser_context_args = browser_context_args.copy()
    context_args_marker = next(request.node.iter_markers("browser_context_args"), None)
    additional_context_args = context_args_marker.kwargs if context_args_marker else {}
    browser_context_args.update(additional_context_args)

    context = browser.new_context(**browser_context_args)
    context.on("page", lambda page: pages.append(page))

    tracing_option = pytestconfig.getoption("--tracing")
    capture_trace = tracing_option in ["on", "retain-on-failure"]
    if capture_trace:
        context.tracing.start(
            title=slugify(request.node.nodeid),
            screenshots=True,
            snapshots=True,
            sources=True,
        )

    yield context

    # If request.node is missing rep_call, then some error happened during execution
    # that prevented teardown, but should still be counted as a failure
    failed = request.node.rep_call.failed if hasattr(request.node, "rep_call") else True

    if capture_trace:
        retain_trace = tracing_option == "on" or (
            failed and tracing_option == "retain-on-failure"
        )
        if retain_trace:
            trace_path = _build_artifact_test_folder(pytestconfig, request, "trace.zip")
            context.tracing.stop(path=trace_path)
        else:
            context.tracing.stop()

    screenshot_option = pytestconfig.getoption("--screenshot")
    capture_screenshot = screenshot_option == "on" or (
        failed and screenshot_option == "only-on-failure"
    )
    if capture_screenshot:
        for index, page in enumerate(pages):
            human_readable_status = "failed" if failed else "finished"
            screenshot_path = _build_artifact_test_folder(
                pytestconfig, request, f"test-{human_readable_status}-{index+1}.png"
            )
            try:
                page.screenshot(
                    timeout=5000,
                    path=screenshot_path,
                    full_page=pytestconfig.getoption("--full-page-screenshot"),
                )
            except Error:
                pass

    context.close()

    video_option = pytestconfig.getoption("--video")
    preserve_video = video_option == "on" or (
        failed and video_option == "retain-on-failure"
    )
    if preserve_video:
        for page in pages:
            video = page.video
            if not video:
                continue
            try:
                video_path = video.path()
                file_name = os.path.basename(video_path)
                video.save_as(
                    path=_build_artifact_test_folder(pytestconfig, request, file_name)
                )
            except Error:
                # Silent catch empty videos.
                pass


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("playwright", "Playwright")
    group.addoption(
        "--baseUrl",
        help="指定Playwright page.goto默认域名.",
    )
    group.addoption(
        "--browser",
        default="chromium",
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
        "--tracing",
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
