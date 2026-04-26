"""
JARVIS Brain — Command Chain Engine
Executes multi-step command sequences: c1 → c2 → c3
Each step gets context from the previous step's result.
"""
from typing import Optional
from jarvis.logger import logger


class CommandChain:
    """
    Executes a list of action dicts sequentially.
    Passes context (results) from step N to step N+1.
    
    Usage:
        chain = CommandChain(skill_registry, tts)
        chain.execute(steps=[action1, action2, action3])
    """

    def __init__(self, skill_registry, tts=None, speak_fn=None):
        """
        Args:
            skill_registry: The SkillRegistry to dispatch actions through
            tts: TextToSpeech instance (optional)
            speak_fn: Callable to speak and log text (optional)
        """
        self.skills = skill_registry
        self.tts = tts
        self.speak_fn = speak_fn

    def _speak(self, text: str):
        """Speak progress update."""
        if self.speak_fn:
            self.speak_fn(text)
        elif self.tts:
            self.tts.speak(text)

    def execute(self, steps: list[dict]) -> str:
        """
        Execute a chain of action steps sequentially.
        
        Args:
            steps: List of action dicts from IntentRouter
            
        Returns:
            Combined result string from all steps
        """
        total = len(steps)
        if total == 0:
            return "No commands to execute, Sir."

        if total == 1:
            # Single command, just execute normally
            return self.skills.execute_action(steps[0])

        logger.info(f"CommandChain: Executing {total} chained commands")
        self._speak(f"I have {total} tasks to complete, Sir. Starting now.")

        results = []
        context = {}  # Shared context between steps

        for i, step in enumerate(steps, 1):
            action_name = step.get("action", "unknown")
            logger.info(f"CommandChain: Step {i}/{total} — {action_name}")

            # Inject context from previous steps
            if "params" not in step:
                step["params"] = {}
            step["params"]["_chain_context"] = context
            step["params"]["_step_number"] = i
            step["params"]["_total_steps"] = total

            try:
                result = self.skills.execute_action(step)
                results.append(f"Step {i}: {result}")

                # Update context with this step's result
                context[f"step_{i}_action"] = action_name
                context[f"step_{i}_result"] = result
                
                # Carry forward filename/path for file operations
                params = step.get("params", {})
                if "filename" in params:
                    context["last_filename"] = params["filename"]
                if "directory" in params:
                    context["last_directory"] = params["directory"]

                if i < total:
                    self._speak(f"Step {i} complete. Moving to step {i + 1}.")

            except Exception as e:
                error_msg = f"Step {i} failed: {str(e)}"
                logger.error(f"CommandChain: {error_msg}")
                results.append(error_msg)
                self._speak(f"I encountered an error on step {i}, Sir. {str(e)}")
                # Continue with remaining steps unless it's critical
                context[f"step_{i}_error"] = str(e)

        # Final summary
        self._speak(f"All {total} tasks completed, Sir.")
        return "\n".join(results)
