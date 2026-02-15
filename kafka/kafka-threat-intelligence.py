# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import argparse
import random
from datetime import datetime, timedelta
import socket
#import pytz
from confluent_kafka import Producer
from fastavro import parse_schema, schemaless_writer
import io
import time
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider

def oauth_cb(oauth_config):
    auth_token, expiry_ms = MSKAuthTokenProvider.generate_auth_token(oauth_config.get('region', 'us-east-1'))
    # Note that this library expects oauth_cb to return expiry time in seconds since epoch, while the token generator returns expiry in ms
    return auth_token, expiry_ms/1000


# Define the Avro schema
threat_schema = {
    "namespace": "security.threat",
    "type": "record",
    "name": "ThreatIntel",
    "fields": [
        {"name": "threat_id", "type": "long"},
        {"name": "ip_address", "type": "string"},
        {"name": "domain_name", "type": "string"},
        {"name": "threat_type", "type": "string"},
        {"name": "confidence_score", "type": "double"},
        #{"name": "confidence_score", "type": {"type": "bytes","logicalType": "decimal", "precision": 3, "scale": 2}},
        {"name": "first_seen_date", "type": {"type": "long","logicalType": "timestamp-millis"}},
        {"name": "last_seen_date", "type": {"type": "long","logicalType": "timestamp-millis"}},
        {"name": "malware_family", "type": "string"},
        {"name": "source", "type": "string"}
    ]
}

parsed_schema = parse_schema(threat_schema)

# Value pools
threat_types = ['Malware, C2', 'Data Exfiltration', 'Brute Force', 
               'Ransomware', 'APT', 'Crypto Mining']
sources = ['Internal', 'External CTI', 'OSINT', 'Partner Feed']
malware_families = ['Emotet', 'TrickBot', 'Ryuk', 'Maze', 'Cobalt Strike', 'BlackMatter']

external_ips = [f"52.1.{i}.{j}" for i in range(1, 4) for j in range(1, 20)]

malicious_domains = [
    f"{random.choice(['evil', 'bad', 'malware', 'ransomware', 'hack'])}"
    f"{random.randint(1,999)}."
    f"{random.choice(['com', 'net', 'org', 'biz', 'info'])}"
    for _ in range(500)
]

def generate_record(batch_id, current_time):
    
    current_time = datetime.now()
    first_seen = current_time - timedelta(days=random.randint(1, 90))
    last_seen = first_seen + timedelta(days=random.randint(0, 30))
    #first_seen = first_seen.strftime("%Y-%m-%dT%H:%M:%SZ")  # ISO8601
    #last_seen = last_seen.strftime("%Y-%m-%dT%H:%M:%SZ")  # ISO8601
    return {
        'threat_id': int(f"{batch_id}{random.randint(1,1000000)}"),
        'ip_address': random.choice(external_ips),
        'domain_name': random.choice(malicious_domains),
        'threat_type': random.choice(threat_types),
        'confidence_score': round(random.uniform(0.5, 1.0), 2),
        'first_seen_date': first_seen,
        'last_seen_date': last_seen,
        'malware_family': random.choice(malware_families),
        'source': random.choice(sources)
        
    }

def delivery_report(err, msg):
    if err is not None:
        print('Delivery failed:', err)
    else:
        print(f"Message delivered to {msg.topic()} partition {msg.partition()} offset {msg.offset()}")

# --------------- Argument Parser and Main Logic -----------
def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Generate simulated events for network and endpoint schemas')
    parser.add_argument('--topic-name', dest='topic', action='store',
                        required=True, help='Kafka topic name')
    parser.add_argument("-c", "--count", type=int, default=10,
                        help="Number of messages to send")
    parser.add_argument('--broker', dest='bserver', action='store',
                        required=True, help='Kafka broker address')
    parser.add_argument('--region', dest='region', action='store',
                        default='us-east-1', help='AWS region (default: us-east-1)')    
    args = parser.parse_args()
    # set global region variable with the region value passed in the argument
    region_g = args.region    
    return args

def main():
    args = parse_arguments()
    producer_config = {
        'bootstrap.servers': args.bserver,
        'batch.size': 262144, # num of bytes
        'linger.ms': 10, # after 10 milisec send the package
        'acks': 1,
        #'client.id': args.clientid,
        'client.id': socket.gethostname(),                        
        'compression.codec': 'snappy',
        'security.protocol': 'SASL_SSL',
        'sasl.mechanisms': 'OAUTHBEARER',
        'oauth_cb': lambda config: oauth_cb({'region': args.region}),
    }
    
    producer = Producer(producer_config)
    topic = args.topic
    num_messages = args.count
    batch_id = 0
    current_time = datetime.now()
    
    for _ in range(num_messages):
        event = generate_record(batch_id, current_time)
        buf = io.BytesIO()
        schemaless_writer(buf, parsed_schema, event)
        value = buf.getvalue()
        # Partitioning by tenant_id
        producer.produce(
            topic,
            value=value,
            callback=delivery_report
        )
        producer.poll(0)
        #time.sleep(0.1)
    producer.flush()

if __name__ == "__main__":
    main()
