#!/bin/bash

# LocalStack SQS Setup Script
# This script runs when LocalStack starts to configure SQS queues for testing

set -e

echo "Setting up SQS queues for end-to-end testing..."

# Set AWS endpoint to LocalStack
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# Create the main ANY_OFFER_CHANGED queue
echo "Creating ANY_OFFER_CHANGED queue..."
QUEUE_URL=$(awslocal sqs create-queue \
    --queue-name ah-repricer-any-offer-changed \
    --attributes '{
        "MessageRetentionPeriod": "1209600",
        "VisibilityTimeoutSeconds": "300",
        "ReceiveMessageWaitTimeSeconds": "20"
    }' \
    --query 'QueueUrl' --output text)

echo "ANY_OFFER_CHANGED queue created: $QUEUE_URL"

# Create Dead Letter Queue
echo "Creating Dead Letter Queue..."
DLQ_URL=$(awslocal sqs create-queue \
    --queue-name ah-repricer-dlq \
    --attributes '{
        "MessageRetentionPeriod": "1209600"
    }' \
    --query 'QueueUrl' --output text)

echo "Dead Letter Queue created: $DLQ_URL"

# Get queue ARNs for redrive policy
QUEUE_ARN=$(awslocal sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' --output text)

DLQ_ARN=$(awslocal sqs get-queue-attributes \
    --queue-url $DLQ_URL \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' --output text)

# Configure redrive policy on main queue
echo "Configuring redrive policy..."
awslocal sqs set-queue-attributes \
    --queue-url $QUEUE_URL \
    --attributes '{
        "RedrivePolicy": "{\"deadLetterTargetArn\":\"'$DLQ_ARN'\",\"maxReceiveCount\":3}"
    }'

# Create SNS topic for ANY_OFFER_CHANGED notifications
echo "Creating SNS topic for notifications..."
TOPIC_ARN=$(awslocal sns create-topic \
    --name ah-repricer-any-offer-changed-topic \
    --query 'TopicArn' --output text)

echo "SNS Topic created: $TOPIC_ARN"

# Subscribe the SQS queue to the SNS topic
echo "Subscribing SQS queue to SNS topic..."
awslocal sns subscribe \
    --topic-arn $TOPIC_ARN \
    --protocol sqs \
    --notification-endpoint $QUEUE_ARN

# Allow SNS to write to SQS queue
echo "Setting up SQS queue policy for SNS..."
awslocal sqs set-queue-attributes \
    --queue-url $QUEUE_URL \
    --attributes '{
        "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sns.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"'$QUEUE_ARN'\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"'$TOPIC_ARN'\"}}}]}"
    }'

echo "SQS setup completed successfully!"
echo "Queue URL: $QUEUE_URL"
echo "DLQ URL: $DLQ_URL"  
echo "Topic ARN: $TOPIC_ARN"

# Export these for test usage
echo "export TEST_SQS_QUEUE_URL=\"$QUEUE_URL\"" > /tmp/localstack_config.sh
echo "export TEST_SQS_DLQ_URL=\"$DLQ_URL\"" >> /tmp/localstack_config.sh
echo "export TEST_SNS_TOPIC_ARN=\"$TOPIC_ARN\"" >> /tmp/localstack_config.sh
echo "export TEST_SQS_QUEUE_ARN=\"$QUEUE_ARN\"" >> /tmp/localstack_config.sh

echo "Configuration saved to /tmp/localstack_config.sh"