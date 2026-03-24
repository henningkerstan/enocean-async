from typing import Any, Callable

# Type aliases for semantic resolvers and instruction encoders.
# Using Any to avoid circular imports (capabilities/ imports from eep/).
type SemanticResolver = Callable[[dict[str, Any], dict[str, Any]], Any | None]
type InstructionEncoder = Callable[
    [Any, dict[str, Any]], Any
]  # (Instruction, options) → RawEEPMessage
