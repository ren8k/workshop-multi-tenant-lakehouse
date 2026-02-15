# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import argparse
import random
from datetime import datetime, timedelta
#import pytz
import socket
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


auth_schema = {
    "namespace": "tenant.auth",
    "type": "record",
    "name": "AuthenticationEvent",
    "fields": [
        {"name": "auth_id", "type": "long"},
        {"name": "tenant_id", "type": "string"},
        {"name": "timestamp", "type": {"type": "long","logicalType": "timestamp-millis"}},  
        {"name": "user_id", "type": "string"},
        {"name": "source_ip", "type": "string"},
        {"name": "authentication_type", "type": "string"},
        {"name": "status", "type": "string"},
        {"name": "failure_reason", "type": ["string", "null"]},
        {"name": "location", "type": "string"},
        {"name": "country_code", "type": "string"},
        {"name": "device_type", "type": "string"}
    ]
}

parsed_schema= parse_schema(auth_schema)

# ---------------- Value Pools ------------------
#tenant_ids = [12345, 12346]

auth_types = ['password', '2FA', 'SSO', 'certificate', 'biometric']
statuses = ['SUCCESS', 'FAILED']
failure_reasons = ['Invalid Password', 'Account Locked', 'Invalid Token', 'Expired Certificate']
locations = ['London', 'Paris', 'Berlin', 'New York', 'Tokyo', 'Singapore', 'Sydney']
country_codes = ['GB', 'FR', 'DE', 'US', 'JP', 'SG', 'AU']
device_types = ['Desktop', 'Laptop', 'Mobile', 'Tablet']
users = [f"user_{i}" for i in range(1, 51)]
#regions = ['NA', 'EU', 'APAC']

# --------------- Unified Record Generator -----------------
def generate_record(batch_id, current_time, tenant_ids):
    try:
        tenant_id = random.choice(tenant_ids)
        #region = random.choice(regions)
        user_id = random.choice(users)
        is_suspicious = random.random() < 0.1
        if is_suspicious:
            status = 'FAILED'
            auth_count = random.randint(5, 20)
        else:
            status = random.choice(statuses)
            auth_count = 1

        location_idx = random.randint(0, len(locations) - 1)
        if status == 'FAILED':
            failure_reason = random.choice(failure_reasons)
        else:
            failure_reason = None  # Use None for successful authentications
        
        return {
            'auth_id': int(f"{batch_id}{random.randint(1,1000000)}"),
            'tenant_id': tenant_id,
            'timestamp': (current_time - timedelta(
                hours=random.randint(0, 24),
                minutes=random.randint(0, 60)
            )),#.isoformat(),
            'user_id': user_id,
            'source_ip': f"192.168.{random.randint(1,6)}.{random.randint(1,20)}",
            'authentication_type': random.choice(auth_types),
            'status': status,
            'failure_reason': failure_reason,
            'location': locations[location_idx],
            'country_code': country_codes[location_idx],
            'device_type': random.choice(device_types)
        }
    except Exception as e:
        print(f"Error in generate_record: {str(e)}")
        return None
    

# --------------- Delivery Report Callback -----------------
def delivery_report(err, msg):
    if err is not None:
        print('Delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}] partition: {}'.format(
            msg.topic(), msg.value(), msg.partition()))

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
       # 'client.id': args.clientid,
        'client.id': socket.gethostname(),
        'compression.codec': 'snappy',
        'security.protocol': 'SASL_SSL',
        'sasl.mechanisms': 'OAUTHBEARER',
        #'oauth_cb': oauth_cb,
        'oauth_cb': lambda config: oauth_cb({'region': args.region}),
    }
    
    producer = Producer(producer_config)
    topic = args.topic
    num_messages = args.count
    batch_id = random.randint(10, 99)
    current_time = datetime.now()

   # print('Start of data gen - ', str(datetime.now()))
    for i in range(num_messages):
        event = generate_record(batch_id, current_time, args.tenant_ids)
        if event is None:
            #print(f"Skipping invalid event for batch {batch_id}")
            continue
        
        try:
            #print(f"Generated event for batch {batch_id}: {event}")
            buf = io.BytesIO()
            schemaless_writer(buf, parsed_schema, event)
            value = buf.getvalue()
            producer.produce(
                topic,
                value=value,
                callback=delivery_report
            )
            producer.poll(0)
            #time.sleep(0.1)
        except Exception as e:
            print(f"Error generating/sending message for batch {batch_id}: {str(e)}")
            print(f"Problematic event: {event}")
        
        #batch_id += 1  # Increment batch_id
        
    producer.flush()

if __name__ == "__main__":
    main()
