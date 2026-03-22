from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


ALLOWED_TASK_TYPES = {
    "summarize_document",
    "extract_fields",
    "extract_and_fill",
}

ALLOWED_ACTIONS = {
    "analyze_template",
    "read_document",
    "extract_fields",
    "extract_for_template",
    "summarize_document",
    "fill_template",
    "verify_document",
    "save_document",
}


ALLOWED_TASK_TYPES = {
    "summarize_document",
    "extract_fields",
    "extract_and_fill",
}

ALLOWED_ACTIONS = {
    "read_document",
    "extract_fields",
    "summarize_document",
    "fill_template",
    "verify_document",
    "save_document",
}

ALLOWED_FILE_ROLES = {"source", "template", "reference"}


@dataclass
class PlannerFileContext:
    file_id: str
    filename: str
    file_type: str
    extension: str
    role_hint: Optional[str] = None
    content_preview: str = ""


@dataclass
class PlannerContext:
    user_prompt: str
    files: List[PlannerFileContext] = field(default_factory=list)

@dataclass
class PlanStep:
    step_id: str
    action: str
    description: str = ""
    file_role: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)


@dataclass
class Plan:
    version: str
    task_type: str
    summary: str
    file_roles: Dict[str, str] = field(default_factory=dict)   # file_id -> role
    steps: List[PlanStep] = field(default_factory=list)
    raw_llm_output: Optional[Dict[str, Any]] = None


class WorkflowPlanner:
    def __init__(self, llm_client: Any):
        self.llm = llm_client

    def create_plan(self, context: PlannerContext) -> Plan:
        planner_input = self.build_planner_context(context)

        draft = self.generate_plan_draft_with_llm(planner_input)

        if draft is not None:
            plan = self.validate_and_repair_plan(draft, context)
            if plan is not None:
                return plan

        return self.fallback_plan(context)

    def build_planner_context(self, context: PlannerContext) -> Dict[str, Any]:
        return {
            "user_prompt": context.user_prompt,
            "available_task_types": sorted(ALLOWED_TASK_TYPES),
            "available_actions": sorted(ALLOWED_ACTIONS),
            "available_file_roles": sorted(ALLOWED_FILE_ROLES),
            "files": [
                {
                    "file_id": f.file_id,
                    "filename": f.filename,
                    "file_type": f.file_type,
                    "extension": f.extension,
                    "role_hint": f.role_hint,
                    "content_preview": f.content_preview,
                }
                for f in context.files
            ],
        }

    def generate_plan_draft_with_llm(
        self,
        planner_input: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(planner_input)

        try:
            raw = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0,
            )
        except Exception:
            return None

        return self._parse_llm_json(raw)

    def _build_system_prompt(self) -> str:
        return """
    You are the central planner of an Office Agent.

    You must do three things:
    1. Infer the role of each file.
    2. Choose the correct task type.
    3. Generate a complete execution plan.

    Strict rules:
    - Output JSON only.
    - file role must be one of:
    source
    template
    reference

    - task_type must be one of:
    summarize_document
    extract_fields
    extract_and_fill

    - step.action must be one of:
    analyze_template
    read_document
    extract_fields
    extract_for_template
    summarize_document
    fill_template
    verify_document
    save_document

    - Do not invent new file roles.
    - Do not invent new task types.
    - Do not invent new actions.
    - Do not output markdown.
    - Do not output explanations outside JSON.
    """.strip()

    def _build_user_prompt(self, planner_input: Dict[str, Any]) -> str:
        return f"""
    Generate the execution plan as JSON.

    Planner input:
    {json.dumps(planner_input, ensure_ascii=False, indent=2)}

    Required JSON schema:
    {{
    "task_type": "extract_and_fill",
    "summary": "Short summary of the plan",
    "file_roles": {{
        "file_1": "source",
        "file_2": "source",
        "file_3": "template"
    }},
    "steps": [
        {{
        "step_id": "step_1",
        "action": "analyze_template",
        "description": "Analyze the template and extract placeholders",
        "file_role": "template",
        "depends_on": []
        }},
        {{
        "step_id": "step_2",
        "action": "read_document",
        "description": "Read all source/reference documents",
        "file_role": "source",
        "depends_on": ["step_1"]
        }},
        {{
        "step_id": "step_3",
        "action": "extract_for_template",
        "description": "Generate final fill values for the template placeholders",
        "file_role": "source",
        "depends_on": ["step_2"]
        }}
    ]
    }}

    Planning guidance:
    - Infer file roles from filename, content preview, and user prompt together.
    - Files containing placeholders like {{{{name}}}} are likely templates.
    - Files with narrative content, records, or source material are usually source.
    - Supporting material that helps understanding but is not the main source can be reference.
    - If the user asks for summary, prefer summarize_document.
    - If the user asks for structured information only, prefer extract_fields.
    - If the user asks to fill one document using other documents, prefer extract_and_fill.
    - If task_type is extract_and_fill and a template file exists, prefer this workflow:
    analyze_template
    -> read_document
    -> extract_for_template
    -> fill_template
    -> verify_document
    -> save_document
    - Steps must be minimal but complete.
    """.strip()

    def _parse_llm_json(self, llm_text: str) -> Optional[Dict[str, Any]]:
        if not llm_text or not isinstance(llm_text, str):
            return None

        text = llm_text.strip()

        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced_match:
            candidate = fenced_match.group(1).strip()
            try:
                data = json.loads(candidate)
                return data if isinstance(data, dict) else None
            except Exception:
                pass

        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except Exception:
            pass

        candidate = self._extract_first_json_object(text)
        if candidate:
            try:
                data = json.loads(candidate)
                return data if isinstance(data, dict) else None
            except Exception:
                return None

        return None

    def _extract_first_json_object(self, text: str) -> Optional[str]:
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False

        for i in range(start, len(text)):
            ch = text[i]

            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        return None

    def validate_and_repair_plan(
        self,
        draft: Dict[str, Any],
        context: PlannerContext,
    ) -> Optional[Plan]:
        if not isinstance(draft, dict):
            return None

        repaired = self.repair_plan_dict(draft, context)

        if not self.is_valid_plan_dict(repaired, context):
            return None

        return self.to_plan(repaired)

    def repair_plan_dict(
        self,
        draft: Dict[str, Any],
        context: PlannerContext,
    ) -> Dict[str, Any]:
        repaired = dict(draft)

        task_type = repaired.get("task_type")
        if task_type not in ALLOWED_TASK_TYPES:
            repaired["task_type"] = self._infer_task_type_by_rules(context)

        raw_file_roles = repaired.get("file_roles")
        if not isinstance(raw_file_roles, dict):
            repaired["file_roles"] = self._infer_file_roles_by_rules(context)
        else:
            repaired["file_roles"] = self._repair_file_roles(raw_file_roles, context)

        raw_steps = repaired.get("steps", [])
        repaired_steps: List[Dict[str, Any]] = []

        for i, step in enumerate(raw_steps, start=1):
            if not isinstance(step, dict):
                continue

            action = step.get("action")
            if action not in ALLOWED_ACTIONS:
                continue

            repaired_steps.append({
                "step_id": step.get("step_id") or f"step_{i}",
                "action": action,
                "description": step.get("description", ""),
                "file_role": step.get("file_role"),
                "depends_on": step.get("depends_on", []),
            })

        repaired["steps"] = self._repair_steps_by_task_type(
            task_type=repaired["task_type"],
            steps=repaired_steps,
        )

        if not repaired.get("summary"):
            repaired["summary"] = f"Auto-generated plan for {repaired['task_type']}"

        return repaired

    def _repair_file_roles(
        self,
        file_roles: Dict[str, str],
        context: PlannerContext,
    ) -> Dict[str, str]:
        valid_ids = {f.file_id for f in context.files}
        repaired: Dict[str, str] = {}

        for file_id, role in file_roles.items():
            if file_id not in valid_ids:
                continue
            if role not in ALLOWED_FILE_ROLES:
                continue
            repaired[file_id] = role

        if not repaired:
            return self._infer_file_roles_by_rules(context)

        template_count = sum(1 for r in repaired.values() if r == "template")
        if template_count > 1:
            # 保留第一个 template，其他降为 source
            seen_template = False
            for file_id, role in list(repaired.items()):
                if role == "template":
                    if not seen_template:
                        seen_template = True
                    else:
                        repaired[file_id] = "source"

        return repaired

    def is_valid_plan_dict(
        self,
        draft: Dict[str, Any],
        context: PlannerContext,
    ) -> bool:
        if draft.get("task_type") not in ALLOWED_TASK_TYPES:
            return False

        if not isinstance(draft.get("file_roles"), dict):
            return False

        steps = draft.get("steps")
        if not isinstance(steps, list) or not steps:
            return False

        for step in steps:
            if not isinstance(step, dict):
                return False
            if step.get("action") not in ALLOWED_ACTIONS:
                return False

        return True

    def to_plan(self, draft: Dict[str, Any]) -> Plan:
        steps = [
            PlanStep(
                step_id=step["step_id"],
                action=step["action"],
                description=step.get("description", ""),
                file_role=step.get("file_role"),
                depends_on=step.get("depends_on", []),
            )
            for step in draft.get("steps", [])
        ]

        return Plan(
            version="v1",
            task_type=draft["task_type"],
            summary=draft.get("summary", ""),
            file_roles=draft.get("file_roles", {}),
            steps=steps,
            raw_llm_output=draft,
        )

    def fallback_plan(self, context: PlannerContext) -> Plan:
        task_type = self._infer_task_type_by_rules(context)
        file_roles = self._infer_file_roles_by_rules(context)
        steps = self._default_steps_for_task_type(task_type)

        return Plan(
            version="v1",
            task_type=task_type,
            summary=f"Fallback plan for {task_type}",
            file_roles=file_roles,
            steps=steps,
            raw_llm_output=None,
        )

    def _infer_task_type_by_rules(self, context: PlannerContext) -> str:
        prompt = context.user_prompt.lower()

        if any(k in prompt for k in ["总结", "概括", "摘要", "summarize", "summary"]):
            return "summarize_document"

        if any(k in prompt for k in ["填写", "填入", "填表", "模板", "fill"]):
            return "extract_and_fill"

        if any(k in prompt for k in ["提取", "抽取", "识别", "extract"]):
            return "extract_fields"

        if len(context.files) >= 2:
            return "extract_and_fill"

        return "summarize_document"

    def _infer_file_roles_by_rules(self, context: PlannerContext) -> Dict[str, str]:
        roles: Dict[str, str] = {}

        if len(context.files) == 1:
            roles[context.files[0].file_id] = "source"
            return roles

        template_keywords = ["template", "模板", "空表", "样表", "审核表", "申请表"]

        template_idx = None
        for i, f in enumerate(context.files):
            name = f.filename.lower()
            preview = (f.content_preview or "").lower()

            if any(k in name for k in template_keywords) or "{{" in preview:
                template_idx = i
                break

        for i, f in enumerate(context.files):
            if template_idx is not None and i == template_idx:
                roles[f.file_id] = "template"
            else:
                roles[f.file_id] = "source"

        return roles

    def _default_steps_for_task_type(self, task_type: str) -> List[PlanStep]:
        if task_type == "summarize_document":
            return [
                PlanStep("step_1", "read_document", "Read source document(s)", "source", []),
                PlanStep("step_2", "summarize_document", "Summarize source document(s)", "source", ["step_1"]),
            ]

        if task_type == "extract_fields":
            return [
                PlanStep("step_1", "read_document", "Read source document(s)", "source", []),
                PlanStep("step_2", "extract_fields", "Extract structured fields", "source", ["step_1"]),
            ]

        if task_type == "extract_and_fill":
            return [
                PlanStep("step_1", "analyze_template", "Analyze the template and extract placeholders", "template", []),
                PlanStep("step_2", "read_document", "Read source document(s)", "source", ["step_1"]),
                PlanStep("step_3", "extract_for_template", "Generate final fill values for template placeholders", "source", ["step_2"]),
                PlanStep("step_4", "fill_template", "Fill template document", "template", ["step_3"]),
                PlanStep("step_5", "verify_document", "Verify output document", "template", ["step_4"]),
                PlanStep("step_6", "save_document", "Save output document", "template", ["step_5"]),
            ]

        return [PlanStep("step_1", "read_document", "Read source document", "source", [])]

    def _repair_steps_by_task_type(
        self,
        task_type: str,
        steps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        required_actions_map = {
            "summarize_document": [
                "read_document",
                "summarize_document",
            ],
            "extract_fields": [
                "read_document",
                "extract_fields",
            ],
            "extract_and_fill": [
                "analyze_template",
                "read_document",
                "extract_for_template",
                "fill_template",
                "verify_document",
                "save_document",
            ],
        }

        required_actions = required_actions_map.get(task_type, ["read_document"])
        existing_actions = [s["action"] for s in steps]
        repaired = list(steps)

        for action in required_actions:
            if action not in existing_actions:
                repaired.append({
                    "step_id": f"step_{len(repaired) + 1}",
                    "action": action,
                    "description": f"Auto-added step: {action}",
                    "file_role": self._default_file_role_for_action(action),
                    "depends_on": [],
                })

        order_map = {action: idx for idx, action in enumerate(required_actions)}
        repaired.sort(key=lambda s: order_map.get(s["action"], 999))

        for i, step in enumerate(repaired):
            step["step_id"] = f"step_{i + 1}"
            step["depends_on"] = [] if i == 0 else [f"step_{i}"]
            if not step.get("file_role"):
                step["file_role"] = self._default_file_role_for_action(step["action"])

        return repaired

    def _default_file_role_for_action(self, action: str) -> Optional[str]:
        if action == "analyze_template":
            return "template"
        if action in {"read_document", "extract_fields", "extract_for_template", "summarize_document"}:
            return "source"
        if action in {"fill_template", "verify_document", "save_document"}:
            return "template"
        return None