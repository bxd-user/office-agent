from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type


class FileType(str, Enum):
    """抽象文件类型，用于工具路由和能力声明。"""

    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    PDF = "pdf"
    TEXT = "text"
    CSV = "csv"
    IMAGE = "image"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


class Capability(str, Enum):
    """工具能力标签。

    后续 runtime / registry 可以按 capability 查找合适工具，
    而不是把逻辑写死在 if/else 里。
    """

    READ = "read"
    WRITE = "write"
    INSPECT = "inspect"
    EXTRACT = "extract"
    REPLACE = "replace"
    FILL_TEMPLATE = "fill_template"
    VALIDATE = "validate"
    EXPORT = "export"
    CONVERT = "convert"


@dataclass(slots=True)
class ToolContext:
    """工具执行时的上下文。

    这里不放具体业务逻辑，只放执行期公共信息。
    后面可以继续扩展 trace_id、artifact_store、config 等。
    """

    task_id: str
    working_dir: str
    temp_dir: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        """向上下文追加一条日志。"""
        self.logs.append(message)


@dataclass(slots=True)
class ToolArtifact:
    """工具执行产生的附加产物。

    示例：
    - 输出文件路径
    - 中间快照
    - 导出的 PDF
    - 调试用结构化 JSON
    """

    name: str
    path: Optional[str] = None
    type: Optional[str] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    """统一的工具返回结果。

    所有工具都尽量返回这个结构，避免不同工具返回风格混乱。
    """

    success: bool
    data: Any = None
    message: str = ""
    error: Optional[str] = None
    artifacts: List[ToolArtifact] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        data: Any = None,
        message: str = "",
        artifacts: Optional[List[ToolArtifact]] = None,
        logs: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ToolResult":
        return cls(
            success=True,
            data=data,
            message=message,
            artifacts=artifacts or [],
            logs=logs or [],
            metadata=metadata or {},
        )

    @classmethod
    def fail(
        cls,
        error: str,
        message: str = "",
        data: Any = None,
        logs: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ToolResult":
        return cls(
            success=False,
            data=data,
            message=message,
            error=error,
            logs=logs or [],
            metadata=metadata or {},
        )


@dataclass(slots=True)
class ToolInput:
    """所有工具输入参数模型的最小基类。

    现在先用 dataclass。
    以后如果你想切到 pydantic，也可以保持接口不变。
    """

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ToolError(Exception):
    """工具基类异常。"""


class ToolValidationError(ToolError):
    """工具输入校验失败。"""


class ToolExecutionError(ToolError):
    """工具执行失败。"""


class BaseTool(ABC):
    """所有工具的统一父类。

    设计原则：
    1. 工具只做原子能力
    2. 工具不负责跨文件业务决策
    3. 工具统一输入、输出、日志和异常风格
    """

    name: str = ""
    description: str = ""
    supported_file_types: tuple[FileType, ...] = ()
    capabilities: tuple[Capability, ...] = ()

    @property
    @abstractmethod
    def input_model(self) -> Type[ToolInput]:
        """返回该工具对应的输入参数模型类型。"""
        raise NotImplementedError

    def validate_input(self, params: ToolInput) -> None:
        """基础输入校验。

        子类可以覆盖以实现更严格的检查。
        """
        if not isinstance(params, self.input_model):
            raise ToolValidationError(
                f"{self.name}: invalid input type, expected "
                f"{self.input_model.__name__}, got {type(params).__name__}"
            )

    def can_handle_file_type(self, file_type: FileType) -> bool:
        """判断工具是否支持某种抽象文件类型。"""
        if not self.supported_file_types:
            return False
        return file_type in self.supported_file_types

    def has_capability(self, capability: Capability) -> bool:
        """判断工具是否声明了某种能力。"""
        return capability in self.capabilities

    def execute_safe(self, params: ToolInput, ctx: ToolContext) -> ToolResult:
        """统一包装执行逻辑。

        优点：
        - 统一异常转 ToolResult
        - 自动记录日志
        - 方便 runtime 直接调用
        """
        try:
            self.validate_input(params)
            ctx.log(f"[{self.name}] start")
            result = self.execute(params, ctx)
            if result.logs:
                ctx.logs.extend(result.logs)
            ctx.log(f"[{self.name}] finished: success={result.success}")
            return result
        except ToolError as exc:
            ctx.log(f"[{self.name}] tool error: {exc}")
            return ToolResult.fail(error=str(exc), message=f"{self.name} failed")
        except Exception as exc:  # noqa: BLE001
            ctx.log(f"[{self.name}] unexpected error: {exc}")
            return ToolResult.fail(
                error=f"Unexpected error in tool {self.name}: {exc}",
                message=f"{self.name} failed unexpectedly",
            )

    @abstractmethod
    def execute(self, params: ToolInput, ctx: ToolContext) -> ToolResult:
        """工具核心执行函数。"""
        raise NotImplementedError


class BaseFileAdapter(ABC):
    """不同文件格式底层操作的适配器抽象。

    示例：
    - WordAdapter -> python-docx
    - ExcelAdapter -> openpyxl
    - PptAdapter -> python-pptx

    目的是把第三方库隔离在 adapter 层。
    """

    supported_extensions: tuple[str, ...] = ()

    def supports(self, file_path: str) -> bool:
        suffix = Path(file_path).suffix.lower()
        return suffix in self.supported_extensions

    def ensure_supported(self, file_path: str) -> None:
        if not self.supports(file_path):
            raise ToolValidationError(
                f"{self.__class__.__name__} does not support file: {file_path}"
            )

    @abstractmethod
    def load(self, file_path: str) -> Any:
        """加载文件对象。"""
        raise NotImplementedError

    @abstractmethod
    def save(self, document: Any, output_path: str) -> str:
        """保存文件对象到目标路径。"""
        raise NotImplementedError


class BaseDocumentTool(BaseTool, ABC):
    """文档类工具中间抽象。

    它用于处理“面向文件”的工具，而不是纯计算类工具。
    """

    supported_extensions: tuple[str, ...] = ()

    def supports_path(self, file_path: str) -> bool:
        suffix = Path(file_path).suffix.lower()
        return suffix in self.supported_extensions

    def ensure_path_supported(self, file_path: str) -> None:
        if not self.supports_path(file_path):
            raise ToolValidationError(
                f"{self.name} does not support file path: {file_path}"
            )


class BaseInspectTool(BaseDocumentTool, ABC):
    """只读检查类工具。

    适合：
    - inspect_word_structure
    - inspect_excel_schema
    - extract_placeholders
    """

    pass


class BaseTransformTool(BaseDocumentTool, ABC):
    """转换/修改类工具。

    适合：
    - fill_template
    - replace_text
    - convert_to_pdf
    """

    pass


class BaseValidateTool(BaseDocumentTool, ABC):
    """校验类工具。

    适合：
    - validate_unfilled_placeholders
    - validate_excel_headers
    - validate_ppt_overflow
    """

    pass


class BaseBatchTool(BaseTool, ABC):
    """批量工具抽象。

    现在最小 demo 不一定会立即用到，但提前留好位置很有价值。
    例如：
    - 批量生成多个 Word
    - 批量校验多个文件
    """

    @abstractmethod
    def execute_batch(
        self,
        params_list: List[ToolInput],
        ctx: ToolContext,
    ) -> List[ToolResult]:
        raise NotImplementedError


class ToolRegistry:
    """工具注册表。

    作用：
    - 按名称查工具
    - 按 capability 查工具
    - 按 file type 查工具

    后续 runtime 和 agent 都可以依赖它，而不是直接 import 某个具体工具。
    """

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if not tool.name:
            raise ValueError("Tool must have a non-empty name")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def list_all(self) -> List[BaseTool]:
        return list(self._tools.values())

    def find_by_capability(self, capability: Capability) -> List[BaseTool]:
        return [
            tool
            for tool in self._tools.values()
            if tool.has_capability(capability)
        ]

    def find_by_file_type(self, file_type: FileType) -> List[BaseTool]:
        return [
            tool
            for tool in self._tools.values()
            if tool.can_handle_file_type(file_type)
        ]

    def find_by_file_type_and_capability(
        self,
        file_type: FileType,
        capability: Capability,
    ) -> List[BaseTool]:
        return [
            tool
            for tool in self._tools.values()
            if tool.can_handle_file_type(file_type) and tool.has_capability(capability)
        ]