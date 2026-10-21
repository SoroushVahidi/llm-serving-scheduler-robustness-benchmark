"""Strict, versioned client-to-scheduler metadata. No missing-class fallback."""
from dataclasses import dataclass
import math

TBT = {"tight": .1, "interactive": .1, "critical": .1,
       "medium": .3, "standard": .3, "loose": .5, "batch": .5}


@dataclass(frozen=True)
class RequestMetadata:
    request_id: str
    ordinal: int
    class_id: str
    arrival_s: float
    deadline_s: float
    weight: float

    def __post_init__(self):
        if not isinstance(self.request_id, str) or not self.request_id or type(self.ordinal) is not int or self.ordinal < 0:
            raise ValueError("Explicit request identity and nonnegative integer ordinal required")
        if not isinstance(self.class_id, str) or self.class_id not in TBT:
            raise ValueError(f"Unknown/missing SLAI class: {self.class_id!r}")
        if not all(type(x) in (int, float) and math.isfinite(x)
                   for x in (self.arrival_s, self.deadline_s, self.weight)):
            raise ValueError("Nonfinite workload metadata")
        if self.arrival_s < 0 or self.deadline_s < self.arrival_s or self.weight <= 0:
            raise ValueError("Invalid arrival, deadline or weight")

    def xargs(self):
        return {"lssp_schema": "mgpu00-v1", "lssp_request_id": self.request_id,
                "lssp_ordinal": self.ordinal, "lssp_class_id": self.class_id,
                "lssp_arrival_s": self.arrival_s, "lssp_deadline_s": self.deadline_s,
                "lssp_weight": self.weight}

    @classmethod
    def from_xargs(cls, value):
        if not isinstance(value, dict) or value.get("lssp_schema") != "mgpu00-v1":
            raise ValueError("Missing MGPU00 request metadata schema")
        try:
            return cls(value["lssp_request_id"], value["lssp_ordinal"], value["lssp_class_id"],
                       value["lssp_arrival_s"], value["lssp_deadline_s"], value["lssp_weight"])
        except KeyError as exc:
            raise ValueError(f"Missing required scheduler metadata: {exc}") from exc

    @classmethod
    def from_request(cls, request):
        return cls.from_xargs(getattr(getattr(request, "sampling_params", None), "extra_args", None))

    def admission_key(self, prompt_tokens):
        # Exact lexicographic ordering; never collapse TBT and length into a float.
        return TBT[self.class_id], prompt_tokens, self.ordinal
