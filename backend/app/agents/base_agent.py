"""
Sentinel Drain - Base Agent & Google ADK Architecture
Foundation for multi-agent reasoning, tool dispatch, audit logging,
and Gemini LLM integration with deterministic fallback.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional

# Attempt import of google.genai
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

class BaseAgent:
    def __init__(self, agent_name: str, role_description: str):
        self.agent_name = agent_name
        self.role_description = role_description
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = None

        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[{self.agent_name}] Warning initializing Gemini client: {e}")

    def call_llm(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Calls Gemini if configured, otherwise falls back to deterministic engine."""
        if self.client:
            try:
                config = {}
                if system_instruction:
                    config["system_instruction"] = system_instruction

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                print(f"[{self.agent_name}] Gemini API call failed: {e}. Using deterministic reasoning engine.")

        return self.deterministic_reasoning(prompt, system_instruction)

    def deterministic_reasoning(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Override in subclasses to provide structured deterministic responses."""
        return f"[{self.agent_name}] Processed task according to protocol."

    def log_action(
        self,
        incident_id: str,
        action_type: str,
        tool_called: str,
        input_params: Dict[str, Any],
        output_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Logs an agent action / tool invocation to the audit record."""
        return {
            "incident_id": incident_id,
            "agent_name": self.agent_name,
            "action_type": action_type,
            "tool_called": tool_called,
            "input_params": json.dumps(input_params),
            "output_result": json.dumps(output_result),
            "timestamp": time.time()
        }

    def create_evidence(
        self,
        incident_id: str,
        evidence_type: str,
        source: str,
        summary: str,
        data: Dict[str, Any],
        confidence: float
    ) -> Dict[str, Any]:
        """Creates an auditable piece of evidence for the incident record."""
        return {
            "incident_id": incident_id,
            "agent_name": self.agent_name,
            "evidence_type": evidence_type,
            "source": source,
            "summary": summary,
            "data_json": json.dumps(data),
            "confidence": round(confidence, 2),
            "timestamp": time.time()
        }
