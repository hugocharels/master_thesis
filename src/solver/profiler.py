import csv
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ConstraintProfile:
    """Profile data for a single constraint type"""

    name: str
    num_clauses: int
    generation_time: float
    method_profiles: Dict[str, Dict[str, Any]]  # method_name -> {clauses, time}


class SolverProfiler:
    """Collects profiling data during SAT solving"""

    def __init__(self):
        self.constraint_profiles: Dict[str, ConstraintProfile] = {}
        self.total_clauses = 0
        self.total_generation_time = 0.0
        self.solve_time = 0.0
        self.satisfiable = None

    def start_constraint(self, constraint_name: str) -> "ConstraintProfiler":
        """Start profiling a constraint"""
        return ConstraintProfiler(self, constraint_name)

    def add_constraint_profile(self, profile: ConstraintProfile):
        """Add a completed constraint profile"""
        self.constraint_profiles[profile.name] = profile
        self.total_clauses += profile.num_clauses
        self.total_generation_time += profile.generation_time

    def set_solve_results(self, solve_time: float, satisfiable):
        """Record solving results"""
        self.solve_time = solve_time
        self.satisfiable = satisfiable

    def to_dict(self) -> Dict[str, Any]:
        """Convert profiling data to dictionary"""
        return {
            "total_clauses": self.total_clauses,
            "total_generation_time": self.total_generation_time,
            "solve_time": self.solve_time,
            "satisfiable": self.satisfiable,
            "constraints": {
                name: asdict(profile)
                for name, profile in self.constraint_profiles.items()
            },
        }

    def to_json(self, filepath: Optional[str] = None) -> str:
        """Export profiling data as JSON"""
        data = self.to_dict()
        json_str = json.dumps(data, indent=2)
        if filepath:
            Path(filepath).write_text(json_str)
        return json_str

    def to_csv(self, filepath: str):
        """Export profiling data as CSV"""
        rows = []
        for constraint_name, profile in self.constraint_profiles.items():
            # Main constraint row
            rows.append(
                {
                    "constraint": constraint_name,
                    "method": "TOTAL",
                    "num_clauses": profile.num_clauses,
                    "time": profile.generation_time,
                }
            )
            # Method-specific rows
            for method_name, method_data in profile.method_profiles.items():
                rows.append(
                    {
                        "constraint": constraint_name,
                        "method": method_name,
                        "num_clauses": method_data["clauses"],
                        "time": method_data["time"],
                    }
                )

        with open(filepath, "w", newline="") as f:
            if rows:
                writer = csv.DictWriter(
                    f, fieldnames=["constraint", "method", "num_clauses", "time"]
                )
                writer.writeheader()
                writer.writerows(rows)


class ConstraintProfiler:
    """Context manager for profiling a single constraint"""

    def __init__(self, solver_profiler: SolverProfiler, constraint_name: str):
        self.solver_profiler = solver_profiler
        self.constraint_name = constraint_name
        self.start_time = 0.0
        self.total_clauses = 0
        self.method_profiles = {}

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        generation_time = end_time - self.start_time

        profile = ConstraintProfile(
            name=self.constraint_name,
            num_clauses=self.total_clauses,
            generation_time=generation_time,
            method_profiles=self.method_profiles,
        )
        self.solver_profiler.add_constraint_profile(profile)

    def profile_method(self, method_name: str):
        """Get a method profiler for a specific constraint method"""
        return MethodProfiler(self, method_name)

    def add_clauses(self, num_clauses: int):
        """Add clauses to the total count"""
        self.total_clauses += num_clauses


class MethodProfiler:
    """Context manager for profiling a constraint method"""

    def __init__(self, constraint_profiler: ConstraintProfiler, method_name: str):
        self.constraint_profiler = constraint_profiler
        self.method_name = method_name
        self.start_time = 0.0
        self.clause_count = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        method_time = end_time - self.start_time

        self.constraint_profiler.method_profiles[self.method_name] = {
            "clauses": self.clause_count,
            "time": method_time,
        }
        self.constraint_profiler.add_clauses(self.clause_count)

    def count_clauses(self, clauses):
        """Count clauses from a generator/iterator"""
        clause_list = list(clauses)
        self.clause_count += len(clause_list)
        return clause_list
