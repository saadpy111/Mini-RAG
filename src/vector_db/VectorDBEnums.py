from enum import StrEnum

class VectorDBType(StrEnum):
    QDRANT = "qdrant"


class DistanceMethodEnums(StrEnum):
    COSINE = "cosine"
    DOT = "dot"
    EUCLIDEAN = "euclidean"