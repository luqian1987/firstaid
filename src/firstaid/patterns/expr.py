"""受限表达式求值。

规则条件和派生公式都用它。刻意不用 eval 全功能：
白名单 AST 节点 + 白名单函数，禁止属性写入、下标、导入、调用任意对象。
理由是这些表达式来自 knowledge/ 下的 YAML——将来由领域人员维护，
它必须是可审计的数据，而不是能执行任意代码的口子。
"""
from __future__ import annotations

import ast
import math
from typing import Any, Callable, Mapping

_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.UnaryOp, ast.BinOp, ast.Compare, ast.Call,
    ast.Name, ast.Load, ast.Constant, ast.Attribute, ast.IfExp,
    ast.And, ast.Or, ast.Not, ast.USub, ast.UAdd,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.List, ast.Tuple,
)

# 只允许访问这些属性名，防止通过 __class__ 之类逃逸
_ALLOWED_ATTRS = {
    "value", "unit", "status", "in_range", "is_high", "is_low", "abnormal",
    "negative", "has_range", "present", "ratio_to_upper", "ratio_to_lower",
    "position_in_range", "censor", "code", "text", "qualitative",
    "reported_flag", "method", "device", "axis",
    # 常用切点判定：与报告自带区间严格分开的另一套
    "advisory_in_range", "advisory_high", "advisory_low", "has_advisory", "judged",
}

_FUNCS: dict[str, Callable[..., Any]] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "sqrt": math.sqrt,
    "all_of": lambda *xs: all(bool(x) for x in xs),
    "any_of": lambda *xs: any(bool(x) for x in xs),
    "count_true": lambda *xs: sum(1 for x in xs if bool(x)),
}


class ExprError(ValueError):
    pass


def validate(src: str) -> ast.Expression:
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        raise ExprError(f"表达式语法错误: {src!r} ({e})") from e
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ExprError(
                f"表达式含不允许的语法 {type(node).__name__}: {src!r}")
        if isinstance(node, ast.Attribute) and node.attr not in _ALLOWED_ATTRS:
            raise ExprError(f"表达式含不允许的属性 .{node.attr}: {src!r}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
                raise ExprError(f"表达式含不允许的函数调用: {src!r}")
    return tree


def evaluate(src: str, names: Mapping[str, Any]) -> Any:
    tree = validate(src)
    env: dict[str, Any] = dict(_FUNCS)
    env.update(names)
    try:
        return eval(compile(tree, "<rule>", "eval"), {"__builtins__": {}}, env)
    except ZeroDivisionError:
        return None
    except (TypeError, AttributeError, KeyError, NameError):
        # 输入缺失导致算不出来 —— 返回 None，由调用方判定为 INDETERMINATE，
        # 绝不静默当成 False。
        return None


def referenced_names(src: str) -> set[str]:
    tree = validate(src)
    return {n.id for n in ast.walk(tree)
            if isinstance(n, ast.Name) and n.id not in _FUNCS}
