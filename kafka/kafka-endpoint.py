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


endpoint_schema = {
    "namespace": "tenant.endpoint",
    "type": "record",
    "name": "Endpoint",
    "fields": [
        {"name": "endpoint_id", "type": "long"},
        {"name": "tenant_id", "type": "string"},
        {"name": "hostname", "type": "string"},
        {"name": "ip_address", "type": "string"},
        {"name": "operating_system", "type": "string"},
        {"name": "os_version", "type": "string"},
        {"name": "last_patch_date", "type": {"type": "long","logicalType": "timestamp-millis"}},
        {"name": "antivirus_status", "type": "string"},
        {"name": "risk_score", "type": "double"},
        {"name": "department", "type": "string"},
        {"name": "region", "type": "string"},
        {"name": "country_code", "type": "string"}
    ]
}


parsed_schema= parse_schema(endpoint_schema)

# ---------------- Value Pools ------------------
#tenant_ids = [12345, 12346]
#firstRun = False
regions = ['NA', 'EU', 'APAC']
departments = ['IT', 'Finance', 'HR', 'Sales', 'Marketing', 'R&D']
operating_systems = ['Windows 10', 'Windows 11', 'Ubuntu 20.04', 'RHEL 8', 'macOS 12']
antivirus_status = ['Updated', 'Outdated', 'Disabled', 'Error']


# --------------- Unified Record Generator -----------------
def generate_record(batch_id, current_time, tenant_ids, firstRun):
    tenant_id = random.choice(tenant_ids)
    region = random.choice(regions)
    dept = random.choice(departments)
    # Set the endpoint ID to a number within 1000 if the python script is executed for the first time
    if firstRun:
        ep_id = random.randint(1,1000)
    else:
        ep_id = random.randint(1,1000000)
    
    hostname = f"{region}-{dept}-{random.randint(0,999):03d}"
    ip_last_octets = random.randint(1, 20)
    ip_address = f"192.168.{departments.index(dept)+1}.{ip_last_octets}"
    last_patch_date_dt = current_time - timedelta(days=random.randint(0, 90))
    last_patch_date = last_patch_date_dt    
    #last_patch_date = last_patch_date_dt.isoformat()    
    #last_patch_date_dt = current_time - timedelta(days=random.randint(0, 90))
    #last_patch_date = last_patch_date_dt.strftime("%Y-%m-%dT%H:%M:%SZ")  # ISO8601
    days_since_patch = (current_time - last_patch_date_dt).days
    base_risk = min(days_since_patch / 30, 5)
    risk_score = round(min(base_risk + random.uniform(0, 7), 10), 2)
    return {
        'endpoint_id': ep_id,
        'tenant_id': tenant_id,
        'hostname': hostname,
        'ip_address': ip_address,
        'operating_system': random.choice(operating_systems),
        'os_version': f"{random.randint(1,3)}.{random.randint(0,9)}",
        'last_patch_date': last_patch_date,
        'antivirus_status': random.choice(antivirus_status),
        'risk_score': risk_score,
        'department': dept,
        'region': region,
        'country_code': ''
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
    parser.add_argument("--first-run", type=bool, default=False,
                        help="Set the value to true to generate endpoint IDs within 1000")    
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

    print('Start of data gen - ', str(datetime.now()))
    for _ in range(num_messages):
        event = generate_record(batch_id, current_time, args.tenant_ids, args.first_run)
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
