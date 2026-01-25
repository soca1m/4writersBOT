"""
Base Agent Class - Following SOLID principles

Single Responsibility: Each agent does ONE thing
Open/Closed: Easy to extend with new agent types
Liskov Substitution: All agents can be used interchangeably
Interface Segregation: Minimal required interface
Dependency Inversion: Depend on abstractions (LLM interface)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path

from src.workflows.state import OrderWorkflowState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the workflow.

    Implements common functionality:
    - State management
    - Logging
    - Error handling
    - LLM interaction patterns
    """

    def __init__(self, agent_name: str, llm_model=None):
        """
        Initialize agent

        Args:
            agent_name: Human-readable agent name for logging
            llm_model: Language model instance (optional)
        """
        self.agent_name = agent_name
        self.llm = llm_model
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")

    @abstractmethod
    async def execute(self, state: OrderWorkflowState) -> Dict[str, Any]:
        """
        Execute agent's primary task

        Args:
            state: Current workflow state

        Returns:
            Updated state dict
        """
        pass

    def log_start(self, order_id: str, extra_info: str = ""):
        """Log agent execution start"""
        msg = f"🤖 {self.agent_name}: Processing order {order_id}"
        if extra_info:
            msg += f" - {extra_info}"
        self.logger.info(msg)
        print(f"\n{'='*80}")
        print(msg)
        print('='*80 + '\n')

    def log_success(self, message: str):
        """Log successful completion"""
        self.logger.info(f"✅ {message}")
        print(f"✅ {message}\n")

    def log_warning(self, message: str):
        """Log warning"""
        self.logger.warning(f"⚠️ {message}")
        print(f"⚠️ {message}\n")

    def log_error(self, message: str):
        """Log error"""
        self.logger.error(f"❌ {message}")
        print(f"❌ {message}\n")

    def update_state(
        self,
        state: OrderWorkflowState,
        status: str,
        **updates
    ) -> Dict[str, Any]:
        """
        Update state with new values and log entry

        Args:
            state: Current state
            status: New status value
            **updates: Additional state updates

        Returns:
            Updated state dict
        """
        # Add agent log entry
        agent_logs = state.get('agent_logs', [])
        log_entry = f"[{self.agent_name}] {status}"

        return {
            **state,
            "status": status,
            "agent_logs": agent_logs + [log_entry],
            **updates
        }

    def handle_error(
        self,
        state: OrderWorkflowState,
        error: Exception,
        error_context: str = ""
    ) -> Dict[str, Any]:
        """
        Standard error handling

        Args:
            state: Current state
            error: Exception that occurred
            error_context: Additional context about the error

        Returns:
            State dict with error status
        """
        error_msg = f"{error_context}: {str(error)}" if error_context else str(error)
        self.log_error(error_msg)

        return self.update_state(
            state,
            status="failed",
            error=error_msg
        )


class PromptBasedAgent(BaseAgent):
    """
    Agent that uses LLM prompts

    Adds prompt loading and LLM invocation helpers
    """

    def __init__(self, agent_name: str, llm_model=None, prompt_file: Optional[str] = None):
        """
        Initialize prompt-based agent

        Args:
            agent_name: Agent name
            llm_model: LLM instance
            prompt_file: Name of prompt file (without .txt extension) or full filename
        """
        super().__init__(agent_name, llm_model)
        self.prompt_file = prompt_file
        self._prompt_template = None

    def load_prompt(self) -> str:
        """
        Load prompt template using PromptManager

        Returns:
            Prompt template string
        """
        if self._prompt_template is None and self.prompt_file:
            from src.services.prompt_manager import PromptManager

            # Remove .txt extension if present
            prompt_name = self.prompt_file.replace('.txt', '')

            self._prompt_template = PromptManager.load(prompt_name)
            self.logger.debug(f"Loaded prompt: {prompt_name}")

        return self._prompt_template or ""

    async def invoke_llm(
        self,
        prompt: str,
        error_context: str = "LLM invocation"
    ) -> Optional[str]:
        """
        Invoke LLM with error handling

        Args:
            prompt: Formatted prompt
            error_context: Context for error messages

        Returns:
            LLM response text or None if error
        """
        # Get LLM instance if not already set
        if not self.llm:
            from src.utils.llm_service import get_smart_model
            self.llm = get_smart_model()

        if not self.llm:
            self.log_error(f"{error_context}: No LLM model available")
            return None

        try:
            response = await self.llm.ainvoke(prompt)
            return response.content.strip()
        except Exception as e:
            self.log_error(f"{error_context}: {e}")
            return None

    def format_prompt(self, template: str, **kwargs) -> str:
        """
        Format prompt template with variables

        Args:
            template: Prompt template string
            **kwargs: Template variables

        Returns:
            Formatted prompt
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            self.log_warning(f"Missing template variable: {e}")
            # Return template with missing variables for debugging
            return template


class ValidationAgent(PromptBasedAgent):
    """
    Agent that validates/checks content

    Adds validation rule management and result parsing
    """

    def __init__(
        self,
        agent_name: str,
        llm_model=None,
        prompt_file: Optional[Path] = None,
        max_attempts: int = 10
    ):
        """
        Initialize validation agent

        Args:
            agent_name: Agent name
            llm_model: LLM instance
            prompt_file: Prompt file path
            max_attempts: Maximum validation attempts
        """
        super().__init__(agent_name, llm_model, prompt_file)
        self.max_attempts = max_attempts

    def check_max_attempts(
        self,
        state: OrderWorkflowState,
        attempt_key: str
    ) -> bool:
        """
        Check if max attempts reached

        Args:
            state: Current state
            attempt_key: State key for attempt counter

        Returns:
            True if max reached, False otherwise
        """
        attempts = state.get(attempt_key, 0)

        if attempts >= self.max_attempts:
            self.log_warning(f"Max attempts ({self.max_attempts}) reached")
            return True

        return False

    def increment_attempts(
        self,
        state: OrderWorkflowState,
        attempt_key: str
    ) -> int:
        """
        Increment attempt counter

        Args:
            state: Current state
            attempt_key: State key for counter

        Returns:
            New attempt count
        """
        attempts = state.get(attempt_key, 0) + 1
        self.logger.debug(f"Attempts: {attempts}/{self.max_attempts}")
        return attempts
