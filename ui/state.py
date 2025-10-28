from dataclasses import dataclass
from typing import Optional

from core.dxf_core.dxf_engine import DXFAnalysisResult

@dataclass
class AppState:
    dxf_result: Optional[DXFAnalysisResult] = None

app_state = AppState()
