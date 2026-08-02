from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import random
import re
import time
from typing import Mapping, Sequence

import numpy as np

from .proxy_qubo import SparseProxyQUBO


def qasm_gate_metrics(qasm: str) -> dict[str, int]:
    """Return the CNOT count and a conservative logical gate depth."""
    cnot_count = 0
    depths: dict[int, int] = {}
    for raw_line in str(qasm or "").splitlines():
        line = raw_line.strip().lower()
        if not line or line.startswith(("//", "openqasm", "include", "qreg", "creg", "barrier")):
            continue
        qubits = [int(value) for value in re.findall(r"q\[(\d+)\]", line)]
        if line.startswith("measure"):
            continue
        if line.startswith("cx "):
            cnot_count += 1
        if not qubits:
            continue
        layer = max((depths.get(qubit, 0) for qubit in set(qubits)), default=0) + 1
        for qubit in set(qubits):
            depths[qubit] = layer
    return {"cnot_count": cnot_count, "depth": max(depths.values(), default=0)}


@dataclass(frozen=True)
class QAOAParameters:
    depth: int
    gamma: tuple[float, ...]
    beta: tuple[float, ...]
    optimizer: str
    initial_value: float
    final_value: float
    evaluations: int

    def payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CompilationAudit:
    cnot_count: int
    swap_count: int
    depth: int
    two_qubit_gate_layers: int
    mapping_verified: bool
    uncalibrated_couplings: int
    passed: bool
    reasons: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class QAOARunResult:
    arm: str
    counts: dict[str, int]
    qasm: str
    physical_qasm: str
    parameters: QAOAParameters
    compilation: CompilationAudit
    shots: int
    seed: int
    task_id: str = ""
    backend: str = ""
    message: str = ""

    def payload(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "counts": dict(self.counts),
            "qasm": self.qasm,
            "physical_qasm": self.physical_qasm,
            "parameters": self.parameters.payload(),
            "compilation": self.compilation.payload(),
            "shots": self.shots,
            "seed": self.seed,
            "task_id": self.task_id,
            "backend": self.backend,
            "message": self.message,
        }


def _validate_parameters(
    depth: int,
    gamma: Sequence[float],
    beta: Sequence[float],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    depth = int(depth)
    if depth not in {1, 2, 3}:
        raise ValueError("QAOA depth must be p=1, p=2, or p=3.")
    gamma_values = tuple(float(value) for value in gamma)
    beta_values = tuple(float(value) for value in beta)
    if len(gamma_values) != depth or len(beta_values) != depth:
        raise ValueError("gamma and beta must contain one value per QAOA layer.")
    return gamma_values, beta_values


def build_qaoa_qasm(
    proxy: SparseProxyQUBO,
    depth: int,
    gamma: Sequence[float],
    beta: Sequence[float],
) -> str:
    gamma_values, beta_values = _validate_parameters(depth, gamma, beta)
    width = proxy.width
    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg q[{width}];",
        f"creg c[{width}];",
    ]
    lines.extend(f"h q[{index}];" for index in range(width))

    # QUBO x=(1-Z)/2 conversion. Global phases are omitted.
    ising_linear = [-coefficient / 2.0 for coefficient in proxy.linear]
    ising_quadratic: list[tuple[int, int, float]] = []
    for row in proxy.kept_interactions:
        ising_linear[row.left] -= row.coefficient / 4.0
        ising_linear[row.right] -= row.coefficient / 4.0
        ising_quadratic.append((row.left, row.right, row.coefficient / 4.0))

    for layer, (layer_gamma, layer_beta) in enumerate(zip(gamma_values, beta_values), start=1):
        lines.append(f"// qaoa_layer_{layer}")
        for index, coefficient in enumerate(ising_linear):
            if abs(coefficient) > 1e-15:
                lines.append(f"rz({2.0 * layer_gamma * coefficient:.12g}) q[{index}];")
        for left, right, coefficient in ising_quadratic:
            lines.append(f"cx q[{left}],q[{right}];")
            lines.append(f"rz({2.0 * layer_gamma * coefficient:.12g}) q[{right}];")
            lines.append(f"cx q[{left}],q[{right}];")
        lines.extend(f"rx({2.0 * layer_beta:.12g}) q[{index}];" for index in range(width))
    lines.extend(f"measure q[{index}] -> c[{index}];" for index in range(width))
    return "\n".join(lines) + "\n"


def _statevector(
    proxy: SparseProxyQUBO,
    gamma: Sequence[float],
    beta: Sequence[float],
) -> np.ndarray:
    width = proxy.width
    size = 1 << width
    state = np.ones(size, dtype=np.complex128) / math.sqrt(size)
    energies = np.array(
        [proxy.energy(tuple((basis >> index) & 1 for index in range(width))) for basis in range(size)],
        dtype=np.float64,
    )
    for layer_gamma, layer_beta in zip(gamma, beta):
        state *= np.exp(-1j * float(layer_gamma) * energies)
        cosine = math.cos(float(layer_beta))
        minus_i_sine = -1j * math.sin(float(layer_beta))
        for qubit in range(width):
            step = 1 << qubit
            for base in range(0, size, step * 2):
                for offset in range(step):
                    zero = base + offset
                    one = zero + step
                    amp_zero, amp_one = state[zero], state[one]
                    state[zero] = cosine * amp_zero + minus_i_sine * amp_one
                    state[one] = minus_i_sine * amp_zero + cosine * amp_one
    return state


def expected_proxy_energy(
    proxy: SparseProxyQUBO,
    gamma: Sequence[float],
    beta: Sequence[float],
) -> float:
    state = _statevector(proxy, gamma, beta)
    probabilities = np.abs(state) ** 2
    energies = np.array(
        [proxy.energy(tuple((basis >> index) & 1 for index in range(proxy.width))) for basis in range(1 << proxy.width)],
        dtype=np.float64,
    )
    return float(np.dot(probabilities, energies))


def pretrain_parameters(
    proxy: SparseProxyQUBO,
    depth: int,
    initial_gamma: Sequence[float] | None = None,
    initial_beta: Sequence[float] | None = None,
    rounds: int = 2,
) -> QAOAParameters:
    depth = int(depth)
    gamma = list(initial_gamma or [0.8] * depth)
    beta = list(initial_beta or [0.4] * depth)
    _validate_parameters(depth, gamma, beta)
    initial_value = expected_proxy_energy(proxy, gamma, beta)
    best_value = initial_value
    evaluations = 1
    step = 0.40
    for _round in range(max(0, int(rounds))):
        for family in (gamma, beta):
            for index in range(depth):
                original = family[index]
                candidates = [original - step, original, original + step]
                scored = []
                for caó_u¶‰žËkºwµçA9½¹”€ô9½¹”(€€€€€€€…•ÁÑ•‘}…ÍÍ¥¹µ•¹Ð€ô9½¹”(€€€€€€€ÍÑ•Á}ÍÑ…ÑÕÌ€ô€‰=5A1Qˆ(€€€€€€€‘•¥Í¥½¸€ô€‰É•©•Ñ•è¹¼ÍÑÉ¥Ñ±äÍ¡½ÉÑ•È™•…Í¥‰±”…¹‘¥‘…Ñ”¥¸Q½Àµ¬ˆ(€€€€€€€¥˜Ù…±¥‘…Ñ¥½¹}•ÉÉ½Èè(€€€€€€€€€€€ÍÑ•Á}ÍÑ…ÑÕÌ€ô€‰9=Q}Y1U	1ˆ¥˜¹½Ð½¹™¥œ¹ÍÕ‰µ¥Ñ}¡…É‘Ý…É”•±Í”€‰%1ˆ(€€€€€€€€€€€¥˜Í½ÕÉ”€„ô€‰¡…É‘Ý…É”ˆè(€€€€€€€€€€€€€€€ÍÑ•Á}ÍÑ…ÑÕÌ€ô€‰%1ˆ(€€€€€€€€€€€‘•¥Í¥½¸€ô˜‰É•©•Ñ•èíÙ…±¥‘…Ñ¥½¹}•ÉÉ½Éôˆ(€€€€€€€€€€€¥˜½Ù•É…±±}ÍÑ…ÑÕÌ€„ô€‰%1ˆè(€€€€€€€€€€€€€€€½Ù•É…±±}ÍÑ…ÑÕÌ€ôÍÑ•Á}ÍÑ…ÑÕÌ(€€€€€€€•±Í”è(€€€€€€€€€€€…¹‘¥‘…Ñ•}‰…Ñ °…•ÁÑ•‘}…ÍÍ¥¹µ•¹Ð€ô•Ù…±Õ…Ñ•}½Õ¹ÑÌ (€€€€€€€€€€€€€€€…É´õÉÕ¸¹…É´°(€€€€€€€€€€€€€€€½Õ¹ÑÌõÉÕ¸¹½Õ¹ÑÌ°(€€€€€€€€€€€€€€€ÁÉ½áäõÁÉ½áä°(€€€€€€€€€€€€€€€…ÍÍ¥¹µ•¹ÑÌõÕÉÉ•¹Ð°(€€€€€€€€€€€€€€€‰±½­}ÕÍÑ½µ•ÉÌõ‰±½­}ÕÍÑ½µ•ÉÌ°(€€€€€€€€€€€€€€€‘•Á½Ðõ¥¹ÍÑ…¹”¹‘•Á½Ð°(€€€€€€€€€€€€€€€Ù•¡¥±•}…Á…¥Ñäõ¥¹ÍÑ…¹”¹Ù•¡¥±•}…Á…¥Ñä°(€€€€€€€€€€€€€€€…¹‘¥‘…Ñ•}¬ô Ä€ððÁÉ½áä¹Ý¥‘Ñ ¤¥˜Í½ÕÉ”€ôô€‰•á…Ðˆ•±Í”½¹™¥œ¹…¹‘¥‘…Ñ•}¬°(€€€€€€€€€€€€€€€É½ÕÑ¥¹}µ•Ñ¡½õ½¹™¥œ¹É½ÕÑ¥¹}µ•Ñ¡½°(€€€€€€€€€€€€¤(€€€€€€€€€€€¥˜…•ÁÑ•‘}…ÍÍ¥¹µ•¹Ð¥Ì¹½Ð9½¹”è(€€€€€€€€€€€€€€€ÕÉÉ•¹Ð€ô…•ÁÑ•‘}…ÍÍ¥¹µ•¹Ð(€€€€€€€€€€€€€€€…•ÁÑ•‘}µ½Ù•Ì€¬ô€Ä(€€€€€€€€€€€€€€€‘•¥Í¥½¸€ô€ (€€€€€€€€€€€€€€€€€€€˜‰…•ÁÑ•èÍÑÉ¥Ñ±äÍ¡½ÉÑ•È‰ä€ˆ(€€€€€€€€€€€€€€€€€€€˜‰í…¹‘¥‘…Ñ•}‰…Ñ ¹…•ÁÑ•¹¥µÁÉ½Ù•µ•¹Ðè¸Ù™ôˆ(€€€€€€€€€€€€€€€€¤(€€€€€€€…™Ñ•È€ôÑÉÕ•}É½ÕÑ•}‘¥ÍÑ…¹”¡ÕÉÉ•¹Ð°¥¹ÍÑ…¹”¹‘•Á½Ð°É½ÕÑ¥¹}µ•Ñ¡½õ½¹™¥œ¹É½ÕÑ¥¹}µ•Ñ¡½¤(€€€€€€€ÑÉ…•Ì¹…ÁÁ•¹ (€€€€€€€€€€€	±½­QÉ…” (€€€€€€€€€€€€€€€Í•ÅÕ•¹”õ¥¹‘•à°(€€€€€€€€€€€€€€€‰±½¬õ‰±½¬°(€€€€€€€€€€€€€€€Í½ÕÉ”õÍ½ÕÉ”°(€€€€€€€€€€€€€€€‰…Í•±¥¹•}‘¥ÍÑ…¹”õ‰•™½É”°(€€€€€€€€€€€€€€€‘¥ÍÑ…¹•}…™Ñ•Èõ…™Ñ•È°(€€€€€€€€€€€€€€€…•ÁÑ•õ…•ÁÑ•‘}…ÍÍ¥¹µ•¹Ð¥Ì¹½Ð9½¹”°(€€€€€€€€€€€€€€€‘•¥Í¥½¸õ‘•¥Í¥½¸°(€€€€€€€€€€€€€€€ÁÉ½áäõÁÉ½áä°(€€€€€€€€€€€€€€€ÉÕ¸õÉÕ¸°(€€€€€€€€€€€€€€€…¹‘¥‘…Ñ•Ìõ…¹‘¥‘…Ñ•}‰…Ñ °(€€€€€€€€€€€€€€€ÍÑ…ÑÕÌõÍÑ•Á}ÍÑ…ÑÕÌ°(€€€€€€€€€€€€¤(€€€€€€€€¤((€€€¥˜Í½ÕÉ”€ôô€‰¡…É‘Ý…É”ˆ…¹¹½Ð½¹™¥œ¹ÍÕ‰µ¥Ñ}¡…É‘Ý…É”è(€€€€€€€½Ù•É…±±}ÍÑ…ÑÕÌ€ô€‰9=Q}Y1U	1ˆ(€€€€€€€µ•ÍÍ…•Ì¹…ÁÁ•¹ ‰!…É‘Ý…É”µ½‘”½µÁ±•Ñ•…Ì„Õ…É‘•‘ÉäµÉÕ¸ì¹¼Ñ…Í¬Ý…ÌÍÕ‰µ¥ÑÑ•¸ˆ¤(€€€™¥¹…±}‘¥ÍÑ…¹”€ôÑÉÕ•}É½ÕÑ•}‘¥ÍÑ…¹”¡ÕÉÉ•¹Ð°¥¹ÍÑ…¹”¹‘•Á½Ð°É½ÕÑ¥¹}µ•Ñ¡½õ½¹™¥œ¹É½ÕÑ¥¹}µ•Ñ¡½¤(€€€É•ÑÕÉ¸••Á	±½­I•ÍÕ±Ð (€€€€€€€µ½‘”õ¹½Éµ…±¥é•‘}µ½‘”°(€€€€€€€Í½ÕÉ”õÍ½ÕÉ”°(€€€€€€€ÍÑ…ÑÕÌõ½Ù•É…±±}ÍÑ…ÑÕÌ°(€€€€€€€µ•ÍÍ…”ôˆð€ˆ¹©½¥¸¡µ•ÍÍ…•Ì¤½È€‰••Á	±½¬Í…¸½µÁ±•Ñ•¸ˆ°(€€€€€€€‰…Í•±¥¹•}‘¥ÍÑ…¹”õ‰…Í•±¥¹”°(€€€€€€€™¥¹…±}‘¥ÍÑ…¹”õ™¥¹…±}‘¥ÍÑ…¹”°(€€€€€€€…•ÁÑ•‘}µ½Ù•Ìõ…•ÁÑ•‘}µ½Ù•Ì°(€€€€€€€‰±½­ÌõÑÕÁ±”¡‰±½­Ì¤°(€€€€€€€…¹‘¥‘…Ñ•}Á½½°õÑÕÁ±”¡Á½½°¤°(€€€€€€€…ÍÍ¥¹µ•¹ÑÌõÕÉÉ•¹Ð°(€€€€€€€ÑÉ…•ÌõÑÕÁ±”¡ÑÉ…•Ì¤°(€€€€¤