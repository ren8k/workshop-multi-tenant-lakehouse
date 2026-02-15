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

# ---------------- Avro Schemas ------------------


software_schema = {
    "namespace": "tenant.software",
    "type": "record",
    "name": "InstalledSoftware",
    "fields": [
        {"name": "software_instance_id", "type": "long"},
        {"name": "endpoint_id", "type": "long"},
        {"name": "tenant_id", "type": "string"},
        {"name": "software_name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "install_date", "type": {"type": "long","logicalType": "timestamp-millis"}},  
        {"name": "is_critical", "type": "boolean"}
    ]
}

parsed_schema= parse_schema(software_schema)

# ---------------- Value Pools ------------------
#tenant_ids = [12345, 12346]
regions = ['NA', 'EU', 'APAC']

operating_systems = ['Windows 10', 'Windows 11', 'Ubuntu 20.04', 'RHEL 8', 'macOS 12']
antivirus_status = ['Updated', 'Outdated', 'Disabled', 'Error']
protocols = ["TCP", "UDP", "ICMP", "GRE"]
actions = ["ALLOW", "DENY", "DROP", "ALERT"]
threat_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

statuses = ['SUCCESS', 'FAILED']
failure_reasons = ['Invalid Password', 'Account Locked', 'Invalid Token', 'Expired Certificate', None]
locations = ['London', 'Paris', 'Berlin', 'New York', 'Tokyo', 'Singapore', 'Sydney']
country_codes = ['GB', 'FR', 'DE', 'US', 'JP', 'SG', 'AU']
device_types = ['Desktop', 'Laptop', 'Mobile', 'Tablet']
users = [f"user_{i}" for i in range(1, 51)]

software_list = [
    ('Microsoft Office', ['365', '2019', '2016']),
    ('Adobe Acrobat', ['DC', 'XI', 'X']),
    ('Google Chrome', ['91.0', '90.0', '89.0']),
    ('Mozilla Firefox', ['89.0', '88.0', '87.0']),
    ('Java Runtime', ['8', '11', '16']),
    ('Python', ['3.9', '3.8', '3.7']),
    ('Oracle Database', ['19c', '18c', '12c']),
    ('MySQL', ['8.0', '5.7', '5.6']),
    ('Apache Tomcat', ['9.0', '8.5', '7.0']),
    ('Nginx', ['1.21', '1.20', '1.19'])
]


# --------------- Unified Record Generator -----------------
def generate_record( batch_id, current_time, tenant_ids):
    tenant_id = random.choice(tenant_ids)
    region = random.choice(regions)
    # For demo, randomly pick endpoint_id and tenant_id
    # In real use, pass a list of known endpoints and select from it
    endpoint_id = random.randint(1,1000)
    #tenant_id = random.choice(tenant_ids)
    software, versions = random.choice(software_list)
    version = random.choice(versions)
    install_date = current_time - timedelta(days=random.randint(1, 365))
    #install_date = install_date_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    is_critical = random.random() < 0.2
    return {
        'software_instance_id': random.randint(1,1000000),
        'endpoint_id': endpoint_id,
        'tenant_id': tenant_id,
        'software_name': software,
        'version': version,
        'install_date': install_date,
        'is_critical': is_critical
    }
    

# --------------- Delivery Report Callback -----------------
def delivery_report(err, msg):
    if err is not None:
        print('Delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}] partition: {}'.format(
            msg.topic(), msg.partition(), msg.partition()))

# --------------- Argument Parser and Main Logic -----------
def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Generate simulated events for network and endpoint schemas')
    parser.add_argument('--topic-name', dest='topic', action='store',
                        required=True, help='Kafka topic name')
#    parser.add_argument('--client-id', dest='clientid', action='store',
 #                       required=True, help='Kafka client ID')
    parser.add_argument('--tenant-ids', required=True, help='Comma-separated list of tenant IDs')    
    parser.add_argument("-c", "--count", type=int, default=10,
                        help="Number of messages to send")
    parser.add_argument('--broker', dest='bserver', action='store',
                        required=True, help='Kafka broker address')
    parser.add_argument('--region', dest='region', action='store',
                        default='us-east-1', help='AWS region (default: us-east-1)')    
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
        event = generate_record(batch_id, current_time, args.tenant_ids)
        buf = io.BytesIO()
        schemaless_writer(buf, parsed_schema, event)
        value = buf.getvalue()
        # Partitioning by tenant_id
        producer.produce(
            topic,
            value=value,
            key=str(event["tenant_id"]),
            callback=delivery_report
        )
        producer.poll(0)
        #time.sleep(0.1)
    producer.flush()

if __name__ == "__main__":
    main()
