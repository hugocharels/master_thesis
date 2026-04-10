from lle import World

from generators.world_builder import Direction, WorldBuilder
from solver import CooperationProfileAnalyzer, CooperationProfileResult, LLEAdapter


def analyze(world: World, t: int):
    world.reset()
    adapted = LLEAdapter(world)
    return CooperationProfileAnalyzer(adapted, T_MAX=t).analyze()


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


def test_lle_level_1_is_independent():
    result = analyze(World.level(1), 10)

    assert result.solvable is True
    assert result.cooperation_required is False
    assert result.profile == "independent"
    assert result.necessary_helpers == frozenset()
    assert result.dependency_edges == frozenset()
    assert result.matches_profile("independent")
    assert not result.matches_profile("cooperative")


def test_lle_level_2_is_independent():
    result = analyze(World.level(2), 10)

    assert result.solvable is True
    assert result.cooperation_required is False
    assert result.profile == "independent"
    assert result.necessary_helpers == frozenset()
    assert result.dependency_edges == frozenset()


def test_lle_level_3_is_asymmetric():
    result = analyze(World.level(3), 10)

    assert result.solvable is True
    assert result.cooperation_required is True
    assert result.necessary_helpers == frozenset({0})
    assert result.matches_profile("cooperative")
    assert result.matches_profile("asymmetric")
    assert not result.matches_profile("mutual")
    assert not result.matches_profile("fully_coupled")
    assert (0, 1) in result.dependency_edges


def test_lle_level_4_is_mutual():
    result = analyze(World.level(4), 10)

    assert result.solvable is True
    assert result.cooperation_required is True
    assert result.necessary_helpers == frozenset({0, 1})
    assert result.matches_profile("cooperative")
    assert result.matches_profile("mutual")
    assert result.matches_profile("fully_coupled")
    assert (0, 1) in result.dependency_edges
    assert (1, 0) in result.dependency_edges
    assert result.largest_scc_size == 2


def test_custom_three_agent_level_is_distributed():
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
    assert result.profile == "distributed"
    assert result.matches_profile("distributed")
    assert not result.matches_profile("mutual")
    assert result.necessary_helpers == frozenset({0, 1})
    assert result.dependency_edges == frozenset({(0, 1), (0, 2), (1, 2)})


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


def test_profile_matching_recognizes_all_supported_types():
    independent = make_result(
        cooperation_required=False,
        necessary_helpers=frozenset(),
        dependency_edges=frozenset(),
        longest_chain_length=0,
        profile="independent",
    )
    assert independent.matches_profile("independent")
    assert not independent.matches_profile("cooperative")

    asymmetric = make_result()
    assert asymmetric.matches_profile("asymmetric")
    assert asymmetric.matches_profile("cooperative")

    mutual = make_result(
        num_agents=2,
        necessary_helpers=frozenset({0, 1}),
        dependency_edges=frozenset({(0, 1), (1, 0)}),
        mutual_pairs=frozenset({(0, 1)}),
        largest_scc_size=2,
        profile="mutual",
    )
    assert mutual.matches_profile("mutual")

    chain = make_result(
        num_agents=3,
        necessary_helpers=frozenset({0, 1}),
        dependency_edges=frozenset({(0, 1), (1, 2)}),
        longest_chain_length=2,
        profile="asymmetric",
    )
    assert chain.matches_profile("chain")
    assert not chain.matches_profile("distributed")

    distributed = make_result(
        num_agents=3,
        necessary_helpers=frozenset({0, 1}),
        dependency_edges=frozenset({(0, 2), (1, 2)}),
        profile="distributed",
    )
    assert distributed.matches_profile("distributed")
    assert not distributed.matches_profile("chain")

    fully_coupled = make_result(
        num_agents=3,
        necessary_helpers=frozenset({0, 1, 2}),
        dependency_edges=frozenset({(0, 1), (1, 2), (2, 0)}),
        largest_scc_size=3,
        profile="fully_coupled",
    )
    assert fully_coupled.matches_profile("fully_coupled")
