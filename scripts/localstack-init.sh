#!/bin/bash

# LocalStack initialization script for urepricer development
echo "Initializing LocalStack for urepricer development..."

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
until curl -f http://localhost:4566/_localstack/health > /dev/null 2>&1; do
    echo "Waiting for LocalStack..."
    sleep 2
done

echo "LocalStack is ready, creating AWS resources..."

# Create SQS queues
echo "Creating SQS queues..."

# Amazon Any Offer Changed queue
awslocal sqs create-queue \
    --queue-name amazon-any-offer-changed-queue \
    --attributes VisibilityTimeoutSeconds=60,MessageRetentionPeriod=1209600

# Feed Processing queue  
awslocal sqs create-queue \
    --queue-name feed-processing-queue \
    --attributes VisibilityTimeoutSeconds=60,MessageRetentionPeriod=1209600

# Processed Data queue
awslocal sqs create-queue \
    --queue-name processed-data-queue \
    --attributes VisibilityTimeoutSeconds=60,MessageRetentionPeriod=1209600

# List created queues
echo "Created SQS queues:"
awslocal sqs list-queues

# Create S3 buckets if needed
echo "Creating S3 buckets..."
awslocal s3 mb s3://urepricer-feeds-dev
awslocal s3 mb s3://urepricer-exports-dev

echo "LocalStack initialization completed!"
echo "Available resources:"
echo "- SQS Queues: amazon-any-offer-changed-queue, feed-processing-queue, processed-data-queue"
echo "- S3 Buckets: urepricer-feeds-dev, urepricer-exports-dev"