import pytest
from lle import Direction, World

from generators.world_builder import WorldBuilder
from solver import CooperationProfileAnalyzer, CooperationProfileResult


def analyze(world: World, t: int):
    world.reset()
    return CooperationProfileAnalyzer(world, T_MAX=t).analyze()


def build_world(width, height, agents=(), exits=(), walls=(), lasers=()):
    builder = WorldBuilder(width, height)
    for idx, pos in enumerate(agents):
        builder.add_agent(idx, pos)
    for pos in exits:
        builder.add_exit(pos)
    for pos in walls:
        builder.add_wall(pos)
    for color, pos, direction in lasers:
        builder.add_laser(color, pos, direction)
    world = builder.build()
    world.reset()
    return world


def make_result(**overrides):
    base = dict(
        solvable=True,
        cooperation_required=True,
        num_agents=3,
        necessary_helpers=frozenset({0}),
        dependency_edges=frozenset({(0, 1)}),
        helper_events=tuple(),
        mutual_pairs=frozenset(),
        longest_chain_length=1,
        largest_scc_size=1,
        synchronous_width=1,
        profile="asymmetric",
    )
    base.update(overrides)
    return CooperationProfileResult(**base)


# ==========================================================
# Analyzer tests on real worlds
# ==========================================================


@pytest.mark.parametrize(
    "level,t,expected_profile,expected_cooperative,expected_helpers,expected_edges",
    [
        (1, 10, "independent", False, frozenset(), frozenset()),
        (2, 10, "independent", False, frozenset(), frozenset()),
        (3, 10, "asymmetric", True, frozenset({0}), frozenset({(0, 1)})),
        (4, 10, "fully_coupled", True, frozenset({0, 1}), frozenset({(0, 1), (1, 0)})),
    ],
)
def test_lle_levels_have_expected_profile_signals(
    level, t, expected_profile, expected_cooperative, expected_helpers, expected_edges
):
    result = analyze(World.level(level), t)

    assert result.solvable is True
    assert result.cooperation_required is expected_cooperative
    assert result.profile == expected_profile
    assert result.necessary_helpers == expected_helpers
    assert result.dependency_edges == expected_edges


def test_lle_level_4_has_expected_coupling_metrics():
    result = analyze(World.level(4), 10)

    assert result.matches_profile("cooperative")
    assert result.matches_profile("mutual")
    assert result.matches_profile("fully_coupled")
    assert not result.matches_profile("asymmetric")
    assert result.mutual_pairs == frozenset({(0, 1)})
    assert result.largest_scc_size == 2
    assert result.longest_chain_length == 0


def test_custom_three_agent_level_is_asymmetric():
    """
    With strict beam semantics that preserve same-colour immunity (Definition 3.6),
    agent 0's traversal of its own beam at (2, 1) is purely navigational and not a
    helping action. Only agent 1 must truncate its own beam to let agent 2 cross.
    """
    result = analyze(
        build_world(
            5,
            5,
            agents=[(0, 0), (0, 2), (0, 4)],
            exits=[(4, 0), (4, 2), (4, 4)],
            lasers=[
                (0, (2, 0), Direction.EAST),
                (1, (2, 2), Direction.EAST),
            ],
        ),
        8,
    )

    assert result.solvable is True
    assert result.cooperation_required is True
    assert result.profile == "asymmetric"
    assert result.matches_profile("asymmetric")
    assert result.matches_profile("cooperative")
    assert not result.matches_profile("mutual")
    assert not result.matches_profile("fully_coupled")
    assert not result.matches_profile("distributed")
    assert result.necessary_helpers == frozenset({1})
    assert result.dependency_edges == frozenset({(1, 2)})
    assert result.longest_chain_length == 1
    assert result.largest_scc_size == 1


def test_crossed_beams_three_agents_is_mutual():
    """
    Two horizontal beams of opposite colours fully overlap on row 2. Agents 0 and 1
    each block their own beam to let the other cross, and both blockings together
    open the middle column for agent 2. The mutual blocking dominates the
    classification, producing a 'mutual' profile with a 2-agent SCC.
    """
    result = analyze(
        build_world(
            5,
            5,
            agents=[(0, 1), (0, 3), (0, 2)],
            exits=[(4, 1), (4, 3), (4, 2)],
            lasers=[
                (0, (2, 0), Direction.EAST),
                (1, (2, 4), Direction.WEST),
            ],
        ),
        10,
    )

    assert result.solvable is True
    assert result.cooperation_required is True
    assert result.profile == "mutual"
    assert result.matches_profile("mutual")
    assert result.matches_profile("cooperative")
    assert result.largest_scc_size == 2
    assert (0, 1) in result.mutual_pairs or (1, 0) in result.mutual_pairs


def test_three_agents_two_separated_lasers_is_distributed():
    """
    Two lasers in different rows facing opposite directions: L0 at (2, 0) going east
    blocks row 2, and L1 at (4, 7) going west blocks row 4. All three exits are at
    the top row, so the beneficiary B0 (color 2) starting at (6, 2) must cross both
    row 4 and row 2 to reach an exit. Both helpers are necessary: H0 (color 0) must
    truncate L0 to clear row 2, and H1 (color 1) must truncate L1 to clear row 4.
    Critically there is no mutual back-edge — H1's row-2 crossing is enabled by H0
    (chain edge H0->H1) but H0's detour stays out of L1's row, so no H1->H0 edge
    forms. The result is dependency edges {H0->H1, H0->B0, H1->B0}, with B0 indegree
    2, classifying as 'distributed'.
    """
    result = analyze(
        build_world(
            8,
            7,
            agents=[(0, 0), (0, 7), (6, 2)],
            exits=[(0, 1), (0, 3), (0, 6)],
            lasers=[
                (0, (2, 0), Direction.EAST),
                (1, (4, 7), Direction.WEST),
            ],
        ),
        14,
    )

    assert result.solvable is True
    assert result.cooperation_required is True
    assert result.profile == "distributed"
    assert result.matches_profile("distributed")
    assert result.matches_profile("cooperative")
    assert not result.matches_profile("mutual")
    assert not result.matches_profile("fully_coupled")
    assert result.necessary_helpers == frozenset({0, 1})
    assert result.dependency_edges == frozenset({(0, 1), (0, 2), (1, 2)})
    assert result.mutual_pairs == frozenset()
    assert result.largest_scc_size == 1


def test_unsolvable_world_returns_unsolvable_profile():
    result = analyze(
        build_world(
            4,
            4,
            agents=[(0, 0), (0, 3)],
            exits=[(3, 0), (3, 3)],
            walls=[(2, 0), (2, 1), (2, 2), (2, 3)],
        ),
        5,
    )

    assert result.solvable is False
    assert result.cooperation_required is False
    assert result.profile == "unsolvable"
    assert result.necessary_helpers == frozenset()
    assert result.dependency_edges == frozenset()
    assert result.longest_chain_length == 0
    assert result.largest_scc_size == 0


# ==========================================================
# Profile recognition unit tests
# ==========================================================


@pytest.mark.parametrize(
    "target,result",
    [
        (
            "independent",
            make_result(
                cooperation_required=False,
                necessary_helpers=frozenset(),
                dependency_edges=frozenset(),
                longest_chain_length=0,
                profile="independent",
            ),
        ),
        ("cooperative", make_result(profile="asymmetric")),
        ("asymmetric", make_result(profile="asymmetric")),
        (
            "mutual",
            make_result(
                num_agents=2,
                necessary_helpers=frozenset({0, 1}),
                dependency_edges=frozenset({(0, 1), (1, 0)}),
                mutual_pairs=frozenset({(0, 1)}),
                largest_scc_size=2,
                profile="mutual",
            ),
        ),
        (
            "chain",
            make_result(
                num_agents=3,
                necessary_helpers=frozenset({0, 1}),
                dependency_edges=frozenset({(0, 1), (1, 2)}),
                longest_chain_length=2,
                profile="asymmetric",
            ),
        ),
        (
            "distributed",
            make_result(
                num_agents=3,
                necessary_helpers=frozenset({0, 1}),
                dependency_edges=frozenset({(0, 2), (1, 2)}),
                profile="distributed",
            ),
        ),
        (
            "fully_coupled",
            make_result(
                num_agents=3,
                necessary_helpers=frozenset({0, 1, 2}),
                dependency_edges=frozenset({(0, 1), (1, 2), (2, 0)}),
                largest_scc_size=3,
                profile="fully_coupled",
            ),
        ),
    ],
)
def test_matches_profile_positive_cases(target, result):
    assert result.matches_profile(target)


@pytest.mark.parametrize(
    "target,result",
    [
        ("cooperative", make_result(cooperation_required=False, profile="independent")),
        ("independent", make_result(profile="asymmetric")),
        ("asymmetric", make_result(profile="distributed")),
        (
            "mutual",
            make_result(
                dependency_edges=frozenset({(0, 1)}),
                mutual_pairs=frozenset(),
                profile="asymmetric",
            ),
        ),
        (
            "chain",
            make_result(
                dependency_edges=frozenset({(0, 2), (1, 2)}),
                longest_chain_length=1,
                profile="distributed",
            ),
        ),
        (
            "distributed",
            make_result(
                dependency_edges=frozenset({(0, 1), (1, 2)}),
                longest_chain_length=2,
                profile="asymmetric",
            ),
        ),
        (
            "fully_coupled",
            make_result(
                dependency_edges=frozenset({(0, 1), (1, 2)}),
                largest_scc_size=1,
                profile="asymmetric",
            ),
        ),
    ],
)
def test_matches_profile_negative_cases(target, result):
    assert not result.matches_profile(target)


@pytest.mark.parametrize(
    "edges,longest_chain_length,expected",
    [
        (frozenset(), 0, False),
        (frozenset({(0, 1)}), 1, True),
        (frozenset({(0, 1), (1, 2)}), 2, True),
        (frozenset({(0, 2), (1, 2)}), 1, False),
        (frozenset({(0, 1), (0, 2)}), 1, False),
        (frozenset({(0, 1), (1, 0)}), 0, False),
    ],
)
def test_chain_recognition_logic(edges, longest_chain_length, expected):
    result = make_result(
        num_agents=3,
        dependency_edges=edges,
        longest_chain_length=longest_chain_length,
    )
    assert result.matches_profile("chain") is expected


@pytest.mark.parametrize(
    "edges,expected",
    [
        (frozenset(), False),
        (frozenset({(0, 1)}), False),
        (frozenset({(0, 2), (1, 2)}), True),
        (frozenset({(0, 1), (1, 2)}), False),
        (frozenset({(0, 2), (1, 2), (2, 0)}), True),
    ],
)
def test_distributed_recognition_logic(edges, expected):
    result = make_result(
        num_agents=3,
        dependency_edges=edges,
        profile="distributed" if expected else "asymmetric",
    )
    assert result.matches_profile("distributed") is expected


def test_unknown_profile_raises_value_error():
    with pytest.raises(ValueError, match="Unknown cooperation profile"):
        make_result().matches_profile("nonexistent")
