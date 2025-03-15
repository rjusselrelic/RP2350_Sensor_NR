#Boilerplate code to store New Relic Metric
#in the New Relic API these are put together in an array to send multiple metrics at one

from typing import Any, List, TypeVar, Type, cast, Callable


T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_float(x: Any) -> float:
    assert isinstance(x, (float, int)) and not isinstance(x, bool)
    return float(x)


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def to_float(x: Any) -> float:
    assert isinstance(x, float)
    return x


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


class Attributes:
    app_name: str
    host_name: str

    def __init__(self, app_name: str, host_name: str) -> None:
        self.app_name = app_name
        self.host_name = host_name

    @staticmethod
    def from_dict(obj: Any) -> 'Attributes':
        assert isinstance(obj, dict)
        app_name = from_str(obj.get("app.name"))
        host_name = from_str(obj.get("host.name"))
        return Attributes(app_name, host_name)

    def to_dict(self) -> dict:
        result: dict = {}
        result["app.name"] = from_str(self.app_name)
        result["host.name"] = from_str(self.host_name)
        return result


class Metric:
    name: str
    type: str
    value: float
    timestamp: int
    attributes: Attributes

    def __init__(self, name: str, type: str, value: float, timestamp: int, attributes: Attributes) -> None:
        self.name = name
        self.type = type
        self.value = value
        self.timestamp = timestamp
        self.attributes = attributes

    @staticmethod
    def from_dict(obj: Any) -> 'Metric':
        assert isinstance(obj, dict)
        name = from_str(obj.get("name"))
        type = from_str(obj.get("type"))
        value = from_float(obj.get("value"))
        timestamp = from_int(obj.get("timestamp"))
        attributes = Attributes.from_dict(obj.get("attributes"))
        return Metric(name, type, value, timestamp, attributes)

    def to_dict(self) -> dict:
        result: dict = {}
        result["name"] = from_str(self.name)
        result["type"] = from_str(self.type)
        result["value"] = to_float(self.value)
        result["timestamp"] = from_int(self.timestamp)
        result["attributes"] = to_class(Attributes, self.attributes)
        return result


class NRMetricElement:
    metrics: List[Metric]

    def __init__(self, metrics: List[Metric]) -> None:
        self.metrics = metrics

    @staticmethod
    def from_dict(obj: Any) -> 'NRMetricElement':
        assert isinstance(obj, dict)
        metrics = from_list(Metric.from_dict, obj.get("metrics"))
        return NRMetricElement(metrics)

    def to_dict(self) -> dict:
        result: dict = {}
        result["metrics"] = from_list(lambda x: to_class(Metric, x), self.metrics)
        return result


def nr_metric_from_dict(s: Any) -> List[NRMetricElement]:
    return from_list(NRMetricElement.from_dict, s)


def nr_metric_to_dict(x: List[NRMetricElement]) -> Any:
    return from_list(lambda x: to_class(NRMetricElement, x), x)
