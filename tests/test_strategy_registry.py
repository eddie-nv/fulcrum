"""Unit tests for the strategy registry."""
import pytest
from fulcrum.services import strategy_registry


def test_registry_has_40_or_more_strategies():
    assert len(strategy_registry.REGISTRY) >= 40


def test_all_strategies_have_required_fields():
    for s in strategy_registry.REGISTRY:
        assert s.name, f"Strategy missing name: {s}"
        assert s.description, f"Strategy missing description: {s.name}"
        assert s.category, f"Strategy missing category: {s.name}"
        assert callable(s.executor), f"Strategy missing callable executor: {s.name}"


def test_no_duplicate_names():
    names = [s.name for s in strategy_registry.REGISTRY]
    assert len(names) == len(set(names)), "Duplicate strategy names found"


def test_categories_cover_required_set():
    required = {"config", "dependency", "runtime", "network", "storage", "auth", "resource", "code"}
    found = {s.category for s in strategy_registry.REGISTRY}
    assert required <= found


def test_get_by_name():
    s = strategy_registry.get("fix-redis-port")
    assert s is not None
    assert s.category == "config"


def test_get_unknown_returns_none():
    assert strategy_registry.get("does-not-exist") is None


def test_all_names_returns_list_of_strings():
    names = strategy_registry.all_names()
    assert isinstance(names, list)
    assert all(isinstance(n, str) for n in names)
    assert "fix-redis-port" in names
    assert "add-backoff" in names


def test_by_category_groups_correctly():
    grouped = strategy_registry.by_category()
    assert "config" in grouped
    assert "dependency" in grouped
    assert all(s.category == "config" for s in grouped["config"])


def test_executor_fix_redis_port():
    s = strategy_registry.get("fix-redis-port")
    snap = {"env": {"REDIS_PORT": "6379", "REDIS_HOST": "redis"}}
    params = s.get_fork_params(snap)
    assert params["env_overrides"]["REDIS_PORT"] == "6380"


def test_executor_add_backoff():
    s = strategy_registry.get("add-backoff")
    params = s.get_fork_params({})
    assert params["env_overrides"]["ENABLE_BACKOFF"] == "true"


def test_executor_add_circuit_breaker():
    s = strategy_registry.get("add-circuit-breaker")
    params = s.get_fork_params({})
    assert "CIRCUIT_BREAKER" in params["env_overrides"]


def test_executor_rollback_swaps_image():
    s = strategy_registry.get("rollback")
    snap = {"image": "fulcrum-target-v2", "env": {}}
    params = s.get_fork_params(snap)
    assert params["image"] == "fulcrum-target-v1"
    assert params["env_overrides"] == {}


def test_executor_rollback_to_v1():
    s = strategy_registry.get("rollback-to-v1")
    snap = {"image": "myapp-v2", "env": {}}
    params = s.get_fork_params(snap)
    assert params["image"] == "myapp-v1"


def test_executor_restart_no_changes():
    s = strategy_registry.get("restart")
    params = s.get_fork_params({"env": {"PORT": "3000"}})
    assert params["env_overrides"] == {}


def test_executor_disable_retries():
    s = strategy_registry.get("disable-retries")
    params = s.get_fork_params({})
    assert params["env_overrides"]["MAX_PAYMENT_RETRIES"] == "0"


def test_config_category_has_fix_redis_port():
    grouped = strategy_registry.by_category()
    config_names = [s.name for s in grouped["config"]]
    assert "fix-redis-port" in config_names


def test_dependency_category_has_backoff_and_circuit_breaker():
    grouped = strategy_registry.by_category()
    dep_names = [s.name for s in grouped["dependency"]]
    assert "add-backoff" in dep_names
    assert "add-circuit-breaker" in dep_names
