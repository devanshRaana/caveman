"""
JARVIS Skill — Browser Automation
Controls Chrome via Selenium for Gmail, WhatsApp, Google Meet, and URL navigation.
"""
import subprocess
import time
import urllib.parse
from jarvis.skills.base import BaseSkill
from jarvis.utils.connectivity import is_online
from jarvis.logger import logger


class BrowserSkill(BaseSkill):
    name = "browser"
    priority = 18

    def __init__(self, memory=None):
        super().__init__(memory)
        self._driver = None

    def can_handle(self, text: str) -> bool:
        triggers = [
            "send email", "send an email", "compose email", "mail to",
            "send whatsapp", "whatsapp message", "message on whatsapp",
            "google meet", "start a meet", "video call", "join meeting",
            "open website", "go to website", "open url", "browse to",
            "scroll down", "go down", "scroll up", "go up",
            "play video", "play the first", "play the second", "play the third",
        ]
        return self._contains_any(text, triggers)

    def execute(self, text: str) -> str:
        return "Browser skill requires action-based execution."

    def execute_action(self, action: str, params: dict) -> str:
        handler = {
            "send_email": self._send_email,
            "send_whatsapp": self._send_whatsapp,
            "start_meet": self._start_meet,
            "start_video_call": self._start_video_call,
            "open_url": self._open_url,
            "youtube_search": self._youtube_search,
            "youtube_play": self._youtube_play,
            "scroll_down": self._scroll_down,
            "scroll_up": self._scroll_up,
        }.get(action)

        if handler:
            return handler(params)
        return f"Unknown browser action: {action}"

    def _get_driver(self):
        """Initialize Selenium WebDriver if not already running."""
        if self._driver:
            try:
                self._driver.title  # Test if driver is still alive
                return self._driver
            except Exception:
                self._driver = None

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            # Use existing Chrome profile so user is already logged in
            user_data_dir = str(
                __import__("pathlib").Path.home()
                / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
            )
            options.add_argument(f"--user-data-dir={user_data_dir}")
            options.add_argument("--profile-directory=Default")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            self._driver.implicitly_wait(10)
            logger.info("BrowserSkill: Chrome WebDriver initialized")
            return self._driver

        except ImportError:
            logger.error("BrowserSkill: selenium or webdriver-manager not installed")
            return None
        except Exception as e:
            logger.error(f"BrowserSkill: WebDriver init failed: {e}")
            # Fallback: try without profile (fresh session)
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options
                from webdriver_manager.chrome import ChromeDriverManager

                options = Options()
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                service = Service(ChromeDriverManager().install())
                self._driver = webdriver.Chrome(service=service, options=options)
                self._driver.implicitly_wait(10)
                logger.info("BrowserSkill: Chrome WebDriver initialized (fresh profile)")
                return self._driver
            except Exception as e2:
                logger.error(f"BrowserSkill: Fallback WebDriver also failed: {e2}")
                return None

    def _open_url(self, params: dict) -> str:
        """Open a URL in Chrome."""
        url = params.get("url", "")
        if not url:
            return "Which website would you like me to open, Sir?"

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        driver = self._get_driver()
        if driver:
            try:
                driver.get(url)
                return f"Opening {url} in Chrome, Sir."
            except Exception as e:
                logger.error(f"BrowserSkill: Selenium URL error: {e}")

        # Try simple browser open first (faster, no Selenium needed)
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "chrome", url],
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return f"Opening {url} in Chrome, Sir."
        except Exception as e:
            return f"I couldn't open the URL, Sir: {e}"

    def _send_email(self, params: dict) -> str:
        """Compose an email in Gmail via Chrome."""
        if not is_online():
            return "I need an internet connection to send emails, Sir."

        to = params.get("to", "")
        subject = params.get("subject", "")
        body = params.get("body", "")

        # Build Gmail compose URL
        gmail_url = "https://mail.google.com/mail/?view=cm"
        if to:
            gmail_url += f"&to={urllib.parse.quote(to)}"
        if subject:
            gmail_url += f"&su={urllib.parse.quote(subject)}"
        if body:
            gmail_url += f"&body={urllib.parse.quote(body)}"

        try:
            # Open Gmail compose with pre-filled fields
            subprocess.Popen(
                ["cmd", "/c", "start", "chrome", gmail_url],
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            response = "I've opened Gmail compose"
            if to:
                response += f" addressed to {to}"
            if subject:
                response += f" with subject '{subject}'"
            response += ", Sir. Please review and hit send."

            logger.info(f"BrowserSkill: Gmail compose opened for {to}")
            return response

        except Exception as e:
            logger.error(f"BrowserSkill: Gmail error: {e}")
            return f"I had trouble opening Gmail, Sir: {e}"

    def _send_whatsapp(self, params: dict) -> str:
        """Send a WhatsApp message via WhatsApp Web."""
        if not is_online():
            return "I need an internet connection for WhatsApp, Sir."

        contact = params.get("contact", "")
        message = params.get("message", "")
        phone = params.get("phone", "")

        if phone:
            # Direct phone number — use wa.me link
            phone_clean = phone.replace("+", "").replace(" ", "").replace("-", "")
            url = f"https://wa.me/{phone_clean}"
            if message:
                url += f"?text={urllib.parse.quote(message)}"

            try:
                subprocess.Popen(
                    ["cmd", "/c", "start", "chrome", url],
                    shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                return f"I've opened WhatsApp Web for {phone}. The message is pre-filled, Sir — just hit send."
            except Exception as e:
                return f"I had trouble opening WhatsApp, Sir: {e}"

        elif contact:
            # Contact name — use Selenium to navigate WhatsApp Web
            driver = self._get_driver()
            if not driver:
                # Fallback: open WhatsApp Web directly
                try:
                    subprocess.Popen(
                        ["cmd", "/c", "start", "chrome", "https://web.whatsapp.com"],
                        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    return f"I've opened WhatsApp Web, Sir. Please search for {contact} and send your message manually."
                except Exception:
                    return "I couldn't open WhatsApp Web, Sir."

            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                driver.get("https://web.whatsapp.com")
                logger.info("BrowserSkill: Navigating to WhatsApp Web")

                # Wait for WhatsApp to load (user may need to scan QR)
                search_box = WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
                    )
                )

                # Search for contact
                search_box.clear()
                search_box.send_keys(contact)
                time.sleep(2)

                # Click on the contact
                contact_elem = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, f'//span[@title="{contact}"]')
                    )
                )
                contact_elem.click()
                time.sleep(1)

                if message:
                    # Type and send message
                    msg_box = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                        )
                    )
                    msg_box.send_keys(message)
                    msg_box.send_keys(Keys.ENTER)
                    return f"Message sent to {contact} on WhatsApp, Sir."
                else:
                    return f"I've opened the chat with {contact} on WhatsApp, Sir. What would you like to say?"

            except Exception as e:
                logger.error(f"BrowserSkill: WhatsApp automation error: {e}")
                return f"I had some trouble with WhatsApp automation, Sir. I've opened WhatsApp Web — you may need to find {contact} manually."

        else:
            # No contact info — just open WhatsApp Web
            try:
                subprocess.Popen(
                    ["cmd", "/c", "start", "chrome", "https://web.whatsapp.com"],
                    shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                return "I've opened WhatsApp Web, Sir. Who would you like to message?"
            except Exception:
                return "I couldn't open WhatsApp Web, Sir."

    def _start_meet(self, params: dict) -> str:
        """Start or join a Google Meet."""
        if not is_online():
            return "I need an internet connection for Google Meet, Sir."

        meeting_link = params.get("meeting_link", "")

        if meeting_link:
            # Join existing meeting
            if "meet.google.com" not in meeting_link:
                meeting_link = f"https://meet.google.com/{meeting_link}"
        else:
            # Start a new meeting
            meeting_link = "https://meet.google.com/new"

        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "chrome", meeting_link],
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            if "new" in meeting_link:
                return "Starting a new Google Meet session, Sir."
            else:
                return f"Joining the Google Meet, Sir."

        except Exception as e:
            return f"I had trouble with Google Meet, Sir: {e}"

    def _start_video_call(self, params: dict) -> str:
        """Start a video call on the specified platform."""
        platform = params.get("platform", "meet").lower()
        contact = params.get("contact", "")

        if "whatsapp" in platform:
            if contact:
                return self._send_whatsapp({"contact": contact, "message": ""})
            else:
                try:
                    subprocess.Popen(
                        ["cmd", "/c", "start", "chrome", "https://web.whatsapp.com"],
                        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    return "I've opened WhatsApp Web for a video call, Sir. Please select the contact and start the call."
                except Exception:
                    return "I couldn't open WhatsApp Web, Sir."
        else:
            # Default to Google Meet
            return self._start_meet(params)

    def cleanup(self):
        """Close the WebDriver."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def _youtube_search(self, params: dict) -> str:
        """Search YouTube in Chrome."""
        query = params.get("query", params.get("_raw", ""))
        if not query:
            return "What would you like me to search for on YouTube, Sir?"

        encoded_query = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"

        driver = self._get_driver()
        if driver:
            try:
                driver.get(url)
                logger.info(f"BrowserSkill: YouTube search for '{query}' (Selenium)")
                return f"Searching YouTube for '{query}', Sir."
            except Exception as e:
                logger.error(f"BrowserSkill: Selenium YouTube error: {e}")

        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "chrome", url],
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logger.info(f"BrowserSkill: YouTube search for '{query}' (subprocess)")
            return f"Searching YouTube for '{query}', Sir."
        except Exception as e:
            logger.error(f"BrowserSkill: YouTube error: {e}")
            return f"I couldn't open YouTube, Sir: {e}"

    def _scroll_down(self, params: dict) -> str:
        """Scroll down the current page."""
        driver = self._get_driver()
        if not driver:
            return "Chrome is not currently automated, Sir."
        try:
            driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
            return "Scrolling down, Sir."
        except Exception as e:
            logger.error(f"BrowserSkill: _scroll_down error: {e}")
            return "I couldn't scroll the page, Sir."

    def _scroll_up(self, params: dict) -> str:
        """Scroll up the current page."""
        driver = self._get_driver()
        if not driver:
            return "Chrome is not currently automated, Sir."
        try:
            driver.execute_script("window.scrollBy(0, -window.innerHeight * 0.8);")
            return "Scrolling up, Sir."
        except Exception as e:
            logger.error(f"BrowserSkill: _scroll_up error: {e}")
            return "I couldn't scroll the page, Sir."

    def _youtube_play(self, params: dict) -> str:
        """Play a specific video from YouTube search results."""
        driver = self._get_driver()
        if not driver:
            return "Chrome is not currently automated, Sir."
            
        video_number = params.get("video_number", 1)
        if isinstance(video_number, str):
            try:
                video_number = int(video_number)
            except ValueError:
                video_number = 1
                
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # Wait for search results
            elements = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "ytd-video-renderer a#video-title")
                )
            )
            
            if not elements:
                return "I couldn't find any videos to play, Sir."
                
            idx = video_number - 1
            if idx >= len(elements) or idx < 0:
                idx = 0
                
            target_video = elements[idx]
            
            # Scroll to element to ensure it's clickable and visible
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_video)
            import time
            time.sleep(0.5)
            
            title = target_video.text
            
            # Click the video
            driver.execute_script("arguments[0].click();", target_video)
            
            return f"Playing video number {video_number}: {title}, Sir."
            
        except Exception as e:
            logger.error(f"BrowserSkill: _youtube_play error: {e}")
            return "I couldn't play that video, Sir."
