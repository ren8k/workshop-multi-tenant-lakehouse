# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import sys
import argparse
from pyspark.sql.types import *
from pyspark.sql.functions import *
from pyspark.sql import SparkSession
from pyspark.sql.avro.functions import from_avro, to_avro

def parse_arguments():
    parser = argparse.ArgumentParser(description='Spark Streaming Job Arguments')
    
    # Add arguments
    parser.add_argument('--catalog', required=True, help='Iceberg catalog name')
    parser.add_argument('--database', required=True, help='Iceberg database name')
    parser.add_argument('--table', required=True, help='Table name')
    parser.add_argument('--bootstrap-servers', required=True, help='Kafka bootstrap servers')
    parser.add_argument('--topic', required=True, help='Kafka topic')
    parser.add_argument('--checkpoint-location', required=True, help='Checkpoint location')
    parser.add_argument('--warehouse-location', required=True, help='Warehouse location')
    parser.add_argument('--tenant-ids', required=True, help='Comma-separated list of tenant IDs')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Convert tenant-ids string to list
    args.tenant_ids = args.tenant_ids.split(',')
    
    return args

def create_spark_session(args):
    return SparkSession \
        .builder \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config(f"spark.sql.catalog.{args.catalog}", "org.apache.iceberg.spark.SparkCatalog") \
        .config(f"spark.sql.catalog.{args.catalog}.catalog-impl", "software.amazon.s3tables.iceberg.S3TablesCatalog") \
        .config(f"spark.sql.catalog.{args.catalog}.warehouse", args.warehouse_location) \
        .appName("emr-msk-consumer") \
        .getOrCreate()

def create_kafka_stream(spark, args):
    schema_inline = '''{
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
    }'''

    return spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", args.bootstrap_servers) \
        .option("kafka.security.protocol", "SASL_SSL") \
        .option("kafka.sasl.mechanism", "AWS_MSK_IAM") \
        .option("kafka.sasl.jaas.config", "software.amazon.msk.auth.iam.IAMLoginModule required;") \
        .option("kafka.sasl.client.callback.handler.class", "software.amazon.msk.auth.iam.IAMClientCallbackHandler") \
        .option("subscribe", args.topic) \
        .option("startingOffsets", "earliest") \
        .option("maxOffsetsPerTrigger", 5000000) \
        .load() \
        .select(from_avro("value", schema_inline).alias("data")) \
        .select("data.*")

def process_micro_batch(batch_df, batch_id, args):
    if batch_df.isEmpty():
        return
        
    for tenant_id in args.tenant_ids:
        tenant_df = batch_df.filter(col("tenant_id") == tenant_id)
        
        if not tenant_df.isEmpty():
            tenant_df.write \
                .format("iceberg") \
                .mode("append") \
                .saveAsTable(f"""`{args.catalog}`.{args.database}.{args.table}""")

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Create Spark session
    spark = create_spark_session(args)
    
    # Create Kafka stream
    df = create_kafka_stream(spark, args)
    
    # Create streaming query
    data = df.writeStream \
        .foreachBatch(lambda df, id: process_micro_batch(df, id, args)) \
        .trigger(processingTime='60 seconds') \
        .option("checkpointLocation", args.checkpoint_location) \
        .start()
    
    # Wait for termination
    data.awaitTermination()

if __name__ == "__main__":
    main()