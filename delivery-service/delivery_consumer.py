# delivery_consumer.py

import json
import threading
from confluent_kafka import Consumer
from sqlalchemy.orm import Session
from datetime import datetime
import models, database
import os
from dotenv import load_dotenv
load_dotenv()


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
DELIVERY_TOPIC = "new_order_topic"
GROUP_ID = "delivery-service-group"

def start_delivery_consumer():
    def consume():
        consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': GROUP_ID,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True
        })

        consumer.subscribe([DELIVERY_TOPIC])
        print(f"✅ Kafka Consumer started, listening to topic: {DELIVERY_TOPIC}")

        try:
            while True:
                msg = consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    print(f"❌ Kafka error: {msg.error()}")
                    continue

                try:
                    data = json.loads(msg.value().decode("utf-8"))
                    print(f"📦 New order received in delivery-service: {data}")

                    db: Session = next(database.get_db())
                    new_delivery = models.Delivery(
                        order_uid=data["order_uid"],
                        status="PENDING",  # default status
                        # assigned_at, updated_at are handled by the model defaults
                    )
                    db.add(new_delivery)
                    db.commit()
                    db.close()
                    print(f"✅ Delivery entry created for Order UID: {data['order_uid']}")

                except Exception as e:
                    print(f"🔥 Error processing message: {e}")

        except KeyboardInterrupt:
            print("🛑 Consumer interrupted manually.")
        finally:
            consumer.close()
            print("🔒 Kafka Consumer closed gracefully.")

    threading.Thread(target=consume, daemon=True).start()
