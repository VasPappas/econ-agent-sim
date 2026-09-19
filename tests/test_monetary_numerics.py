"""Independent checks of the dependency-free neighboring-block Newton kernel."""

from math import exp, sin

import pytest

from econ_agent_sim._monetary_numerics import (
    _block_solve,
    _jacobian,
    _solve_small,
    solve_blocks,
)


def test_small_system_pivots_and_multiple_right_hand_sides():
    matrix = [[0., 2., 0., 0.], [3., 0., 0., 0.],
              [0., 0., 0., 4.], [0., 0., 5., 0.]]
    expected = [[1., -2.], [3., -4.], [5., -6.], [7., -8.]]
    right = [[sum(matrix[i][j] * expected[j][k] for j in range(4))
              for k in range(2)] for i in range(4)]
    actual = _solve_small(matrix, right)
    for row, target in zip(actual, expected):
        assert row == pytest.approx(target, abs=1e-14)


def test_block_elimination_has_independently_small_linear_residual():
    count = 17
    lower = [[[.04 * (1 + i + j) for j in range(4)] for i in range(4)]
             for _ in range(count)]
    upper = [[[-.03 * (1 + i + 2 * j) for j in range(4)] for i in range(4)]
             for _ in range(count)]
    diagonal = [[[5. if i == j else .03 * (i - j) for j in range(4)]
                 for i in range(4)] for _ in range(count)]
    residual = [sin(.37 * i) for i in range(4 * count)]
    answer = _block_solve(lower, diagonal, upper, residual)
    errors = []
    for block in range(count):
        for row in range(4):
            value = residual[4 * block + row]
            for source, matrix in ((block - 1, lower[block]),
                                   (block, diagonal[block]),
                                   (block + 1, upper[block])):
                if 0 <= source < count:
                    value += sum(matrix[row][j] * answer[4 * source + j] for j in range(4))
            errors.append(value)
    assert max(map(abs, errors)) < 1e-14


@pytest.mark.parametrize("count", [1, 2, 3, 7])
def test_colored_jacobian_matches_independent_dense_differences(count):
    vector = [.1 + .007 * i for i in range(4 * count)]

    def evaluate(x):
        result = []
        for block in range(count):
            for row in range(4):
                value = exp(x[4 * block + row])
                for source in range(max(0, block - 1), min(count, block + 2)):
                    value += sum((.02 + .01 * row + .007 * j) * sin(x[4 * source + j])
                                 for j in range(4))
                result.append(value)
        return result

    lower, diagonal, upper = _jacobian(evaluate, vector, evaluate(vector))
    for column in range(len(vector)):
        plus, minus = vector[:], vector[:]
        plus[column] += 2e-6
        minus[column] -= 2e-6
        dense_column = [(a - b) / 4e-6 for a, b in zip(evaluate(plus), evaluate(minus))]
        source, variable = divmod(column, 4)
        for row, expected in enumerate(dense_column):
            target, equation = divmod(row, 4)
            if source == target - 1:
                actual = lower[target][equation][variable]
            elif source == target:
                actual = diagonal[target][equation][variable]
            elif source == target + 1:
                actual = upper[target][equation][variable]
            else:
                actual = 0.
            assert actual == pytest.approx(expected, abs=5e-10)


def test_colored_jacobian_uses_feasible_one_sided_difference():
    def evaluate(x):
        if min(x) < 0:
            raise ArithmeticError("Outside domain.")
        return [2 * z - 1 for z in x]

    _, diagonal, _ = _jacobian(evaluate, [0.] * 4, [-1.] * 4)
    for row in range(4):
        assert diagonal[0][row] == pytest.approx(
            [2. if row == column else 0. for column in range(4)], abs=1e-9,
        )


def test_nonlinear_complementarity_and_neighbor_coupling():
    count = 20

    def evaluate(x):
        result = []
        for block in range(count):
            a, b, c, d = x[4 * block:4 * block + 4]
            following = x[4 * (block + 1)] if block + 1 < count else 0.
            result.extend((exp(a) - 2, min(b, 3 - b), exp(c) - 4, d + following - 1))
        return result

    answer, used, status = solve_blocks(evaluate, [.1] * (4 * count), 30, 1e-10)
    assert status == "equations_converged"
    assert 0 < used <= 30
    assert max(map(abs, evaluate(answer))) <= 1e-10
    for b in answer[1::4]:
        assert b >= -1e-10
        assert 3 - b >= -1e-10
        assert abs(b * (3 - b)) < 1e-9


def test_already_solved_uses_no_iteration():
    answer, used, status = solve_blocks(lambda x: x, [0.] * 4, 1, 1e-12)
    assert (answer, used, status) == ([0.] * 4, 0, "equations_converged")


@pytest.mark.parametrize("initial", [[], [0.], [0.] * 5])
def test_incomplete_blocks_raise(initial):
    with pytest.raises(ValueError, match="four-variable"):
        solve_blocks(lambda x: x, initial, 2, 1e-10)


@pytest.mark.parametrize("callback", [
    lambda x: [float("nan")] * 4,
    lambda x: [float("inf")] * 4,
    lambda x: [0.] * 3,
    lambda x: [1.] * 4,
])
def test_invalid_or_singular_equations_fail_explicitly(callback):
    _, _, status = solve_blocks(callback, [0.] * 4, 10, 1e-10)
    assert status == "numerical_failure"


def test_iteration_budget_does_not_accept_unsolved_equations():
    def evaluate(x):
        return [exp(z) - 2 for z in x]

    answer, used, status = solve_blocks(evaluate, [0.] * 4, 1, 1e-12)
    assert used == 1
    assert status == "iteration_budget_exhausted"
    assert max(map(abs, evaluate(answer))) > 1e-12


def test_global_invertibility_does_not_mask_singular_local_block():
    # This globally invertible swap matrix needs pivoting between time blocks.
    # The intentionally smaller solver does not implement that fallback. It
    # must report failure, rather than return an uncertified Newton solution.
    def evaluate(x):
        return [value - 1 for value in x[4:] + x[:4]]

    answer, _, status = solve_blocks(evaluate, [0.] * 8, 5, 1e-12)
    assert status == "numerical_failure"
    assert max(map(abs, evaluate(answer))) > 1e-12
