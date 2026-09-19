"""Small dependency-free block Newton kernel for the monetary reference.

The callback returns four scaled equations per four-variable time block. Each
equation block may depend on its own block and the immediately adjacent blocks
only. Economic admissibility and certification belong to the caller.
"""

from math import isfinite


def _solve_small(matrix, right):
    """Solve one four-by-four system with several right-hand sides."""
    size = len(matrix)
    width = len(right[0])
    rows = [list(a) + list(b) for a, b in zip(matrix, right)]
    scale = max(abs(x) for row in matrix for x in row)
    if not isfinite(scale) or scale == 0:
        raise ArithmeticError("Singular Newton block.")
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(rows[row][column]))
        if abs(rows[pivot][column]) <= 1e-14 * scale:
            raise ArithmeticError("Singular Newton block.")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        for j in range(column, size + width):
            rows[column][j] /= divisor
        for row in range(column + 1, size):
            factor = rows[row][column]
            for j in range(column, size + width):
                rows[row][j] -= factor * rows[column][j]
    answer = [[0.] * width for _ in range(size)]
    for row in range(size - 1, -1, -1):
        for column in range(width):
            answer[row][column] = rows[row][size + column] - sum(
                rows[row][j] * answer[j][column] for j in range(row + 1, size)
            )
    if not all(isfinite(x) for row in answer for x in row):
        raise ArithmeticError("Unrepresentable Newton direction.")
    return answer


def _block_solve(lower, diagonal, upper, residual):
    """Block Thomas elimination, with pivoting inside each four-by-four block."""
    transformed = []
    for block, original in enumerate(diagonal):
        matrix = [row[:] for row in original]
        right = [upper[block][j][:] + [-residual[4 * block + j]] for j in range(4)]
        if block:
            previous = transformed[-1]
            for row in range(4):
                for column in range(4):
                    matrix[row][column] -= sum(
                        lower[block][row][j] * previous[j][column] for j in range(4)
                    )
                right[row][4] -= sum(
                    lower[block][row][j] * previous[j][4] for j in range(4)
                )
        transformed.append(_solve_small(matrix, right))
    answer = [[0.] * 4 for _ in diagonal]
    for block in range(len(diagonal) - 1, -1, -1):
        for row in range(4):
            answer[block][row] = transformed[block][row][4]
            if block + 1 < len(diagonal):
                answer[block][row] -= sum(
                    transformed[block][row][j] * answer[block + 1][j] for j in range(4)
                )
    return [x for block in answer for x in block]


def _checked(evaluate, vector):
    result = list(evaluate(vector))
    if len(result) != len(vector) or not all(isfinite(x) for x in result):
        raise ArithmeticError("Invalid Newton residual.")
    return result


def _jacobian(evaluate, vector, residual):
    count = len(vector) // 4
    lower, diagonal, upper = (
        [[[0.] * 4 for _ in range(4)] for _ in range(count)] for _ in range(3)
    )
    # Three block colors make the affected row neighborhoods disjoint. Central
    # differences thus need 24 callback evaluations, irrespective of horizon.
    step = min(1e-6, max(1e-8, max(map(abs, residual)) * 1e-3))
    for color in range(3):
        for variable in range(4):
            sources = list(range(color, count, 3))
            if not sources:
                continue
            samples = []
            for sign in (1., -1.):
                trial = list(vector)
                for source in sources:
                    trial[4 * source + variable] += sign * step
                try:
                    samples.append(_checked(evaluate, trial))
                except (ArithmeticError, ValueError):
                    samples.append(None)
            plus, minus = samples
            if plus is None and minus is None:
                raise ArithmeticError("No admissible finite-difference direction.")
            left, right, divisor = (plus, minus, 2 * step)
            if plus is None:
                left, right, divisor = residual, minus, step
            elif minus is None:
                left, right, divisor = plus, residual, step
            for source in sources:
                for target in range(max(0, source - 1), min(count, source + 2)):
                    destination = (lower if source < target else
                                   upper if source > target else diagonal)
                    for equation in range(4):
                        index = 4 * target + equation
                        destination[target][equation][variable] = (
                            left[index] - right[index]
                        ) / divisor
    return lower, diagonal, upper


def solve_blocks(evaluate, initial, max_iterations, tolerance):
    """Return ``(vector, iterations, status)`` without accepting unchecked paths.

    Coordinates should already be dimensionless transforms (such as log capital
    or logit labor). Negative investment or dividends may occur in Newton trials;
    their feasibility must be encoded in the caller's complementarity equations.
    """
    vector = list(initial)
    if not vector or len(vector) % 4:
        raise ValueError("The Newton vector needs complete four-variable blocks.")
    used = 0
    try:
        residual = _checked(evaluate, vector)
        while True:
            norm = max(map(abs, residual))
            if norm <= tolerance:
                return vector, used, "equations_converged"
            if used >= max_iterations:
                return vector, used, "iteration_budget_exhausted"
            lower, diagonal, upper = _jacobian(evaluate, vector, residual)
            direction = _block_solve(lower, diagonal, upper, residual)
            largest = max(map(abs, direction))
            fraction = min(1., 2. / largest) if largest else 1.
            used += 1
            for _ in range(45):
                trial = [x + fraction * dx for x, dx in zip(vector, direction)]
                try:
                    candidate = _checked(evaluate, trial)
                    merit = max(map(abs, candidate))
                except (ArithmeticError, ValueError):
                    merit = float("inf")
                if merit <= tolerance or merit < norm * (1 - 1e-4 * fraction):
                    vector, residual = trial, candidate
                    break
                fraction *= .5
            else:
                return vector, used, "line_search_failed"
    except (ArithmeticError, ValueError):
        return vector, used, "numerical_failure"
