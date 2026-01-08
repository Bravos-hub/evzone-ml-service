"""
Unit tests for KafkaConsumer.
"""
import json

import pytest

from src.config.settings import settings
from src.kafka.consumer import KafkaConsumer
from src.kafka.topics import ANOMALIES_TOPIC, FAILURE_ALERTS_TOPIC, CHARGER_METRICS_TOPIC


class DummyProducer:
    def __init__(self):
        self.published = []
        self.started = False

    async def start(self):
        self.started = True

    async def publish(self, topic, payload):
        self.published.append((topic, payload))


class FailingProducer(DummyProducer):
    async def start(self):
        raise RuntimeError("boom")


class DummyDataCollector:
    def __init__(self):
        self.calls = []

    async def collect_charger_metrics(self, message):
        self.calls.append(message)


class DummyDetector:
    def __init__(self, is_anomaly=True):
        self.is_anomaly = is_anomaly
        self.calls = []

    def detect(self, metrics, tenant_id=None):
        self.calls.append((metrics, tenant_id))
        return {
            "charger_id": metrics.get("charger_id"),
            "is_anomaly": self.is_anomaly,
            "anomaly_score": 90.0,
            "anomaly_type": "TEST",
        }


class DummyModelManager:
    def __init__(self, detector=None):
        self.detector = detector
        self.calls = []

    async def get_model(self, model_name):
        self.calls.append(model_name)
        if model_name == "anomaly_detector":
            return self.detector
        return None


class DummyPredictionService:
    def __init__(self, failure_probability=0.9, detector=None):
        self.failure_probability = failure_probability
        self.calls = []
        self.model_manager = DummyModelManager(detector=detector)

    async def predict_failure(self, charger_id, metrics, tenant_id=None):
        self.calls.append((charger_id, metrics, tenant_id))
        return {
            "charger_id": charger_id,
            "failure_probability": self.failure_probability,
        }


class DummyConsumer:
    def __init__(self, config):
        self.config = config
        self.subscriptions = []
        self.closed = False

    def subscribe(self, topics):
        self.subscriptions.append(list(topics))

    def close(self):
        self.closed = True


class DummyError:
    def __init__(self, code):
        self._code = code

    def code(self):
        return self._code

    def __str__(self):
        return f"DummyError({self._code})"


class DummyMsg:
    def __init__(self, error=None, value=b"{}"):
        self._error = error
        self._value = value

    def error(self):
        return self._error

    def value(self):
        return self._value


class DummyPollConsumer:
    def __init__(self, owner, messages):
        self.owner = owner
        self._messages = list(messages)
        self._idx = 0

    def poll(self, timeout=1.0):
        if self._idx >= len(self._messages):
            self.owner.running = False
            return None
        msg = self._messages[self._idx]
        self._idx += 1
        self.owner.running = False
        return msg


@pytest.mark.asyncio
async def test_consumer_start_subscribes(monkeypatch):
    dummy_producer = DummyProducer()
    data_collector = DummyDataCollector()
    prediction_service = DummyPredictionService()

    monkeypatch.setattr("src.kafka.consumer.Consumer", DummyConsumer)

    async def fake_consume(self):
        self.running = False

    monkeypatch.setattr(KafkaConsumer, "_consume_loop", fake_consume)

    consumer = KafkaConsumer(data_collector, prediction_service, producer=dummy_producer)
    await consumer.start()

    assert consumer.consumer.subscriptions == [[CHARGER_METRICS_TOPIC]]
    assert dummy_producer.started is True
    assert consumer.running is False


@pytest.mark.asyncio
async def test_consumer_start_error(monkeypatch):
    dummy_producer = FailingProducer()
    data_collector = DummyDataCollector()
    prediction_service = DummyPredictionService()

    monkeypatch.setattr("src.kafka.consumer.Consumer", DummyConsumer)

    consumer = KafkaConsumer(data_collector, prediction_service, producer=dummy_producer)
    with pytest.raises(RuntimeError):
        await consumer.start()


@pytest.mark.asyncio
async def test_process_message_missing_charger_id(monkeypatch):
    monkeypatch.setattr(settings, "enable_predictions", True)
    producer = DummyProducer()
    data_collector = DummyDataCollector()
    prediction_service = DummyPredictionService()

    consumer = KafkaConsumer(data_collector, prediction_service, producer=producer)

    message = {"metrics": {"temperature": 20.0}}
    await consumer._process_message(json.dumps(message))

    assert data_collector.calls == []
    assert prediction_service.calls == []
    assert producer.published == []


@pytest.mark.asyncio
async def test_process_message_exception_branch(monkeypatch):
    producer = DummyProducer()
    data_collector = DummyDataCollector()
    prediction_service = DummyPredictionService()

    consumer = KafkaConsumer(data_collector, prediction_service, producer=producer)
    await consumer._process_message("not-json")


@pytest.mark.asyncio
async def test_process_message_publishes_alerts(monkeypatch):
    monkeypatch.setattr(settings, "enable_predictions", True)
    producer = DummyProducer()
    data_collector = DummyDataCollector()
    detector = DummyDetector(is_anomaly=True)
    prediction_service = DummyPredictionService(failure_probability=0.9, detector=detector)

    consumer = KafkaConsumer(data_collector, prediction_service, producer=producer)

    message = {
        "charger_id": "c1",
        "tenant_id": "t1",
        "metrics": {"temperature": 70.0},
    }
    await consumer._process_message(json.dumps(message))

    assert len(data_collector.calls) == 1
    assert data_collector.calls[0]["metrics"]["charger_id"] == "c1"
    assert len(prediction_service.calls) == 1

    topics = {topic for topic, _ in producer.published}
    assert FAILURE_ALERTS_TOPIC in topics
    assert ANOMALIES_TOPIC in topics


@pytest.mark.asyncio
async def test_process_message_predictions_disabled(monkeypatch):
    monkeypatch.setattr(settings, "enable_predictions", False)
    producer = DummyProducer()
    data_collector = DummyDataCollector()
    detector = DummyDetector(is_anomaly=True)
    prediction_service = DummyPredictionService(failure_probability=0.9, detector=detector)

    consumer = KafkaConsumer(data_collector, prediction_service, producer=producer)

    message = {
        "charger_id": "c1",
        "metrics": {"temperature": 70.0},
    }
    await consumer._process_message(json.dumps(message))

    assert prediction_service.calls == []
    topics = {topic for topic, _ in producer.published}
    assert FAILURE_ALERTS_TOPIC not in topics
    assert ANOMALIES_TOPIC in topics


@pytest.mark.asyncio
async def test_stop_closes_consumer():
    producer = DummyProducer()
    data_collector = DummyDataCollector()
    prediction_service = DummyPredictionService()

    consumer = KafkaConsumer(data_collector, prediction_service, producer=producer)
    consumer.consumer = DummyConsumer(config={})
    consumer.running = True

    await consumer.stop()

    assert consumer.running is False
    assert consumer.consumer.closed is True


@pytest.mark.asyncio
async def test_consume_loop_partition_eof(monkeypatch):
    class DummyKafkaError:
        _PARTITION_EOF = 1

    monkeypatch.setattr("src.kafka.consumer.KafkaError", DummyKafkaError)

    producer = DummyProducer()
    data_collector = DummyDataCollector()
    prediction_service = DummyPredictionService()
    consumer = KafkaConsumer(data_collector, prediction_service, producer=producer)

    called = {"count": 0}

    async def fake_process(self, value):
        called["count"] += 1

    monkeypatch.setattr(KafkaConsumer, "_process_message", fake_process)

    msg = DummyMsg(error=DummyError(DummyKafkaError._PARTITION_EOF))
    consumer.consumer = DummyPollConsumer(consumer, [msg])
    consumer.running = True

    await consumer._consume_loop()

    assert called["count"] == 0


@pytest.mark.asyncio
async def test_consume_loop_error_logs_and_skips(monkeypatch):
    class DummyKafkaError:
        _PARTITION_EOF = 1

    monkeypatch.setattr("src.kafka.consumer.KafkaError", DummyKafkaError)

    producer = DummyProducer()
    data_collector = DummyDataCollector()
    prediction_service = DummyPredictionService()
    consumer = KafkaConsumer(data_collector, prediction_service, producer=producer)

    called = {"count": 0}

    async def fake_process(self, value):
        called["count"] += 1

    monkeypatch.setattr(KafkaConsumer, "_process_message", fake_process)

    msg = DummyMsg(error=DummyError(999))
    consumer.consumer = DummyPollConsumer(consumer, [msg])
    consumer.running = True

    await consumer._consume_loop()

    assert called["count"] == 0


@pytest.mark.asyncio
async def test_consume_loop_processes_message(monkeypatch):
    class DummyKafkaError:
        _PARTITION_EOF = 1

    monkeypatch.setattr("src.kafka.consumer.KafkaError", DummyKafkaError)

    producer = DummyProducer()
    data_collector = DummyDataCollector()
    prediction_service = DummyPredictionService()
    consumer = KafkaConsumer(data_collector, prediction_service, producer=producer)

    seen = {"value": None}

    async def fake_process(self, value):
        seen["value"] = value

    monkeypatch.setattr(KafkaConsumer, "_process_message", fake_process)

    msg = DummyMsg(error=None, value=b'{"charger_id":"c1"}')
    consumer.consumer = DummyPollConsumer(consumer, [msg])
    consumer.running = True

    await consumer._consume_loop()

    assert seen["value"] == '{"charger_id":"c1"}'


@pytest.mark.asyncio
async def test_consume_loop_none_message(monkeypatch):
    producer = DummyProducer()
    data_collector = DummyDataCollector()
    prediction_service = DummyPredictionService()
    consumer = KafkaConsumer(data_collector, prediction_service, producer=producer)

    called = {"count": 0}

    async def fake_process(self, value):
        called["count"] += 1

    monkeypatch.setattr(KafkaConsumer, "_process_message", fake_process)

    consumer.consumer = DummyPollConsumer(consumer, [None])
    consumer.running = True

    await consumer._consume_loop()

    assert called["count"] == 0


@pytest.mark.asyncio
async def test_consume_loop_poll_exception(monkeypatch):
    producer = DummyProducer()
    data_collector = DummyDataCollector()
    prediction_service = DummyPredictionService()
    consumer = KafkaConsumer(data_collector, prediction_service, producer=producer)

    class ExplodingConsumer:
        def __init__(self, owner):
            self.owner = owner

        def poll(self, timeout=1.0):
            self.owner.running = False
            raise RuntimeError("boom")

    consumer.consumer = ExplodingConsumer(consumer)
    consumer.running = True

    await consumer._consume_loop()
