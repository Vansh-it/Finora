"""Tests for multi-LLM task router and provider manager."""

from unittest.mock import patch, MagicMock
import os
import pytest
import time

from lib.provider_manager import (
    ProviderManager,
    Provider,
    ProviderStatus,
    TaskType,
    classify_task,
    TASK_ROUTING,
    get_manager,
    generate_text,
    generate_chat,
    PER_PROVIDER_TIMEOUT,
    GLOBAL_TIMEOUT,
)


class TestClassifyTask:
    """Tests for the task classifier (heuristic, no LLM call)."""

    def test_short_message_is_quick_chat(self):
        assert classify_task("hello") == TaskType.QUICK_CHAT
        assert classify_task("thanks") == TaskType.QUICK_CHAT
        assert classify_task("what is that") == TaskType.QUICK_CHAT

    def test_calculation_keywords(self):
        assert classify_task("calculate the margin") == TaskType.CALCULATION
        assert classify_task("what is the ROE formula") == TaskType.CALCULATION
        assert classify_task("how was FCF calculated") == TaskType.CALCULATION
        assert classify_task("step by step derivation of revenue") == TaskType.CALCULATION

    def test_heavy_reasoning_keywords(self):
        assert classify_task("compare this company with its peers") == TaskType.HEAVY_REASONING
        assert classify_task("evaluate the investment opportunity") == TaskType.HEAVY_REASONING
        assert classify_task("should I invest in this company") == TaskType.HEAVY_REASONING
        assert classify_task("what are the pros and cons") == TaskType.HEAVY_REASONING
        assert classify_task("deep dive into DCF valuation") == TaskType.HEAVY_REASONING

    def test_research_with_context(self):
        assert classify_task("what does this company do", has_research_context=True) == TaskType.RESEARCH
        assert classify_task("tell me about the revenue", has_research_context=True) == TaskType.RESEARCH

    def test_research_without_context_falls_back(self):
        assert classify_task("tell me about something random", has_research_context=False) == TaskType.QUICK_CHAT

    def test_financial_keywords_with_context(self):
        assert classify_task("what is the revenue", has_research_context=True) == TaskType.RESEARCH
        assert classify_task("describe the business model", has_research_context=True) == TaskType.RESEARCH


class TestProviderRegistration:
    """Tests for provider registration based on env vars."""

    def test_providers_registered(self):
        mgr = ProviderManager()
        # 3 NVIDIA NIM (Lightning, Super, gpt-oss) + 2 OpenRouter last resorts
        assert len(mgr._providers) == 5

    def test_provider_names(self):
        mgr = ProviderManager()
        names = set(mgr._providers.keys())
        assert "nvidia_nemotron_lightning" in names
        assert "nvidia_nemotron_super" in names
        assert "nvidia_gpt_oss" in names
        assert "openrouter_nemotron_ultra" in names
        assert "openrouter_nemotron_super_free" in names
        # DeepSeek and Kimi are removed (broken / unconfigured)
        assert "nvidia_deepseek_flash" not in names
        assert "nvidia_kimi_k3" not in names

    def test_each_nim_provider_uses_its_own_key(self):
        mgr = ProviderManager()
        # Separate keys so one account's rate limit or outage cannot take down the tier.
        assert mgr._providers["nvidia_nemotron_lightning"].api_key_env == "NVIDIA_API_KEY"
        assert mgr._providers["nvidia_nemotron_super"].api_key_env == "NVIDIA_API_KEY_2"
        assert mgr._providers["nvidia_gpt_oss"].api_key_env == "NVIDIA_API_KEY_3"

    def test_each_nim_provider_uses_a_different_model(self):
        mgr = ProviderManager()
        models = {
            mgr._providers["nvidia_nemotron_lightning"].model,
            mgr._providers["nvidia_nemotron_super"].model,
            mgr._providers["nvidia_gpt_oss"].model,
        }
        assert len(models) == 3, "NIM providers must not all depend on one model"

    def test_providers_have_correct_models(self):
        mgr = ProviderManager()
        assert mgr._providers["nvidia_nemotron_lightning"].model == "nvidia/nemotron-3.5-lightning-30b-a3b"
        assert mgr._providers["openrouter_nemotron_ultra"].model == "nvidia/nemotron-3-ultra-550b-a55b:free"
        assert mgr._providers["openrouter_nemotron_super_free"].model == "nvidia/nemotron-3-super-120b-a12b:free"

    def test_nvidia_providers_use_nvidia_base_url(self):
        mgr = ProviderManager()
        nvidia_base = "https://integrate.api.nvidia.com/v1"
        assert mgr._providers["nvidia_nemotron_lightning"].base_url == nvidia_base

    def test_openrouter_providers_use_openrouter_base_url(self):
        mgr = ProviderManager()
        openrouter_base = "https://openrouter.ai/api/v1"
        assert mgr._providers["openrouter_nemotron_ultra"].base_url == openrouter_base
        assert mgr._providers["openrouter_nemotron_super_free"].base_url == openrouter_base


class TestTaskRouting:
    """Tests for the task routing table."""

    def test_all_task_types_have_routing(self):
        for task_type in TaskType:
            assert task_type in TASK_ROUTING, f"Missing routing for {task_type}"

    def test_routing_has_required_fields(self):
        for task_type, routing in TASK_ROUTING.items():
            for entry in routing:
                assert "provider" in entry, f"Missing 'provider' in {task_type}"
                assert "max_tokens" in entry, f"Missing 'max_tokens' in {task_type}"

    def test_quick_chat_prefers_reliable_providers(self):
        quick_routing = TASK_ROUTING[TaskType.QUICK_CHAT]
        # Nemotron Lightning is the fastest NIM workhorse (~12s on full prompts)
        assert quick_routing[0]["provider"] == "nvidia_nemotron_lightning"
        assert quick_routing[0]["max_tokens"] <= 512

    def test_heavy_reasoning_prefers_powerful_providers(self):
        heavy_routing = TASK_ROUTING[TaskType.HEAVY_REASONING]
        # Nemotron Super 120B is the largest NIM model we route to
        assert heavy_routing[0]["provider"] == "nvidia_nemotron_super"
        # Room to answer, but not so much that we generate text the 300-word
        # cap would throw away (that is pure wasted latency).
        assert 512 <= heavy_routing[0]["max_tokens"] <= 1024

    def test_nvidia_always_outranks_openrouter(self):
        """Product requirement: NVIDIA NIM primary, OpenRouter strictly last."""
        nvidia_tier = {"nvidia_nemotron_lightning", "nvidia_nemotron_super", "nvidia_gpt_oss"}
        openrouter_tier = {"openrouter_nemotron_super_free", "openrouter_nemotron_ultra"}
        for task_type, routing in TASK_ROUTING.items():
            providers = [entry["provider"] for entry in routing]
            nvidia_idx = [i for i, p in enumerate(providers) if p in nvidia_tier]
            openrouter_idx = [i for i, p in enumerate(providers) if p in openrouter_tier]
            if nvidia_idx and openrouter_idx:
                assert max(nvidia_idx) < min(openrouter_idx), (
                    f"OpenRouter outranks NVIDIA NIM in {task_type.value}"
                )

    def test_calculation_uses_low_temperature(self):
        calc_routing = TASK_ROUTING[TaskType.CALCULATION]
        assert calc_routing[0]["temperature"] <= 0.2

    def test_intent_classify_uses_minimal_tokens(self):
        intent_routing = TASK_ROUTING[TaskType.INTENT_CLASSIFY]
        assert intent_routing[0]["max_tokens"] <= 128


class TestProviderHealth:
    """Tests for provider health tracking."""

    def test_provider_starts_healthy(self):
        p = Provider(name="test", model="test", base_url="http://test.com", api_key_env="TEST")
        assert p.is_available() is True
        assert p.status == ProviderStatus.HEALTHY

    def test_rate_limiting(self):
        p = Provider(name="test", model="test", base_url="http://test.com", api_key_env="TEST")
        p.mark_rate_limited(60.0)
        assert p.is_available() is False
        assert p.status == ProviderStatus.RATE_LIMITED

    def test_error_with_short_cooldown(self):
        p = Provider(name="test", model="test", base_url="http://test.com", api_key_env="TEST")
        p.mark_error(0.01)
        assert p.is_available() is False
        time.sleep(0.02)
        assert p.is_available() is True

    def test_auth_failed_long_cooldown(self):
        p = Provider(name="test", model="test", base_url="http://test.com", api_key_env="TEST")
        p.mark_auth_failed()
        assert p.is_available() is False
        assert p.get_cooldown_remaining() > 80000

    def test_unconfigured_always_unavailable(self):
        p = Provider(
            name="test", model="test", base_url="http://test.com",
            api_key_env="TEST", status=ProviderStatus.UNCONFIGURED,
        )
        assert p.is_available() is False

    def test_mark_healthy_clears_cooldown(self):
        p = Provider(name="test", model="test", base_url="http://test.com", api_key_env="TEST")
        p.mark_error(60.0)
        assert p.is_available() is False
        p.mark_healthy()
        assert p.is_available() is True
        assert p.error_count == 0

    def test_mark_healthy_updates_avg_latency(self):
        p = Provider(name="test", model="test", base_url="http://test.com", api_key_env="TEST")
        p.total_requests = 5
        p.mark_healthy(2.0)
        # Running average: ((0.0 * 4) + 2.0) / 5 = 0.4
        assert p.avg_latency == 0.4


class TestSelectProvidersForTask:
    """Tests for provider selection per task type.

    These exercise failover ordering, so they provision their own keys rather
    than depending on whatever happens to be in the ambient environment.
    """

    _KEYS = {"NVIDIA_API_KEY": "test-key", "OPENROUTER_API_KEY": "test-key"}

    def test_select_returns_available_providers(self):
        with patch.dict(os.environ, self._KEYS):
            mgr = ProviderManager()
            mgr._providers["nvidia_nemotron_lightning"].mark_rate_limited()
            candidates = mgr._select_providers_for_task(TaskType.QUICK_CHAT)
            provider_names = [c[0].name for c in candidates]
            assert "nvidia_nemotron_lightning" not in provider_names
            assert len(candidates) >= 1

    def test_select_falls_back_when_primary_down(self):
        with patch.dict(os.environ, self._KEYS):
            mgr = ProviderManager()
            mgr._providers["nvidia_nemotron_lightning"].mark_rate_limited()
            candidates = mgr._select_providers_for_task(TaskType.QUICK_CHAT)
            assert len(candidates) >= 1

    _ALL_KEYS = {
        "NVIDIA_API_KEY": "test-key",
        "NVIDIA_API_KEY_2": "test-key",
        "NVIDIA_API_KEY_3": "test-key",
        "OPENROUTER_API_KEY": "test-key",
    }

    def test_fallback_exhausts_nim_before_openrouter(self):
        """A dead NIM provider must fall through to the next NIM provider,
        never skipping straight to OpenRouter."""
        with patch.dict(os.environ, self._ALL_KEYS):
            mgr = ProviderManager()
            mgr._providers["nvidia_nemotron_lightning"].mark_rate_limited()
            mgr._providers["nvidia_nemotron_super"].mark_rate_limited()
            candidates = [c[0].name for c in mgr._select_providers_for_task(TaskType.QUICK_CHAT)]
            assert candidates[0] == "nvidia_gpt_oss"
            openrouter_at = next(
                (i for i, n in enumerate(candidates) if n.startswith("openrouter_")), None
            )
            assert openrouter_at is not None, "OpenRouter should remain as a last resort"
            assert all(not n.startswith("openrouter_") for n in candidates[:openrouter_at])

    def test_last_resort_still_reaches_openrouter(self):
        with patch.dict(os.environ, self._ALL_KEYS):
            mgr = ProviderManager()
            for name in ("nvidia_nemotron_lightning", "nvidia_nemotron_super", "nvidia_gpt_oss"):
                mgr._providers[name].mark_rate_limited()
            candidates = [c[0].name for c in mgr._select_providers_for_task(TaskType.QUICK_CHAT)]
            assert candidates
            assert candidates[0].startswith("openrouter_")


class TestTimeouts:
    """Tests for timeout configuration."""

    def test_per_provider_timeout_is_reasonable(self):
        # Real NIM latency for a full chat prompt measures 16-34s, so a budget
        # below 30s guarantees a timeout on every normal request.
        assert PER_PROVIDER_TIMEOUT >= 30.0
        assert PER_PROVIDER_TIMEOUT <= 120.0

    def test_global_timeout_is_reasonable(self):
        assert GLOBAL_TIMEOUT >= 60.0
        assert GLOBAL_TIMEOUT <= 300.0

    def test_global_timeout_greater_than_per_provider(self):
        assert GLOBAL_TIMEOUT > PER_PROVIDER_TIMEOUT


class TestProviderStatus:
    """Tests for the status endpoint."""

    def test_status_structure(self):
        mgr = ProviderManager()
        status = mgr.get_status()
        assert "providers" in status
        assert "strategy" in status
        assert status["strategy"] == "fast_failover"
        assert "total_providers" in status
        assert status["total_providers"] == len(mgr._providers)
        assert status["total_providers"] == 5

    def test_status_includes_timeout_info(self):
        mgr = ProviderManager()
        status = mgr.get_status()
        assert status["per_provider_timeout"] == PER_PROVIDER_TIMEOUT
        assert status["global_timeout"] == GLOBAL_TIMEOUT

    def test_status_includes_tags(self):
        mgr = ProviderManager()
        status = mgr.get_status()
        for p in status["providers"]:
            assert "tags" in p


class TestSingletonManager:
    def test_singleton_returns_same_instance(self):
        mgr1 = get_manager()
        mgr2 = get_manager()
        assert mgr1 is mgr2


class TestPayloadConstruction:
    """The NIM chat template must never leak its reasoning preamble into `content`."""

    @staticmethod
    def _call_and_capture(provider, monkeypatch_env):
        captured = {}

        class FakeResponse:
            status_code = 200
            text = ""

            @staticmethod
            def json():
                return {"choices": [{"message": {"content": "finished answer"}}]}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def post(self, url, json=None, headers=None):
                captured.update(json or {})
                return FakeResponse()

        mgr = ProviderManager()
        with patch("httpx.Client", FakeClient):
            out = mgr._call_provider(
                provider,
                [{"role": "user", "content": "hi"}],
                max_tokens=512,
                temperature=0.3,
                top_p=0.9,
            )
        assert out == "finished answer"
        return captured

    def test_nvidia_payload_disables_thinking(self):
        provider = Provider(
            name="nvidia_test",
            model="nvidia/nemotron-3.5-lightning-30b-a3b",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key_env="NVIDIA_API_KEY",
        )
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-test-key"}):
            payload = self._call_and_capture(provider, None)
        assert payload["chat_template_kwargs"] == {"thinking": False}

    def test_non_nvidia_payload_left_alone(self):
        provider = Provider(
            name="openrouter_test",
            model="nvidia/nemotron-3-super-120b-a12b:free",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="OPENROUTER_API_KEY",
        )
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-test-key"}):
            payload = self._call_and_capture(provider, None)
        assert "chat_template_kwargs" not in payload
