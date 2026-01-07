"""
Unit tests for KafkaProducer.
"""
import json

import pytest

from src.kafka.producer import KafkaProducer
from src.config.settings import settings


class DummyMsg:
    def __init__(self, topic):
        self._topic = topic

    def topic(self):
        return self._topic


class DummyProducer:
    def __init__(self, config):
        self.config = config
        self.produced = []
        self.polled = []
        self.flushed = False

    def produce(self, topic, value, callback=None):
        self.produced.append((topic, value))
        if callback:
            callback(None, DummyMsg(topic))

    def poll(self, timeout):
        self.polled.append(timeout)

    def flush(self):
        self.flushed = True


class DummyLogger:
    def __init__(self):
        self.errors = []
        self.debugs = []

    def error(self, msg):
        self.errors.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)


@pytest.mark.asyncio
async def test_start_initializes_producer(monkeypatch):
    monkeypatch.setattr("src.kafka.producer.Producer", DummyProducer)
    monkeypatch.setattr(settings, "kafka_brokers", "localhost:9092")
    monkeypatch.setattr(settings, "kafka_client_id", "test-client")

    producer = KafkaProducer()
    await producer.start()

    assert isinstance(producer.producer, DummyProducer)
    assert producer.producer.config["bootstrap.servers"] == "localhost:9092"
    assert producer.producer.config["client.id"] == "test-client"


@pytest.mark.asyncio
async def test_publish_no_producer_does_nothing():
    producer = KafkaProducer()
    await producer.publish("topic", {"value": 1})

    assert producer.producer is None


@pytest.mark.asyncio
async def test_publish_sends_message(monkeypatch):
    monkeypatch.setattr("src.kafka.producer.Producer", DummyProducer)
    producer = KafkaProducer()
    await producer.start()

    payload = {"charger_id": "c1", "score": 0.5}
    await producer.publish("topic-a", payload)

    assert len(producer.producer.produced) == 1
    topic, value = producer.producer.produced[0]
    assert topic == "topic-a"
    assert value == json.dumps(payload, default=str).encode("utf-8")
    assert producer.producer.polled == [0]


@pytest.mark.asyncio
async def test_flush_and_stop(monkeypatch):
    monkeypatch.setattr("src.kafka.producer.Producer", DummyProducer)
    producer = KafkaProducer()
    await producer.start()

    await producer.flush()
    assert producer.producer.flushed is True

    producer.producer.flushed = False
    await producer.stop()
    assert producer.producer.flushed is True


def test_delivery_callback_logs_error(monkeypatch):
    dummy_logger = DummyLogger()
    monkeypatch.setattr("src.kafka.producer.logger", dummy_logger)

    producer = KafkaProducer()
    producer._delivery_callback(err="boom", msg=None)

    assert len(dummy_logger.errors) == 1
    assert "Message delivery failed" in dummy_logger.errors[0]


def test_delivery_callback_logs_success(monkeypatch):
    dummy_logger = DummyLogger()
    monkeypatch.setattr("src.kafka.producer.logger", dummy_logger)

    producer = KafkaProducer()
    producer._delivery_callback(err=None, msg=DummyMsg("topic-ok"))

    assert len(dummy_logger.debugs) == 1
    assert "Message delivered" in dummy_logger.debugs[0]
