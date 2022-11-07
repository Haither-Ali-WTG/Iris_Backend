"""
Script data to specified kafka topic
"""
import argparse
import codecs
import sys
import json
import logging

from ssl import create_default_context
from kafka import KafkaProducer

class KafkaSender:
    """Class to send data to Kafka"""
    def __init__(self, brokers, cert_path):
        """Init Kafka producer"""
        self.brokers = brokers
        self.cert_path = cert_path
        self.producer = None

    def __enter__(self):
        """Runs on creation after init"""
        context = create_default_context(cafile=self.cert_path)
        self.producer = KafkaProducer(bootstrap_servers=self.brokers,
                                        ssl_context=context,
                                        security_protocol="SSL",
                                        value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        return self

    def __exit__(self, exception_type: None, exception_value: None, traceback: None):
        """Runs on exit to clean up"""
        if self.producer:
            self.producer.flush()
            self.producer.close()

    def send_data(self, topic, message):
        """Actual data sending"""
        self.producer.send(topic, message)

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

    with KafkaSender(args.brokers, args.kafka_cert) as kafka_producer:
        with codecs.open(args.message_file, 'r', 'utf-8-sig') as message_file:
            message = json.load(message_file)
            kafka_producer.send_data(args.topic, message)

if __name__ == "__main__":
    sys.exit(main())
