# System Architecture and Data Flow

This document provides a comprehensive overview of the high-throughput repricing system architecture.

## System Overview

The system processes thousands of repricing messages per minute from Amazon SQS and Walmart webhooks through a 4-step pipeline:

1. **Extract message fields** from SQS/webhook notifications
2. **Read product data** from Redis using Redis OM models  
3. **Make repricing decisions** based on business logic with price validation
4. **Apply strategies** and save calculated prices to Redis with seller-first key naming

### Key Architectural Changes (2025 Update)

- **Redis OM Integration**: Migrated from SQLAlchemy to Redis OM (Object Mapper) for all data models
- **Pydantic Price Validation**: Comprehensive model-level validation ensures `min_price <= max_price` 
- **End-to-End Testing**: LocalStack and containerized testing infrastructure for complete workflow validation
- **FastAPI Webhook Endpoints**: High-performance async endpoints for Walmart integration
- **Seller-First Key Naming**: Redis keys organized by seller for efficient data access patterns

```mermaid
graph TB
    %% External Sources
    Amazon[Amazon ANY_OFFER_CHANGED SQS] --> SQSConsumer[SQS Consumer Service]
    Walmart[Walmart Buy Box Webhooks] --> FastAPI[FastAPI Webhook Endpoints]
    
    %% Core Processing Pipeline
    SQSConsumer --> Orchestrator[Repricing Orchestrator]
    FastAPI --> Orchestrator
    
    Orchestrator --> MessageProcessor[Message Processor]
    MessageProcessor --> RedisService[Redis Service]
    RedisService --> RepricingEngine[Repricing Engine]
    
    %% Data Storage
    Redis[(Redis Cache<br/>2-hour TTL)] <--> RedisService
    
    %% Strategy Processing
    RepricingEngine --> Strategies{Pricing Strategies}
    Strategies --> ChaseBuyBox[Chase BuyBox]
    Strategies --> MaximizeProfit[Maximize Profit] 
    Strategies --> OnlySeller[Only Seller]
    
    %% Error Handling
    Orchestrator --> ErrorHandler[Error Handler]
    ErrorHandler --> DLQ[Dead Letter Queue]
    ErrorHandler --> Alerts[Alert System]
    
    %% Output
    RepricingEngine --> RedisService
    RedisService --> Results[Calculated Prices<br/>Saved to Redis]
    
    %% Styling
    classDef external fill:#e1f5fe
    classDef service fill:#f3e5f5
    classDef storage fill:#e8f5e8
    classDef strategy fill:#fff3e0
    classDef error fill:#ffebee
    
    class Amazon,Walmart external
    class SQSConsumer,FastAPI,Orchestrator,MessageProcessor,RedisService,RepricingEngine service
    class Redis,Results storage
    class ChaseBuyBox,MaximizeProfit,OnlySeller strategy
    class ErrorHandler,DLQ,Alerts error
```

## High-Level Architecture Components

### 1. Message Ingestion Layer
- **SQS Consumer**: Polls Amazon SQS queues for ANY_OFFER_CHANGED notifications with high concurrency
- **FastAPI Webhooks**: Async HTTP endpoints for Walmart buy box change notifications  
- **Message Processor**: Normalizes and validates incoming messages from both platforms

### 2. Data Model Layer (Redis OM)
- **ProductListing**: Redis OM JsonModel for product data with comprehensive price validation
- **B2BTier**: EmbeddedJsonModel for B2B tier pricing with nested validation
- **Price Validation**: Pydantic validators ensure data integrity at model level
- **Seller-First Keys**: Redis keys structured as `listing:{seller_id}:{asin}` for efficient access

### 3. Core Processing Engine
- **Repricing Orchestrator**: Coordinates the entire 4-step pipeline with high concurrency
- **Redis Service**: Handles all data access with connection pooling and TTL management
- **Repricing Engine**: Makes business decisions and applies pricing strategies with bounds checking

### 4. Strategy Layer  
- **Chase BuyBox**: Competes to win the buy box by beating competitor prices
- **Maximize Profit**: Optimizes for profit when already winning buy box
- **Only Seller**: Handles scenarios with no competition, uses mean pricing when needed
- **Price Bounds Validation**: All strategies validate calculated prices against min/max bounds

### 5. Error Handling & Reliability
- **Error Handler**: Comprehensive error classification and handling
- **Dead Letter Queue**: Stores failed messages for manual review
- **Circuit Breaker**: Protects against cascading failures
- **PriceBoundsError**: Custom exceptions for price validation failures

### 6. Testing Infrastructure
- **LocalStack Integration**: SQS and SNS emulation for end-to-end testing
- **Redis Test Instance**: Isolated Redis instance on port 6380 for testing
- **FastAPI TestClient**: Direct endpoint testing with background task verification
- **E2E Test Suite**: Complete workflow tests from webhook/SQS → Redis price updates

## Detailed Data Flow

### Amazon SQS Processing Flow

```mermaid
sequenceDiagram
    participant SQS as Amazon SQS
    participant Consumer as SQS Consumer
    participant Orchestrator as Repricing Orchestrator
    participant Processor as Message Processor
    participant Redis as Redis Service
    participant Engine as Repricing Engine
    participant Strategy as Pricing Strategy
    
    SQS->>Consumer: Poll for messages (batch of 10)
    Consumer->>Consumer: Receive ANY_OFFER_CHANGED notifications
    
    loop For each message
        Consumer->>Orchestrator: Process Amazon message
        Orchestrator->>Processor: Extract & validate message fields
        Processor-->>Orchestrator: ProcessedOfferData
        
        Orchestrator->>Engine: Make repricing decision
        Engine->>Redis: Get product data (ASIN + Seller + SKU)
        Redis-->>Engine: Product data + Strategy config
        Engine->>Engine: Check stock, status, eligibility
        Engine-->>Orchestrator: RepricingDecision
        
        alt Should reprice = true
            Orchestrator->>Engine: Calculate new price
            Engine->>Strategy: Apply pricing strategy
            Strategy->>Strategy: Calculate competitive price
            Strategy-->>Engine: Updated price
            Engine-->>Orchestrator: CalculatedPrice
            
            alt Price changed
                Orchestrator->>Redis: Save new price with 2h TTL
                Redis-->>Orchestrator: Success
            end
        end
        
        Consumer->>SQS: Delete processed message
    end
```

### Walmart Webhook Processing Flow

```mermaid
sequenceDiagram
    participant Walmart as Walmart API
    participant FastAPI as FastAPI Endpoints
    participant Orchestrator as Repricing Orchestrator
    participant Processor as Message Processor
    participant Redis as Redis Service
    participant Engine as Repricing Engine
    
    Walmart->>FastAPI: POST /walmart/webhook (buy box change)
    FastAPI->>FastAPI: Validate webhook payload
    FastAPI-->>Walmart: 200 OK (immediate response)
    
    FastAPI->>Orchestrator: Process webhook (background task)
    Orchestrator->>Processor: Extract & normalize webhook data
    Processor-->>Orchestrator: ProcessedOfferData
    
    Orchestrator->>Engine: Make repricing decision
    Engine->>Redis: Get product by item_id mapping
    Redis-->>Engine: Product data + Strategy
    
    alt Product found & eligible
        Engine->>Engine: Apply Walmart-specific logic
        Orchestrator->>Redis: Save calculated price
    end
```

## Redis Data Architecture

### Data Organization Strategy
```mermaid
graph LR
    subgraph "Redis Cluster"
        subgraph "Product Data"
            ASIN1["ASIN_B07XQXZXYX<br/>├─ SELLER1:SKU1<br/>├─ SELLER1:SKU2<br/>└─ SELLER2:SKU3"]
            ASIN2["ASIN_B08XXXXXXX<br/>├─ SELLER3:SKU4<br/>└─ SELLER4:SKU5"]
        end
        
        subgraph "Strategy Config"
            Strategy1["strategy.1<br/>├─ compete_with<br/>├─ beat_by<br/>└─ min_price_rule"]
            Strategy2["strategy.2<br/>├─ compete_with<br/>├─ beat_by<br/>└─ inventory_age_rules"]
        end
        
        subgraph "Calculated Prices"
            Prices1["CALCULATED_PRICES:SELLER1<br/>├─ SKU1 → price_data<br/>└─ SKU2 → price_data"]
            Prices2["CALCULATED_PRICES:SELLER2<br/>└─ SKU3 → price_data"]
        end
    end
    
    ASIN1 --> TTL1[2h TTL]
    ASIN2 --> TTL2[2h TTL] 
    Strategy1 --> TTL3[2h TTL]
    Strategy2 --> TTL4[2h TTL]
    Prices1 --> TTL5[2h TTL]
    Prices2 --> TTL6[2h TTL]
```

### Connection Pooling & Performance
- **Connection Pool Size**: 20 connections maximum
- **Pipeline Operations**: Batch Redis commands for efficiency
- **Async Operations**: All Redis calls are non-blocking
- **Retry Logic**: Built-in connection retry with exponential backoff

## Concurrency and Throughput Design

### High-Throughput Processing Model
```mermaid
graph TB
    subgraph "SQS Consumer Cluster"
        SQS1[SQS Consumer 1<br/>Concurrency: 50]
        SQS2[SQS Consumer 2<br/>Concurrency: 50] 
        SQS3[SQS Consumer N<br/>Concurrency: 50]
    end
    
    subgraph "FastAPI Cluster"
        API1[FastAPI Instance 1<br/>Workers: 4]
        API2[FastAPI Instance 2<br/>Workers: 4]
        API3[FastAPI Instance N<br/>Workers: 4]
    end
    
    subgraph "Processing Layer"
        Orchestrator[Repricing Orchestrator<br/>Max Concurrent: 100<br/>Batch Size: 50]
    end
    
    SQS1 --> Orchestrator
    SQS2 --> Orchestrator
    SQS3 --> Orchestrator
    
    API1 --> Orchestrator
    API2 --> Orchestrator
    API3 --> Orchestrator
    
    Orchestrator --> Redis[(Redis Cluster<br/>20 Connections)]
```

### Performance Characteristics
- **Target Throughput**: 1,000+ messages per minute
- **Average Processing Time**: ~125ms per message
- **Concurrent Message Processing**: Up to 100 messages simultaneously
- **Batch Processing**: Groups messages for efficiency
- **Memory Usage**: Optimized for minimal memory footprint

## Error Handling and Reliability

### Error Classification System
```mermaid
graph TB
    Error[Incoming Error] --> Classifier{Error Classifier}
    
    Classifier --> Validation[Validation Error<br/>Severity: Medium]
    Classifier --> Network[Network Error<br/>Severity: Medium] 
    Classifier --> Service[External Service Error<br/>Severity: High]
    Classifier --> System[System Error<br/>Severity: Critical]
    
    Validation --> Retry1{Retryable?}
    Network --> Retry2{Retryable?}
    Service --> Retry3{Retryable?}
    System --> Alert[Send Alert]
    
    Retry1 --> |No| DLQ1[Send to DLQ]
    Retry2 --> |Yes| Retry[Retry with backoff]
    Retry2 --> |No| DLQ2[Send to DLQ]
    Retry3 --> |Yes| Retry
    Retry3 --> |No| DLQ3[Send to DLQ]
    
    Alert --> DLQ4[Send to DLQ]
    
    Retry --> Success{Success?}
    Success --> |Yes| Complete[Complete]
    Success --> |No| DLQ5[Send to DLQ]
```

### Circuit Breaker Pattern
```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Open : Failure threshold reached
    Open --> HalfOpen : Recovery timeout
    HalfOpen --> Closed : Success
    HalfOpen --> Open : Failure
    
    note right of Closed : Normal operation
    note right of Open : All calls fail fast
    note right of HalfOpen : Limited test calls
```

## Strategy Processing Architecture

### Strategy Selection Logic
```mermaid
graph TD
    Product[Product Data] --> Check{Check Market Conditions}
    
    Check --> |No offers <= 1| OnlySeller[Only Seller Strategy]
    Check --> |Is buybox winner| MaxProfit[Maximize Profit Strategy]
    Check --> |Has competition| ChaseBuyBox[Chase BuyBox Strategy]
    
    OnlySeller --> Apply1[Apply Strategy Logic]
    MaxProfit --> Apply2[Apply Strategy Logic]  
    ChaseBuyBox --> Apply3[Apply Strategy Logic]
    
    Apply1 --> PriceProcessor[New Price Processor]
    Apply2 --> PriceProcessor
    Apply3 --> PriceProcessor
    
    PriceProcessor --> Validate{Validate Price}
    Validate --> |Within bounds| Success[Updated Price]
    Validate --> |Out of bounds| Rule[Apply Min/Max Rule]
    
    Rule --> Success
```

### B2B Tier Processing
```mermaid
graph LR
    Product[B2B Product] --> Tiers{Has Tiers?}
    
    Tiers --> |Yes| ProcessTiers[Process Each Tier]
    Tiers --> |No| StandardB2B[Standard B2B Pricing]
    
    ProcessTiers --> Tier1[Tier 1: Qty 5<br/>Price: $24.99]
    ProcessTiers --> Tier2[Tier 2: Qty 10<br/>Price: $22.99] 
    ProcessTiers --> Tier3[Tier 3: Qty 25<br/>Price: $20.99]
    ProcessTiers --> Tier4[Tier 4: Qty 50<br/>Price: $18.99]
    ProcessTiers --> Tier5[Tier 5: Qty 100<br/>Price: $16.99]
    
    Tier1 --> SaveTiers[Save All Tier Prices]
    Tier2 --> SaveTiers
    Tier3 --> SaveTiers
    Tier4 --> SaveTiers
    Tier5 --> SaveTiers
    
    StandardB2B --> SaveStandard[Save B2B Price]
    SaveTiers --> Redis[(Redis)]
    SaveStandard --> Redis
```

## Monitoring and Health Checks

### System Health Monitoring
```mermaid
graph TB
    Monitor[Health Check System] --> Services{Check All Services}
    
    Services --> Redis[Redis Health]
    Services --> SQS[SQS Consumer Health]
    Services --> API[FastAPI Health]
    Services --> Orchestrator[Orchestrator Health]
    
    Redis --> |Healthy| Status1[✓ Redis OK]
    Redis --> |Unhealthy| Status2[✗ Redis Failed]
    
    SQS --> |Healthy| Status3[✓ SQS Consumer OK]
    SQS --> |Unhealthy| Status4[✗ SQS Consumer Failed]
    
    API --> |Healthy| Status5[✓ FastAPI OK]  
    API --> |Unhealthy| Status6[✗ FastAPI Failed]
    
    Orchestrator --> |Healthy| Status7[✓ Orchestrator OK]
    Orchestrator --> |Unhealthy| Status8[✗ Orchestrator Failed]
    
    Status1 --> Overall{Overall Health}
    Status2 --> Overall
    Status3 --> Overall
    Status4 --> Overall
    Status5 --> Overall
    Status6 --> Overall
    Status7 --> Overall
    Status8 --> Overall
    
    Overall --> |All Healthy| Healthy[System Status: Healthy]
    Overall --> |Any Unhealthy| Unhealthy[System Status: Unhealthy]
```

### Performance Metrics Dashboard
- **Messages processed per minute**
- **Average processing time**
- **Success rate percentage**
- **Error rates by category**
- **Redis connection pool usage**
- **Memory and CPU utilization**

## Deployment Architecture

### Production Deployment Model
```mermaid
graph TB
    subgraph "Load Balancer"
        ALB[Application Load Balancer]
    end
    
    subgraph "Application Cluster"
        subgraph "Webhook Processing"
            API1[FastAPI Instance 1]
            API2[FastAPI Instance 2]
            API3[FastAPI Instance 3]
        end
        
        subgraph "SQS Processing"
            SQS1[SQS Consumer 1]
            SQS2[SQS Consumer 2]
            SQS3[SQS Consumer 3]
        end
    end
    
    subgraph "Data Layer"
        Redis1[(Redis Master)]
        Redis2[(Redis Replica 1)]
        Redis3[(Redis Replica 2)]
    end
    
    subgraph "Message Queues"
        SQSQueue[Amazon SQS Queues]
        DLQQueue[Dead Letter Queues]
    end
    
    ALB --> API1
    ALB --> API2
    ALB --> API3
    
    SQSQueue --> SQS1
    SQSQueue --> SQS2
    SQSQueue --> SQS3
    
    API1 --> Redis1
    API2 --> Redis1
    API3 --> Redis1
    SQS1 --> Redis1
    SQS2 --> Redis1
    SQS3 --> Redis1
    
    Redis1 --> Redis2
    Redis1 --> Redis3
    
    SQS1 --> DLQQueue
    SQS2 --> DLQQueue
    SQS3 --> DLQQueue
```

## Security Considerations

### Data Protection
- **Redis Authentication**: Password-protected Redis instances
- **AWS IAM**: Proper IAM roles for SQS access
- **API Authentication**: Webhook endpoint authentication
- **Data Encryption**: TLS for all data in transit

### Rate Limiting
- **API Rate Limits**: Per-client request limits
- **SQS Throttling**: Configurable message processing rates  
- **Redis Connection Limits**: Prevent connection pool exhaustion

## Scalability Design

### Horizontal Scaling Points
1. **FastAPI Instances**: Add more webhook processing servers
2. **SQS Consumers**: Increase number of consumer processes
3. **Redis Cluster**: Shard data across multiple Redis nodes
4. **Load Balancers**: Distribute traffic across instances

### Auto-Scaling Triggers
- **CPU Utilization** > 70%
- **Memory Usage** > 80%  
- **Queue Depth** > 1000 messages
- **Error Rate** > 5%

This architecture supports thousands of messages per minute with high reliability, comprehensive error handling, and horizontal scalability.