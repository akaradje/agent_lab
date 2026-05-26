from agent_lab import config


class TestConfig:
    def test_ceilings_positive(self) -> None:
        assert config.MAX_TOTAL_TOKENS > 0
        assert config.MAX_USD > 0
        assert config.MAX_QA_ROUNDS > 0

    def test_pricing_has_expected_models(self) -> None:
        assert "deepseek-v4-flash" in config.PRICING
        assert "deepseek-v4-pro" in config.PRICING
        for model, (input_price, output_price) in config.PRICING.items():
            assert input_price > 0, f"{model} input price must be > 0"
            assert output_price > 0, f"{model} output price must be > 0"

    def test_agent_models_has_all_six_agents(self) -> None:
        expected = {"orchestrator", "researcher", "architect", "worker", "critic", "sandbox"}
        assert set(config.AGENT_MODELS) == expected

    def test_agent_models_reference_known_models(self) -> None:
        for agent, (model, _) in config.AGENT_MODELS.items():
            assert model in config.PRICING, f"{agent} model {model} not in PRICING"

    def test_agent_models_reasoning_effort_valid(self) -> None:
        valid = {"non-think", "think-high", "think-max"}
        for agent, (_, effort) in config.AGENT_MODELS.items():
            assert effort in valid, f"{agent} reasoning_effort {effort} invalid"
