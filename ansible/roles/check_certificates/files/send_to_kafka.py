"""
Script data to specified kafka topic
"""
import argparse
import codecs
import sys
import json
import logging
from contextlib import contextmanager

from ssl import create_default_context
from kafka import KafkaProducer

@contextmanager
def open_kafka(brokers, cert_path):
    """Open connection to Kafka, flushing and closing on exit"""
    context = create_default_context(cafile=cert_path)
    producer = KafkaProducer(bootstrap_servers=brokers,
                             ssl_context=context,
                             security_protocol="SSL",
                             value_serializer=lambda v: json.dumps(v).encode('utf-8'))
    try:
        yield producer
    finally:
        producer.flush()
        producer.close()

def main():
    """Function sends data to specified topic"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--brokers', '-b', help="Comma separated list of brokers",
                        type=str,
                        default="1.au1-test-1.kafka.wtg.ws:9093,2.au1-test-1.kafka.wtg.ws:9093")
    parser.add_argument('--topic', '-t', help="Kafka topic",
                        type=str, default="topic-au1-test-heartbeat-test")
    parser.add_argument('--kafka_cert', '-kc', help="Kafka certificate",
                        type=str, default="certificate.pem")
    parser.add_argument('--message_file', '-m', help="File with JSON message",
                        type=str, default="message.json")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("Send data to kafka")
    logger.info('Brokers: %s', args.brokers)
    logger.info('Topic: %s', args.topic)
    logger.info('Message file: %s', args.message_file)

    with open_kafka(args.brokers, args.kafka_cert) as kafka_producer:
        with codecs.open(args.message_file, 'r', 'utf-8-sig') as message_file:
            message = json.load(message_file)
            kafka_producer.send(args.topic, message)

if __name__ == "__main__":
    sys.exit(main())
