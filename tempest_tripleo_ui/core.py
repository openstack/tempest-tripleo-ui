import logging
from selenium.common import exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support import select
from selenium.webdriver.support import ui
from tempest_tripleo_ui import browser
from tempest_tripleo_ui.decorators import selenium_action
from time import sleep

logger = logging.getLogger(__name__)


class Identifier(object):
    def __init__(self, by, identifier):
        self.by = by
        self.identifier = identifier

    @classmethod
    def xpath(cls, locator):
        return Identifier(By.XPATH, locator)

    @classmethod
    def css_selector(cls, locator):
        return Identifier(By.CSS_SELECTOR, locator)

    @classmethod
    def id(cls, locator):
        return Identifier(By.ID, locator)

    @classmethod
    def class_name(cls, locator):
        return Identifier(By.CLASS_NAME, locator)

    @classmethod
    def link_text(cls, locator):
        return Identifier(By.LINK_TEXT, locator)


class SeleniumElement(object):

    def __init__(self,
                 identifier=None,
                 webelement=None,
                 session=None):
        self.identifier = identifier
        self.webelement = webelement
        self.session = session

    @classmethod
    def by_id(cls, name):
        return SeleniumElement(Identifier(By.ID, name))

    @classmethod
    def by_class(cls, name):
        return SeleniumElement(Identifier(By.CLASS_NAME, name))

    @classmethod
    def by_css(cls, name):
        return SeleniumElement(Identifier(By.CSS_SELECTOR, name))

    @classmethod
    def by_xpath(cls, name):
        return SeleniumElement(Identifier(By.XPATH, name))

    @classmethod
    def by_link_text(cls, name):
        return SeleniumElement(Identifier(By.LINK_TEXT, name))

    @classmethod
    def by_element(cls, elem, browser_session):
        new_elem = SeleniumElement(webelement=elem, session=browser_session)
        return new_elem

    def get_element(self):
        if self.webelement and \
                self.session == browser.get_browser().get_session():
            return self.webelement

        elem = self.wait_for_element()
        if elem is None:
            logger.error("can't find element: {}".format(
                self.get_identifier_string()))

        return elem

    def get_identifier_string(self):
        name = "No identifier"
        if self.identifier:
            name = self.identifier.identifier
        return name

    def wait_for_element(self, timeout_in_seconds=10):
        if self.identifier is None:
            logger.warning("wait_for_element() is irrelevant for elements "
                           "that were not found via an identifier")
            return self.webelement

        try:
            self.webelement = ui.WebDriverWait(
                browser.get_browser().get_driver(),
                timeout_in_seconds).until(
                    EC.presence_of_element_located(
                        (self.identifier.by, self.identifier.identifier))
            )
            self.session = browser.get_browser().get_session()
            return self.webelement
        except exceptions.TimeoutException:
            return None     # because the element is not found

    def wait_for_present_text(self, text, timeout_in_seconds=10):
        try:
            if self.identifier is None:
                logger.warning(
                    'wait_for_present_text will not work properly, '
                    'because there is missing .identifier.')
            self.webelement = ui.WebDriverWait(
                browser.get_browser().get_driver(),
                timeout_in_seconds).until(
                EC.text_to_be_present_in_element(
                    (self.identifier.by, self.identifier.identifier), text)
            )
            return self.webelement
        except exceptions.TimeoutException:
            return None

    def wait_for_staleness(self, timeout_in_seconds=10):
        if self.webelement is None:
            logger.warning("wait_for_staleness() is irrelevant for elements "
                           "that were not found yet")
            return True

        try:
            return ui.WebDriverWait(browser.get_browser().get_driver(),
                                    timeout_in_seconds).until(
                                        EC.staleness_of(self.webelement))
        except exceptions.TimeoutException:
            return None

    def is_stale(self):
        try:
            self.webelement.is_enabled()
            return False
        except exceptions.StaleElementReferenceException:
            return True
        except exceptions.WebDriverException:
            return False

    @selenium_action
    def is_visible(self, webelement):
        return webelement.is_displayed()

    @selenium_action
    def is_selected(self, webelement):
        return webelement.is_selected()

    @selenium_action
    def is_enabled(self, webelement):
        return webelement.is_enabled()

    @selenium_action
    def get_tag_name(self, webelement):
        return webelement.tag_name

    @selenium_action
    def get_text(self, webelement):
        return webelement.text

    def get_all_text(self):
        text = self.get_text()
        if text is None or len(text) == 0:
            text = ""

        child_elements = self.find_child_elements(Identifier.xpath("*"))
        if child_elements is not None and len(child_elements) > 0:
            for child_element in child_elements:
                child_text = child_element.get_all_text()
                if child_text is not None and len(child_text) > 0:
                    if len(text) > 0:
                        text = text + " " + child_text
                    else:
                        text = child_text
        return text

    @selenium_action
    def get_id(self, webelement):
        return webelement.get_attribute("id")

    @selenium_action
    def get_name(self, webelement):
        return webelement.get_attribute("name")

    @selenium_action
    def get_value(self, webelement):
        return webelement.get_attribute("value")

    @selenium_action
    def get_class(self, webelement):
        return webelement.get_attribute("class")

    @selenium_action
    def get_href(self, webelement):
        return webelement.get_attribute("href")

    @selenium_action
    def get_title(self, webelement):
        return webelement.get_attribute("title")

    @selenium_action
    def click_minimum_retries(self, webelement):
        webelement.click()

    # this WON'T be a @selenium_action because we're handling retries
    # internally
    def click(self, use_js=False):

        # try to click and catch exception
        try:
            self.click_minimum_retries()
            return True
        except exceptions.WebDriverException:
            pass

        sleep(1)

        # click failed - scroll the item into view (bottom) and try again
        try:
            self.scroll_into_view(False)
            self.click_minimum_retries()
            return True
        except exceptions.WebDriverException:
            pass

        sleep(1)

        # click failed again - scroll the item into view (top) and try again
        try:
            self.scroll_into_view(True)
            self.click_minimum_retries()
            return True
        except exceptions.WebDriverException:
            pass

        if use_js:
            try:
                logger.warning("almost giving up on all click attempts !!")
                browser.get_browser().save_screenshot()

                browser.get_browser().get_driver().execute_script(
                    'return arguments[0].click();', self.get_element()
                )

                logger.warning(
                    "click was successful only when using "
                    "javascript... {}".format(self.get_identifier_string()))
                sleep(1)
                browser.get_browser().save_screenshot()
                return True
            except BaseException:
                logger.warning(
                    "click was unsuccessful even with javascript! {}".format(
                        self.get_identifier_string()))

        # all failed...
        logger.error(
            "all click attempts failed on: {}".format(
                self.get_identifier_string()))
        return False

    @selenium_action
    def click_at_offset(self, webelement, x, y):
        actions = webdriver.ActionChains(browser.get_browser().get_driver())
        actions.move_to_element_with_offset(webelement, x, y)
        actions.click()
        return actions.perform()

    @selenium_action
    def move_to(self, webelement):
        actions = webdriver.ActionChains(browser.get_browser().get_driver())
        actions.move_to_element(webelement)
        actions.perform()

    @selenium_action
    def scroll_into_view(self, webelement, align_to_top=True):
        driver = browser.get_browser().get_driver()
        if align_to_top:
            driver.execute_script(
                "arguments[0].scroll_into_view(true);", webelement)
        else:
            driver.execute_script(
                "arguments[0].scroll_into_view(false);", webelement)

    @selenium_action
    def submit(self, webelement):
        return webelement.submit()

    @selenium_action
    def clear(self, webelement):
        webelement.clear()
        return webelement.get_attribute('value') == ''

    @selenium_action
    def send_keys(self, webelement, text, tokenize=True):
        text = "{}".format(text)
        if not tokenize:
            webelement.send_keys(text)
            return

        # don't send more than 40 characters at a time, as it
        # can hang some scripts
        token_size = 40
        while len(text) > 0:
            webelement.send_keys(text[:token_size])
            text = text[token_size:]

    @selenium_action
    def send_ctrl_something(self, webelement, key):
        return webelement.send_keys(Keys.CONTROL, self.key)

    # start xpath with ".//"
    @selenium_action
    def find_child_elements(self, webelement, identifier):
        elements = None
        try:
            elements = webelement.find_elements(
                by=self.identifier.by,
                value=self.identifier.identifier)
        except BaseException:
            return None

        if elements is not None:
            ret = []
            for child_element in elements:
                ret.append(SeleniumElement.by_element(child_element,
                                                      self.session))
            return ret

    def drag_and_drop(self, target):
        if self.is_visible() and target.is_visible():
            elem_from = self.get_element()
            elem_to = target.get_element()
            if elem_from and elem_to:
                webdriver.ActionChains(
                    browser.get_browser().get_driver().drag_and_drop(
                        elem_from, elem_to).perform())
        else:
            logger.error("drag-n-drop: items are not visible")

    @selenium_action
    def deselect_all(self, webelement):
        sel = select.Select(webelement)
        return sel.deselect_all()

    @selenium_action
    def select_by_index(self, webelement, index):
        sel = select.Select(webelement)
        return sel.select_by_index(index)

    @selenium_action
    def select_by_value(self, webelement, value):
        sel = select.Select(webelement)
        return sel.select_by_value(value)

    @selenium_action
    def select_by_visible_text(self, webelement, value):
        sel = select.Select(webelement)
        return sel.select_by_visible_text(value)

    @selenium_action
    def deselect_by_index(self, webelement, index):
        sel = select.Select(webelement)
        return sel.deselect_by_index(index)

    @selenium_action
    def deselect_by_value(self, webelement, value):
        sel = select.Select(webelement)
        return sel.deselect_by_value(value)

    @selenium_action
    def deselect_by_visible_text(self, webelement, value):
        sel = select.Select(webelement)
        return sel.deselect_by_visible_text(value)


def selenium_elements(identifier):
    elements = []
    current_browser = browser.get_browser()
    browser_session = current_browser.get_session()
    results = current_browser.get_driver().find_elements(
        by=identifier.by, value=identifier.identifier)
    for elem in results:
        elements.append(SeleniumElement.by_element(elem, browser_session))
    return elements
