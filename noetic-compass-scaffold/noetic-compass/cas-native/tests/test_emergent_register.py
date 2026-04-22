"""Tests for the EmergentRegisterPipeline (ADR-02 / ADR-03)."""

from pathlib import Path

import pytest
import torch

from model.emergent_register import (
    DEFAULT_D_MODEL,
    DEFAULT_REGISTRY_CAPACITY,
    DEFAULT_SIMILARITY_THRESHOLD,
    NUM_DOMAINS,
    NUM_NOETICS,
    NUM_REGISTERS,
    EmergentRegisterBindingHead,
    EmergentRegisterPipeline,
    OmegaRegistry,
    PrerequisiteGate,
    SimilarityActivation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config_path() -> Path:
    """Path to the authoritative omega_registry.yaml."""
    here = Path(__file__).resolve()
    return (
        here.parent.parent / "config" / "omega_registry.yaml"
    )


@pytest.fixture
def d_model() -> int:
    return DEFAULT_D_MODEL  # 128


@pytest.fixture
def gate() -> PrerequisiteGate:
    return PrerequisiteGate()


@pytest.fixture
def binding_head(d_model) -> EmergentRegisterBindingHead:
    return EmergentRegisterBindingHead(d_model=d_model)


@pytest.fixture
def registry(d_model) -> OmegaRegistry:
    return OmegaRegistry(d_model=d_model, capacity=DEFAULT_REGISTRY_CAPACITY)


@pytest.fixture
def pipeline(d_model) -> EmergentRegisterPipeline:
    return EmergentRegisterPipeline(
        d_model=d_model, registry_capacity=DEFAULT_REGISTRY_CAPACITY
    )


# ---------------------------------------------------------------------------
# PrerequisiteGate
# ---------------------------------------------------------------------------


class TestPrerequisiteGate:
    def test_zero_parameters(self, gate):
        """PrerequisiteGate is pure arithmetic — must have ZERO parameters."""
        assert sum(p.numel() for p in gate.parameters()) == 0
        assert len(list(gate.parameters())) == 0

    def test_single_register_active_returns_false(self, gate):
        """Only one register above threshold at a cell: gate must be False."""
        # One batch, all cells, only register 0 active.
        activations = torch.zeros(NUM_NOETICS, NUM_DOMAINS, NUM_REGISTERS)
        activations[..., 0] = 0.9  # way above threshold=0.1
        mask = gate(activations)
        assert mask.shape == (NUM_NOETICS, NUM_DOMAINS)
        assert not mask.any(), "No (Noetic, Domain) cell should pass the gate"

    def test_two_registers_active_returns_true(self, gate):
        """Two registers above threshold at a cell: gate must be True there."""
        activations = torch.zeros(NUM_NOETICS, NUM_DOMAINS, NUM_REGISTERS)
        # At (Noetic=1, Domain=0) activate registers A (1) and E (3).
        activations[1, 0, 1] = 0.8
        activations[1, 0, 3] = 0.5
        mask = gate(activations)
        assert mask[1, 0].item() is True
        # Zero everywhere else.
        mask[1, 0] = False
        assert not mask.any()

    def test_three_registers_active_returns_true(self, gate):
        """Three registers above threshold still returns True."""
        activations = torch.zeros(NUM_NOETICS, NUM_DOMAINS, NUM_REGISTERS)
        activations[3, 2, 0] = 0.6  # T
        activations[3, 2, 1] = 0.4  # A
        activations[3, 2, 2] = 0.2  # f (lowercase authoritative)
        mask = gate(activations)
        assert mask[3, 2].item() is True

    def test_threshold_tunable(self):
        """Threshold is configurable and governs the 'active' decision."""
        strict_gate = PrerequisiteGate(threshold=0.5)
        permissive_gate = PrerequisiteGate(threshold=0.05)

        activations = torch.zeros(NUM_NOETICS, NUM_DOMAINS, NUM_REGISTERS)
        activations[0, 0, 0] = 0.3
        activations[0, 0, 1] = 0.2

        # Strict threshold (0.5) rejects both — no registers above threshold.
        assert not strict_gate(activations)[0, 0].item()
        # Permissive threshold (0.05) accepts both.
        assert permissive_gate(activations)[0, 0].item()

    def test_at_threshold_not_active(self, gate):
        """Strict > comparison — exactly at threshold is not 'active'."""
        activations = torch.zeros(NUM_NOETICS, NUM_DOMAINS, NUM_REGISTERS)
        activations[0, 0, 0] = 0.1  # exactly at default threshold
        activations[0, 0, 1] = 0.1
        assert not gate(activations)[0, 0].item()

    def test_batched_input(self, gate):
        """Gate accepts arbitrary leading batch dims."""
        activations = torch.zeros(2, 3, NUM_NOETICS, NUM_DOMAINS, NUM_REGISTERS)
        activations[0, 1, 5, 2, 0] = 0.6
        activations[0, 1, 5, 2, 1] = 0.7
        mask = gate(activations)
        assert mask.shape == (2, 3, NUM_NOETICS, NUM_DOMAINS)
        assert mask[0, 1, 5, 2].item() is True


# ---------------------------------------------------------------------------
# EmergentRegisterBindingHead
# ---------------------------------------------------------------------------


class TestEmergentRegisterBindingHead:
    def test_parameter_count_is_d_squared(self, binding_head, d_model):
        """ADR-02 locks the binding layer at d^2 params — NOT d^3 (Bilinear)."""
        total = sum(p.numel() for p in binding_head.parameters())
        expected = d_model * d_model  # 16,384 at d=128
        assert total == expected, (
            f"Binding head must have exactly d^2 = {expected} params "
            f"(got {total}); a nn.Bilinear(d,d,d) would cost d^3 ~2.1M."
        )
        # Explicit numeric check at the ADR-02 default.
        assert expected == 16_384

    def test_binding_projection_has_no_bias(self, binding_head):
        """ADR-02: binding_projection is `nn.Linear(d, d, bias=False)`."""
        assert binding_head.binding_projection.bias is None

    def test_output_shape(self, binding_head, d_model):
        """Output shape is (..., d_model) — register axis is folded."""
        states = torch.randn(4, NUM_REGISTERS, d_model)
        mask = torch.ones(4, dtype=torch.bool)
        out = binding_head(states, mask)
        assert out.shape == (4, d_model)

    def test_output_zeroed_where_mask_false(self, binding_head, d_model):
        """Positions where prereq_mask is False must be zeroed out."""
        states = torch.randn(5, NUM_REGISTERS, d_model)
        mask = torch.tensor([True, False, True, False, True])
        out = binding_head(states, mask)
        # False positions: exactly zero.
        assert torch.all(out[1] == 0)
        assert torch.all(out[3] == 0)
        # True positions: at least some entries nonzero (random projection of
        # random product rarely produces all-zero vectors).
        assert out[0].abs().sum() > 0
        assert out[2].abs().sum() > 0
        assert out[4].abs().sum() > 0

    def test_hadamard_fold_then_projection(self, binding_head, d_model):
        """Output must equal projection(prod(states, dim=-2)) when mask True."""
        states = torch.randn(3, NUM_REGISTERS, d_model)
        mask = torch.ones(3, dtype=torch.bool)
        out = binding_head(states, mask)
        expected_folded = states.prod(dim=-2)  # (3, d_model)
        expected = binding_head.binding_projection(expected_folded)
        assert torch.allclose(out, expected, atol=1e-5)

    def test_not_nn_bilinear(self, binding_head):
        """Defensive: confirm implementation is Linear + Hadamard, not Bilinear."""
        assert isinstance(binding_head.binding_projection, torch.nn.Linear)

    def test_gradient_flow(self, binding_head, d_model):
        """Gradients must flow from binding output back to inputs."""
        states = torch.randn(2, NUM_REGISTERS, d_model, requires_grad=True)
        mask = torch.ones(2, dtype=torch.bool)
        out = binding_head(states, mask)
        out.sum().backward()
        assert states.grad is not None
        assert states.grad.abs().sum() > 0


# ---------------------------------------------------------------------------
# OmegaRegistry
# ---------------------------------------------------------------------------


class TestOmegaRegistry:
    def test_default_capacity_20(self, registry, d_model):
        """Default ADR-02 / ADR-03 capacity is 20 slots."""
        assert registry.capacity == 20
        assert registry.registry.shape == (20, d_model)

    def test_initial_active_size_zero(self, registry):
        """No Omega_* admitted at construction — active_size starts at 0."""
        assert registry.active_size == 0

    def test_load_from_config_admits_two(self, registry, config_path):
        """Loading omega_registry.yaml admits exactly Omega_presence + Omega_refusal."""
        registry.load_from_config(config_path)
        assert registry.active_size == 2
        names = registry.get_active_names()
        assert names == ["Omega_presence", "Omega_refusal"]
        assert registry.registry_names[0] == "Omega_presence"
        assert registry.registry_names[1] == "Omega_refusal"

    def test_load_from_config_respects_slot_indices(self, registry, config_path):
        """Appendix I Entry 1 maps to slot 0; Entry 2 maps to slot 1."""
        registry.load_from_config(config_path)
        # Slot 0 holds Omega_presence, slot 1 Omega_refusal.
        assert registry.registry_names[0] == "Omega_presence"
        assert registry.registry_names[1] == "Omega_refusal"
        # Remaining 18 slots unadmitted (reserved_slots_for_growth).
        for i in range(2, 20):
            assert registry.registry_names[i] is None

    def test_add_omega_hot_swap(self, d_model):
        """Hot-swap admission at inference does not require retraining."""
        r = OmegaRegistry(d_model=d_model, capacity=DEFAULT_REGISTRY_CAPACITY)
        # Freeze parameters to simulate inference mode.
        for p in r.parameters():
            p.requires_grad_(False)
        emb = torch.randn(d_model)
        slot = r.add_omega("Omega_flow", embedding=emb)
        assert slot == 0
        assert r.active_size == 1
        assert r.registry_names[0] == "Omega_flow"
        # Embedding was copied into slot 0.
        assert torch.allclose(r.registry[0].detach(), emb, atol=1e-6)

    def test_add_omega_increments_active_size(self, registry, d_model):
        """active_size increments as new Omega_* entries are admitted."""
        assert registry.active_size == 0
        registry.add_omega("Omega_alpha", embedding=torch.randn(d_model))
        assert registry.active_size == 1
        registry.add_omega("Omega_beta", embedding=torch.randn(d_model))
        assert registry.active_size == 2
        registry.add_omega("Omega_gamma")  # no embedding — slot keeps random init
        assert registry.active_size == 3

    def test_add_omega_rejects_wrong_shape(self, registry):
        """Embedding shape must be (d_model,)."""
        with pytest.raises(ValueError, match="Expected embedding shape"):
            registry.add_omega("Omega_bad", embedding=torch.randn(7))

    def test_add_omega_rejects_out_of_range_slot(self, registry, d_model):
        """Slot index must lie within capacity."""
        with pytest.raises(ValueError, match="out of range"):
            registry.add_omega(
                "Omega_oob", embedding=torch.randn(d_model), slot=99
            )

    def test_get_active_embeddings_shape(self, registry, config_path):
        """active_embeddings has shape (active_size, d_model)."""
        registry.load_from_config(config_path)
        emb = registry.get_active_embeddings()
        assert emb.shape == (2, registry.d_model)

    def test_capacity_mismatch_raises(self, d_model, config_path):
        """Config capacity must match registry capacity."""
        r = OmegaRegistry(d_model=d_model, capacity=10)  # config expects 20
        with pytest.raises(ValueError, match="capacity"):
            r.load_from_config(config_path)


# ---------------------------------------------------------------------------
# SimilarityActivation
# ---------------------------------------------------------------------------


class TestSimilarityActivation:
    def test_default_threshold_is_0_7(self):
        """ADR-03 default similarity threshold is 0.7 (empirically untuned)."""
        s = SimilarityActivation()
        assert s.similarity_threshold == 0.7
        # Spec lock: default matches the module-level constant.
        assert s.similarity_threshold == DEFAULT_SIMILARITY_THRESHOLD

    def test_threshold_flagged_as_placeholder_in_source(self):
        """Source must flag 0.7 threshold as EMPIRICALLY UNTUNED PLACEHOLDER."""
        import inspect

        import model.emergent_register as er_module

        src = inspect.getsource(er_module)
        # Check the doc flag appears (case-insensitive on "empirically untuned").
        assert "EMPIRICALLY UNTUNED PLACEHOLDER" in src.upper() or (
            "empirically untuned" in src.lower()
        )

    def test_cosine_similarity_computed(self, registry, d_model):
        """Score equals torch cosine similarity against registry row."""
        # Seed a single registry entry.
        emb = torch.randn(d_model)
        registry.add_omega("Omega_test", embedding=emb)
        activation = SimilarityActivation(similarity_threshold=0.0)

        # Binding output identical to registry embedding -> similarity = 1.0.
        out = activation(emb.unsqueeze(0), registry)
        sim = out["similarities"]["Omega_test"]
        assert torch.allclose(sim, torch.tensor([1.0]), atol=1e-5)

    def test_returns_per_omega_activation(self, registry, config_path, d_model):
        """Returns a similarity score per registered Omega_*."""
        registry.load_from_config(config_path)
        activation = SimilarityActivation()
        binding = torch.randn(3, d_model)
        out = activation(binding, registry)
        assert set(out["similarities"].keys()) == {
            "Omega_presence",
            "Omega_refusal",
        }
        assert out["similarities"]["Omega_presence"].shape == (3,)
        assert out["similarities"]["Omega_refusal"].shape == (3,)

    def test_novel_detection(self, registry, d_model):
        """Binding far from all registry entries is flagged as candidate=True."""
        # Registry embedding is e1 (aligned with first basis vector).
        e1 = torch.zeros(d_model)
        e1[0] = 1.0
        registry.add_omega("Omega_first", embedding=e1)

        # Binding output aligned with e2 (orthogonal) — cosine sim = 0 < 0.7.
        e2 = torch.zeros(d_model)
        e2[1] = 1.0
        activation = SimilarityActivation(similarity_threshold=0.7)
        out = activation(e2.unsqueeze(0), registry)
        assert out["candidate"][0].item() is True

        # Binding output aligned with e1 — cosine sim = 1.0 >= 0.7.
        out2 = activation(e1.unsqueeze(0), registry)
        assert out2["candidate"][0].item() is False

    def test_empty_registry_flags_candidate(self, registry, d_model):
        """With no admitted Omega_*, every binding output is a candidate."""
        activation = SimilarityActivation()
        binding = torch.randn(4, d_model)
        out = activation(binding, registry)
        assert out["similarities"] == {}
        assert out["candidate"].all()


# ---------------------------------------------------------------------------
# EmergentRegisterPipeline — end-to-end
# ---------------------------------------------------------------------------


class TestEmergentRegisterPipeline:
    def test_load_registry_config(self, pipeline, config_path):
        """Pipeline delegates config loading to the internal OmegaRegistry."""
        pipeline.load_registry_config(config_path)
        assert pipeline.registry.active_size == 2

    def test_omega_presence_pattern_matches(self, pipeline, config_path, d_model):
        """Synthetic inputs aligned with Omega_presence embedding should match."""
        pipeline.load_registry_config(config_path)

        # Craft a (num_registers, d_model) state whose Hadamard product, when
        # projected, lands exactly on the Omega_presence registry row. We do
        # this by inverting the projection: pick a target product vector,
        # solve for states whose product equals it, then verify similarity.
        omega_presence_emb = pipeline.registry.registry[0].detach().clone()
        # Desired projected output: omega_presence_emb.
        # bound = W @ folded  =>  folded = W^{-1} @ omega_presence_emb.
        W = pipeline.binding_head.binding_projection.weight.detach()
        folded_target = torch.linalg.solve(W, omega_presence_emb)

        # Choose states so that states.prod(dim=-2) == folded_target.
        # Set registers 1..R to ones, register 0 to folded_target.
        states = torch.ones(NUM_REGISTERS, d_model)
        states[0] = folded_target

        # register_activations: only (Noetic=1, Domain=0) has |A and |E active.
        register_activations = torch.zeros(
            NUM_NOETICS, NUM_DOMAINS, NUM_REGISTERS
        )
        register_activations[1, 0, 1] = 0.9  # |A
        register_activations[1, 0, 3] = 0.9  # |E

        out = pipeline(
            states,
            register_activations,
            cell=(1, 0),
        )
        # Cell passed the prerequisite gate.
        assert out["prereq_mask_cell"].item() is True
        # Similarity to Omega_presence is near 1.0.
        sim_presence = out["similarities"]["Omega_presence"].item()
        assert sim_presence > 0.99, (
            f"Expected ~1.0 cosine similarity to Omega_presence; got {sim_presence}"
        )
        # Not flagged as novel.
        assert out["candidate"].item() is False

    def test_far_from_registry_flagged_novel(self, pipeline, config_path, d_model):
        """Binding outputs orthogonal to every registry row are novel candidates."""
        pipeline.load_registry_config(config_path)
        # Set registry rows to standard basis vectors e0, e1 so we can pick an
        # orthogonal binding target.
        with torch.no_grad():
            pipeline.registry.registry[0].zero_()
            pipeline.registry.registry[0, 0] = 1.0
            pipeline.registry.registry[1].zero_()
            pipeline.registry.registry[1, 1] = 1.0

        # Target binding output aligned with e2 (orthogonal to e0, e1).
        target = torch.zeros(d_model)
        target[2] = 1.0
        W = pipeline.binding_head.binding_projection.weight.detach()
        folded_target = torch.linalg.solve(W, target)
        states = torch.ones(NUM_REGISTERS, d_model)
        states[0] = folded_target

        register_activations = torch.zeros(
            NUM_NOETICS, NUM_DOMAINS, NUM_REGISTERS
        )
        register_activations[1, 0, 1] = 0.9
        register_activations[1, 0, 3] = 0.9

        out = pipeline(states, register_activations, cell=(1, 0))
        # Similarity to both registered Omega_* is ~0 (orthogonal basis vectors).
        for name in ("Omega_presence", "Omega_refusal"):
            assert abs(out["similarities"][name].item()) < 0.05
        # Candidate flagged True because max similarity < 0.7 threshold.
        assert out["candidate"].item() is True

    def test_prereq_gate_suppresses_binding(self, pipeline, config_path, d_model):
        """When the prereq gate fails, binding output is zeroed."""
        pipeline.load_registry_config(config_path)

        states = torch.randn(NUM_REGISTERS, d_model)
        # Only one register active at (1, 0) — gate fails.
        register_activations = torch.zeros(
            NUM_NOETICS, NUM_DOMAINS, NUM_REGISTERS
        )
        register_activations[1, 0, 1] = 0.9

        out = pipeline(states, register_activations, cell=(1, 0))
        assert out["prereq_mask_cell"].item() is False
        assert torch.all(out["binding"] == 0)


# ---------------------------------------------------------------------------
# Backward-compat smoke: importing existing modules still works.
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_existing_embedding_module_still_importable(self):
        """Adding emergent_register must not break cas_native.model.embedding."""
        from model.embedding import CognitiveStateEmbedding, NUM_COGNITIVE_STATES

        assert NUM_COGNITIVE_STATES == 40
        emb = CognitiveStateEmbedding(d_model=64)
        x = torch.randn(1, 4, 64)
        out = emb(x)
        assert out.shape == (1, 4, 40)
