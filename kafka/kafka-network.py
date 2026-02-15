# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import random
from datetime import datetime
import socket
#import pytz
import argparse
from confluent_kafka import Producer
from fastavro import parse_schema, schemaless_writer
import io
import time
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider

def oauth_cb(oauth_config):
    auth_token, expiry_ms = MSKAuthTokenProvider.generate_auth_token(oauth_config.get('region', 'us-east-1'))
    # Note that this library expects oauth_cb to return expiry time in seconds since epoch, while the token generator returns expiry in ms
    return auth_token, expiry_ms/1000

# Your Avro schema
network_schema = {
    "namespace": "network.events",
    "type": "record",
    "name": "NetworkEvent",
    "fields": [
        {"name": "event_id", "type": "long"},
        {"name": "tenant_id", "type": "string"},
        {"name": "timestamp", "type": {"type": "long","logicalType": "timestamp-millis"}},
        {"name": "source_ip", "type": "string"},
        {"name": "destination_ip", "type": "string"},
        {"name": "source_port", "type": "int"},
        {"name": "destination_port", "type": "int"},
        {"name": "protocol", "type": "string"},
        {"name": "bytes_sent", "type": "long"},
        {"name": "bytes_received", "type": "long"},
        {"name": "action", "type": "string"},
        {"name": "threat_level", "type": "string"},
        {"name": "region", "type": "string"}
    ]
}

parsed_schema = parse_schema(network_schema)

# Sample value pools
#tenant_ids = [12345, 12346]  # Example tenant IDs
protocols = ['TCP', 'UDP', 'HTTP', 'HTTPS']
threat_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
actions = ['ALLOWED', 'BLOCKED', 'FLAGGED']
regions = ['NA', 'EU', 'APAC']

internal_ips = [f"192.168.{i}.{j}" for i in range(1, 6) for j in range(1, 20)]
external_ips = [f"52.1.{i}.{j}" for i in range(1, 4) for j in range(1, 20)]

def generate_network_event(tenant_ids):
    tenant_id = random.choice(tenant_ids)
    source_ip = random.choice(internal_ips)
    dest_ip = random.choice(external_ips + internal_ips)
    bytes_sent = random.randint(100, 5000000)
    bytes_received = random.randint(100, 5000000)
    if random.random() < 0.1:
        threat_level = random.choice(["HIGH", "CRITICAL"])
        bytes_sent = random.randint(1000000, 5000000)
    else:
        threat_level = random.choice(threat_levels)
    event = {
        "event_id": random.randint(1, 1000000),
        "tenant_id": tenant_id,
        #"timestamp": datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat(),
        "timestamp": datetime.now(), #.replace(tzinfo=pytz.UTC)
        "source_ip": source_ip,
        "destination_ip": dest_ip,
        "source_port": random.randint(1024, 65535),
        "destination_port": random.choice([80, 443, 53, 22, 3389] + list(range(1024, 65535))),
        "protocol": random.choice(protocols),
        "bytes_sent": bytes_sent,
        "bytes_received": bytes_received,
        "action": random.choice(actions),
        "threat_level": threat_level,
        "region": random.choice(regions)
    }
    return event

def delivery_report(err, msg):
    if err is not None:
        print('Delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}] partition: {}'.format(
            msg.topic(), msg.partition(), msg.partition()))

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Generate simulated NetworkEvents streams')
    parser.add_argument('--topic-name', dest='topic', action='store',
                        default=None, help='Kafka topic name', required=True)
#    parser.add_argument('--client-id', dest='clientid', action='store',
 #                       required=True, help='Kafka client ID')
    parser.add_argument('--tenant-ids', required=True, help='Comma-separated list of tenant IDs')
    parser.add_argument("-c", "--count", type=int, default=10,
                        help="Number of messages to send")
    parser.add_argument('--broker', dest='bserver', action='store',
                        default=None, help='Kafka broker address', required=True)
    parser.add_argument('--region', dest='region', action='store',
                        default='us-east-1', help='AWS region (default: us-east-1)')    
    # Add auth args here if needed
    args = parser.parse_args()
    # set global region variable with the region value passed in the argument
    region_g = args.region        
    # Convert tenant-ids string to list
    args.tenant_ids = args.tenant_ids.split(',')
    return args



def main():
    args = parse_arguments()
    producer_config = {
        'bootstrap.servers': args.bserver,
        'batch.size': 1048576, # num of bytes
        'linger.ms': 10, # after 10 milisec send the package
        'acks': 1,
        #'client.id': args.clientid,
        'client.id': socket.gethostname(),        
        'compression.codec': 'snappy',
        'security.protocol': 'SASL_SSL',
        'sasl.mechanisms': 'OAUTHBEARER',
        'oauth_cb': lambda config: oauth_cb({'region': args.region}),
        # Uncomment & edit next lines if using IAM/OAuth:
        # 'security.protocol': 'SASL_SSL',
        # 'sasl.mechanisms': 'OAUTHBEARER',
        # 'oauth_cb': oauth_cb,
    }

    producer = Producer(producer_config)
    topic = args.topic
    num_messages = args.count

    print('Start of data gen - ', str(datetime.now()))
    for i in range(num_messages):
        event = generate_network_event(args.tenant_ids)
        # Serialize with Avro
        buf = io.BytesIO()
        schemaless_writer(buf, parsed_schema, event)
        value = buf.getvalue()
        # Partitioning by tenant_id
        producer.produce(
            topic,
            value=value,
            key=str(event['tenant_id']),   # this is the key for partitioning
            callback=delivery_report
        )
        producer.poll(0)
        #time.sleep(0.1)
    producer.flush()

if __name__ == "__main__":
    main()
