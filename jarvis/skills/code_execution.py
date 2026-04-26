"""
JARVIS Skill — Code Execution (Open Claw Mode)
Allows JARVIS to write and execute Python code dynamically.
"""
import os
import subprocess
import tempfile
from jarvis.skills.base import BaseSkill
from jarvis.logger import logger


class CodeExecutionSkill(BaseSkill):
    name = "code_execution"
    priority = 10  # High priority for explicit code/automation requests

    def can_handle(self, text: str) -> bool:
        triggers = ["run code", "write a script", "execute python", "open claw", "openclaw", "run a python", "write python"]
        return self._contains_any(text, triggers)

    def execute(self, text: str) -> str:
        return "Code execution requires structured action with a prompt."

    def execute_action(self, action: str, params: dict) -> str:
        prompt = params.get("prompt", "")
        code = params.get("code", "")
        
        if not prompt and not code:
            return "I need instructions or code to execute, Sir."

        if code:
            return self._run_python(code)
            
        return self._generate_and_run(prompt)

    def _generate_and_run(self, prompt: str) -> str:
        try:
            import ollama
            from jarvis.config import CONFIG
            model = CONFIG.get("llm", {}).get("model", "mistral")
            
            system_prompt = """You are JARVIS's code execution engine (Open Claw mode). 
The user wants to perform an offline action or automation. Write ONLY a valid Python script to accomplish this.
DO NOT include any markdown formatting, backticks, explanations, or text outside the code.
Just write the raw python code.
You can use `subprocess`, `os`, `shutil`, `requests`, `pyautogui`, or `pywhatkit` modules.
Example for WhatsApp:
import pywhatkit
pywhatkit.sendwhatmsg_instantly("+1234567890", "message", wait_time=15, tab_close=True, close_time=3)
"""
            
            logger.info(f"Generating code for prompt: {prompt}")
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            
            code = response["message"]["content"].strip()
            
            if code.startswith("```python"):
                code = code[9:]
            elif code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            
            code = code.strip()
            return self._run_python(code)
            
        except Exception as e:
            logger.error(f"CodeExecutionSkill LLM error: {e}")
            return f"I had trouble generating the code, Sir: {e}"

    def _run_python(self, code: str) -> str:
        logger.info(f"Executing Python code:\n{code}")
        
        fd, temp_path = tempfile.mkstemp(suffix=".py")
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(code)
                
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True,
                text=True,
                timeout=45
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if error:
                logger.error(f"Code execution error: {error}")
                return f"The code encountered an error, Sir:\n{error[-200:]}"
                
            if not output:
                return "I've executed the code successfully, Sir, though it didn't produce any console output."
                
            return f"Code executed successfully. Output:\n{output[-300:]}"
            
        except subprocess.TimeoutExpired:
            return "The code execution timed out after 45 seconds, Sir."
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return f"Failed to execute code, Sir: {e}"
        finally:
            try:
                os.remove(temp_path)
            except:
                pass
