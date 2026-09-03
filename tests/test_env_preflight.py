from __future__ import annotations

import pytest

from robustbench.real_llm.env_preflight import RealVLLMEnvironmentError, check_environment


def test_check_environment_passes_for_real_module_set():
    check_environment({"os": "stdlib", "sys": "stdlib"})


def test_check_environment_raises_and_lists_every_missing_module():
    with pytest.raises(RealVLLMEnvironmentError) as exc_info:
        check_environment(
            {
                "os": "stdlib",
                "definitely_not_a_real_module_lssp": "fake requirement one",
                "also_not_a_real_module_lssp": "fake requirement two",
            }
        )
    message = str(exc_info.value)
    assert "definitely_not_a_real_module_lssp" in message
    assert "also_not_a_real_module_lssp" in message
    assert "os" not in message.split("Missing modules:")[1].splitlines()[0]
