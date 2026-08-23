from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture(scope="session")
def knowledge():
    from firstaid.loader import load_knowledge
    return load_knowledge()


@pytest.fixture
def zhang_real(knowledge):
    """真实报告转录的夹具：带原报告结论层，可做对账。"""
    from firstaid.loader import load_fixture
    ont, units, _, _ = knowledge
    tl, _ = load_fixture(FIXTURES / "zhang_real_2026-03-30.yaml", ont, units)
    return tl


@pytest.fixture
def zhang(knowledge):
    from firstaid.loader import load_fixture
    ont, units, _, _ = knowledge
    tl, _ = load_fixture(FIXTURES / "zhang_2026-03-30.yaml", ont, units)
    return tl
