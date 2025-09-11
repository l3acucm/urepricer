# Initial Requirements Checklist

This document contains requirements extracted from the legacy documentation files in `docs/source/`. Each requirement is grouped by category and references its source document.

## Business Logic Requirements

### Core Repricing Strategy
- **Competitive Price Matching**: The system must support three competitive matching strategies: MATCH_BUYBOX (select competitor with buy box), LOWEST_FBA_PRICE (choose competitor with lowest FBA price), and LOWEST_PRICE (choose competitor with lowest overall price). Default behavior is MATCH_BUYBOX. *Source: Repricer Strategy Properties Values.html*

- **Price Adjustment Logic**: The system must implement beat_by functionality where prices can be adjusted relative to competitor prices using positive values (increase competitor price) or negative values (decrease competitor price), with default being 0 (match competitor price exactly). *Source: Repricer Strategy Properties Values.html*

- **Boundary Rule Enforcement**: When calculated prices fall outside min/max boundaries, the system must apply configurable rules: JUMP_TO_MIN, JUMP_TO_MAX, JUMP_TO_AVG, DO_NOTHING, DEFAULT_PRICE, or MATCH_COMPETITOR. Default min_price_rule is JUMP_TO_MIN and max_price_rule is JUMP_TO_MAX. *Source: Repricer Strategy Properties Values.html*

- **Inventory Age-Based Repricing**: The system must support age-based strategy switching with predefined ranges (0-90, 91-180, 181-270, 271-365, 365+ days) where different strategies are applied based on how long inventory has been in Amazon warehouses. *Source: Repricer Strategy Properties Values.html*

### B2B Repricing Support
- **B2B Competitive Logic**: The system must handle B2B repricing with quantity-based competition rules where b2b_compete_for can target LOW (competitors with lower quantity) or HIGH (competitors with higher quantity) offer quantities. *Source: Repricer Strategy Properties Values.html*

- **B2B Price Adjustment**: The system must support B2B-specific price adjustment rules including AVERAGE (set price as average of our price and competitor) and BEAT_BY (apply standard beat_by logic to competitor price). *Source: Repricer Strategy Properties Values.html*

- **B2B Tier Management**: The system must support 5-tier B2B pricing structure (Tier 1-5) with quantity thresholds and individual pricing rules for each tier. *Source: Repricer Queues.html*

### Exception Handling and Skipping Logic
- **Self-Competition Prevention**: The system must skip repricing when our seller already offers the lowest price (for LOWEST_PRICE strategy) or lowest FBA price (for LOWEST_FBA_PRICE strategy) or already has the buy box (for MATCH_BUYBOX strategy). *Source: Repricer Exception Handling.html*

- **Data Validation Skipping**: The system must skip repricing when essential data is missing including: ASIN data not in Redis, strategy_id missing or None, min_price equals max_price, inventory_quantity is 0 or None, or updated_price is None or ≤0. *Source: Repricer Exception Handling.html*

- **Strategy Rule Validation**: The system must validate strategy rules and skip repricing with appropriate error messages when rules are not set, methods are undefined, or required prices (min, max, default, competitor) are missing for the specified rule. *Source: Repricer Exception Handling.html*

### Future Enhancements
- **Profit Maximization Strategy**: The system should implement enhanced profit maximization including default fallback when only seller present, average pricing when both min/max present, and buybox jumping when owning buybox with higher-priced buybox-eligible sellers. *Source: Future Development.html*

- **Night-time Price Positioning**: The system should support raising prices for products at minimum price during non-peak hours to enable continued repricing cycles, with separate schedules for US and UK marketplaces. *Source: Future Development.html*

- **Feed Success Tracking**: The system should add success/error fields to feed submissions and send status updates to the same Kafka topic with detailed error descriptions. *Source: Future Development.html*

## Architecture Requirements

### Data Storage and Caching
- **Redis Data Management**: The system must use Redis for caching listing data, strategy data, and account credentials with structured key-value storage supporting nested data structures for complex product hierarchies (ASIN → Seller → SKU). *Source: Repricer Queues.html*

- **Data Persistence**: The system must maintain data persistence with TTL (Time To Live) validation ensuring data freshness, and support for batch operations to handle multiple products and strategies efficiently. *Source: Funtional Specification Document (Repricer).html*

- **Hierarchical Data Structure**: The system must support hierarchical data organization with ASIN as top level, seller_id as second level, and SKU as third level, allowing for efficient data retrieval and management. *Source: Repricer Models.html*

### Message Queue Architecture
- **Kafka Topic Management**: The system must implement multiple Kafka topics including ah_repricer (repricing payloads), ah-repricer-listing-data (strategy and listing data), ah-repricer-creds (account credentials), ah-repricer-delete-data (data deletion), and ah-repricer-alerts (notifications). *Source: Repricer Queues.html*

- **SQS Integration**: The system must support SQS queue integration for processed data output (ah--processed-data queue) with messages under 250MB containing complete feed submission results and repricing outcomes. *Source: Repricer Queues.html*

- **Batch Processing**: The system must handle both single product messages and batch processing for multiple products in a single message, supporting bulk operations for efficiency. *Source: Repricer Queues.html*

### Notification and Alerting
- **Real-time Alerts**: The system must provide real-time alerting through ah-repricer-alerts topic covering credential validation failures, feed submission errors, and hourly error feed updates. *Source: Repricer Queues.html*

- **Error Tracking**: The system must track and report various error types including invalid credentials, feed submission failures, and strategy application errors with detailed error messages and context. *Source: Repricer Queues.html*

## Deployment Requirements

### Container and Orchestration
- **Docker Containerization**: The system must be containerized using Docker with proper image building (docker build -t core-engine:latest), execution (docker run -it), and registry publishing (docker push) capabilities. *Source: Repricer Deployment.html*

- **Kubernetes Deployment**: The system must deploy on Kubernetes cluster with kubeadm setup, Calico networking, and proper pod/service management including scaling capabilities (kubectl scale deployment ah-core-engine --replicas=2). *Source: Repricer Deployment.html*

- **Helm Chart Management**: The system must use Helm for deployment management with custom chart creation (helm create ah-core-engine), values.yaml customization, and upgrade capabilities (helm upgrade). *Source: Repricer Deployment.html*

### Infrastructure Components
- **Kafka Infrastructure**: The system must deploy Kafka with ZooKeeper coordination, proper topic management, and consumer group monitoring using specified host (92.119.129.177) and port (31483) configuration. *Source: Repricer Deployment.html*

- **Cluster Architecture**: The system must support multi-node Kubernetes cluster with master node (10.0.0.2) and worker nodes (92.119.129.139), proper networking with Calico SDN, and namespace organization (calico-apiserver, calico-system, kube-system). *Source: Repricer Deployment.html*

### Monitoring and Maintenance
- **Pod Management**: The system must provide comprehensive pod management including listing (kubectl get pods), detailed description (kubectl describe pods), log viewing (kubectl logs -f), and shell access (kubectl exec -it). *Source: Repricer Deployment.html*

- **Service Discovery**: The system must support service discovery and management across different namespaces with proper service listing (kubectl get svc -A) and namespace-specific operations. *Source: Repricer Deployment.html*

## Data Management Requirements

### Product and Listing Models
- **Product Data Structure**: The system must handle comprehensive product data including ASIN, seller_id, SKU, pricing boundaries (min, max, default, listed), strategy_id, inventory metrics, and status tracking. *Source: Repricer Models.html*

- **Pricing Data Validation**: The system must validate pricing data ensuring logical consistency between min_price, max_price, default_price, and listed_price with proper error handling for invalid configurations. *Source: Repricer Models.html*

- **Inventory Management**: The system must track inventory_age, inventory_quantity, item_condition, and fulfillment_type with default values (0, None, "new", "AMAZON" respectively) when not provided. *Source: Repricer Queues.html*

### Data Lifecycle Management
- **Data Deletion Operations**: The system must support granular data deletion including SKU-level deletion, seller-level deletion, user account deletion, and strategy deletion with proper cascading effects and data integrity maintenance. *Source: Repricer Queues.html*

- **User Account Management**: The system must validate user credentials, manage account enablement/disablement, handle subscription to notifications, and maintain data integrity in Redis when accounts are modified or deleted. *Source: Repricer Queues.html*

- **Strategy Data Management**: The system must handle strategy creation, modification, and deletion while maintaining references in listing data and providing graceful handling when strategies are deleted (skip repricing for orphaned listings). *Source: Repricer Queues.html*

### Audit and Logging
- **Price Change Logging**: The system must log comprehensive price change information including timestamp, user_id, seller_id, SKU, ASIN, old/new prices, price boundaries, strategy details, market, success status, and detailed repricing messages. *Source: Repricer Queues.html*

- **Error Documentation**: The system must maintain detailed error logs with specific error messages for different failure scenarios including missing data, invalid rules, boundary violations, and strategy application failures. *Source: Repricer Exception Handling.html*

- **Repricing Message Details**: The system must generate detailed repricing messages explaining strategy application, competitive analysis, rule application, and final price decisions for audit and troubleshooting purposes. *Source: Repricer Queues.html*