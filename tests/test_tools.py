import pytest
from jarvis.skills.tools import ToolsSkill
import time

@pytest.fixture
def skill():
    return ToolsSkill()

def test_calculator(skill):
    result = skill.execute_action("calculate", {"expression": "100 * 5"})
    assert "500" in result
    
    result = skill.execute_action("calculate", {"expression": "10 / 2"})
    assert "5" in result
    
    result = skill.execute_action("calculate", {"expression": "2 + 2 * 10"})
    assert "22" in result

def test_duration_parsing(skill):
    assert skill._parse_duration("10 minutes") == 600
    assert skill._parse_duration("1 hour") == 3600
    assert skill._parse_duration("5 seconds") == 5
    assert skill._parse_duration("1 hour 30 minutes") == 5400
    assert skill._parse_duration("90") == 5400  # Default fallback is minutes

def test_stopwatch(skill):
    assert "started" in skill.execute_action("stopwatch_start", {})
    time.sleep(1.1)
    status = skill.execute_action("stopwatch_stop", {})
    assert "stopped" in status
    assert "1 seconds" in status

def test_async_timer(skill):
    class MockTTS:
        def __init__(self):
            self.triggered = False
            self.msg = ""
        def cb(self, text):
            self.triggered = True
            self.msg = text
            
    mock = MockTTS()
    skill.tts_callback = mock.cb
    
    skill.execute_action("set_timer", {"duration": "1 seconds", "name": "pizza"})
    
    # Wait for background thread to fire
    time.sleep(1.5)
    
    assert mock.triggered, "Callback was not fired by background thread!"
    assert "pizza" in mock.msg
