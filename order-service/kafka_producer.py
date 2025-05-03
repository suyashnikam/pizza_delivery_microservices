from confluent_kafka import Producer
import json
import os

# Kafka configuration
kafka_config = {
    'bootstrap.servers': os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
}

# Create Kafka producer instance
producer = Producer(kafka_config)

# Optional: Delivery report callback
def delivery_report(err, msg):
    if err is not None:
        print(f"❌ Delivery failed for Order UID {msg.key().decode()}: {err}")
    else:
        print(f"📬 Message delivered to {msg.topic()} [{msg.partition()}]")

# Produce delivery event
def delivery_event_producer(order_data: dict):
    try:
        producer.produce(
            topic="new_order_topic",
            key=str(order_data["order_uid"]),
            value=json.dumps(order_data),
            callback=delivery_report
        )
        producer.poll(0)  # Trigger delivery report callbacks
        producer.flush()
        print(f"✅ Kafka: Order event published: {order_data['order_uid']}")
    except Exception as e:
        print(f"❌ Kafka error: {e}")
