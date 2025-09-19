class RedisEntry {
  final String asin;
  final String sellerId;
  final String sku;
  final String? region;
  final ProductData productData;
  final Strategy? strategy;
  final CalculatedPrice? calculatedPrice;

  RedisEntry({
    required this.asin,
    required this.sellerId,
    required this.sku,
    this.region,
    required this.productData,
    this.strategy,
    this.calculatedPrice,
  });

  factory RedisEntry.fromJson(Map<String, dynamic> json) {
    return RedisEntry(
      asin: json['asin'] ?? '',
      sellerId: json['seller_id'] ?? '',
      sku: json['sku'] ?? '',
      region: json['region'],
      productData: ProductData.fromJson(json['product_data'] ?? {}),
      strategy: json['strategy'] != null && (json['strategy'] as Map).isNotEmpty
          ? Strategy.fromJson(json['strategy'])
          : null,
      calculatedPrice: json['calculated_price'] != null
          ? CalculatedPrice.fromJson(json['calculated_price'])
          : null,
    );
  }
}

class ProductData {
  final double? listedPrice;
  final double? minPrice;
  final double? maxPrice;
  final double? defaultPrice;
  final String? strategyId;
  final String? status;
  final String? itemCondition;
  final int? quantity;

  ProductData({
    this.listedPrice,
    this.minPrice,
    this.maxPrice,
    this.defaultPrice,
    this.strategyId,
    this.status,
    this.itemCondition,
    this.quantity,
  });

  factory ProductData.fromJson(Map<String, dynamic> json) {
    return ProductData(
      listedPrice: _parseDouble(json['listed_price']),
      minPrice: _parseDouble(json['min_price']),
      maxPrice: _parseDouble(json['max_price']),
      defaultPrice: _parseDouble(json['default_price']),
      strategyId: json['strategy_id']?.toString(),
      status: json['status'],
      itemCondition: json['item_condition'],
      quantity: _parseInt(json['quantity']),
    );
  }

  static double? _parseDouble(dynamic value) {
    if (value == null) return null;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  static int? _parseInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is double) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }
}

class Strategy {
  final String? type;
  final String? beatBy;
  final String? minPriceRule;
  final String? maxPriceRule;

  Strategy({
    this.type,
    this.beatBy,
    this.minPriceRule,
    this.maxPriceRule,
  });

  factory Strategy.fromJson(Map<String, dynamic> json) {
    return Strategy(
      type: json['type'],
      beatBy: json['beat_by'],
      minPriceRule: json['min_price_rule'],
      maxPriceRule: json['max_price_rule'],
    );
  }
}

class CalculatedPrice {
  final double? newPrice;
  final double? oldPrice;
  final String? strategyUsed;
  final String? strategyId;
  final double? competitorPrice;
  final String? calculatedAt;

  CalculatedPrice({
    this.newPrice,
    this.oldPrice,
    this.strategyUsed,
    this.strategyId,
    this.competitorPrice,
    this.calculatedAt,
  });

  factory CalculatedPrice.fromJson(Map<String, dynamic> json) {
    return CalculatedPrice(
      newPrice: ProductData._parseDouble(json['new_price']),
      oldPrice: ProductData._parseDouble(json['old_price']),
      strategyUsed: json['strategy_used'],
      strategyId: json['strategy_id']?.toString(),
      competitorPrice: ProductData._parseDouble(json['competitor_price']),
      calculatedAt: json['calculated_at'],
    );
  }
}

class ListEntriesResponse {
  final String status;
  final int totalKeysFound;
  final int entriesReturned;
  final int offset;
  final int limit;
  final Map<String, dynamic> filtersApplied;
  final List<RedisEntry> entries;

  ListEntriesResponse({
    required this.status,
    required this.totalKeysFound,
    required this.entriesReturned,
    required this.offset,
    required this.limit,
    required this.filtersApplied,
    required this.entries,
  });

  factory ListEntriesResponse.fromJson(Map<String, dynamic> json) {
    return ListEntriesResponse(
      status: json['status'] ?? '',
      totalKeysFound: json['total_keys_found'] ?? 0,
      entriesReturned: json['entries_returned'] ?? 0,
      offset: json['offset'] ?? 0,
      limit: json['limit'] ?? 0,
      filtersApplied: json['filters_applied'] ?? {},
      entries: (json['entries'] as List? ?? [])
          .map((e) => RedisEntry.fromJson(e))
          .toList(),
    );
  }
}

class PopulateMySQLResponse {
  final String status;
  final String message;
  final int batchSize;
  final Map<String, dynamic> results;
  final String completedAt;

  PopulateMySQLResponse({
    required this.status,
    required this.message,
    required this.batchSize,
    required this.results,
    required this.completedAt,
  });

  factory PopulateMySQLResponse.fromJson(Map<String, dynamic> json) {
    return PopulateMySQLResponse(
      status: json['status'] ?? '',
      message: json['message'] ?? '',
      batchSize: json['batch_size'] ?? 0,
      results: json['results'] ?? {},
      completedAt: json['completed_at'] ?? '',
    );
  }
}

class SendSQSResponse {
  final String status;
  final String message;
  final String queueUrl;
  final String queueType;
  final String? messageId;
  final String sentAt;

  SendSQSResponse({
    required this.status,
    required this.message,
    required this.queueUrl,
    required this.queueType,
    this.messageId,
    required this.sentAt,
  });

  factory SendSQSResponse.fromJson(Map<String, dynamic> json) {
    return SendSQSResponse(
      status: json['status'] ?? '',
      message: json['message'] ?? '',
      queueUrl: json['queue_url'] ?? '',
      queueType: json['queue_type'] ?? '',
      messageId: json['message_id'],
      sentAt: json['sent_at'] ?? '',
    );
  }
}