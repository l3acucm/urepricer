import 'dart:convert';
import 'dart:html' as html;
import 'package:http/http.dart' as http;
import '../models/api_models.dart';

class ApiService {
  late final String baseUrl;
  late final http.Client client;

  ApiService() {
    // Get API base URL from environment variable
    baseUrl = _getApiBaseUrl();
    client = http.Client();
  }

  String _getApiBaseUrl() {
    // In Flutter web, environment variables are accessed differently
    // We'll check multiple possible sources
    
    // First try to get from the browser's environment
    String? envUrl = const String.fromEnvironment('API_BASE_URL');
    if (envUrl.isNotEmpty) {
      return envUrl;
    }

    // Try to get from window object (if set via JavaScript)
    try {
      final dynamic apiUrl = html.window.localStorage['API_BASE_URL'] ?? 
                            html.window.sessionStorage['API_BASE_URL'];
      if (apiUrl != null && apiUrl.toString().isNotEmpty) {
        return apiUrl.toString();
      }
    } catch (e) {
      // Ignore errors when accessing localStorage
    }

    // Default fallback
    return 'http://localhost:8001';
  }

  Future<ListEntriesResponse> getEntries({
    String? sellerId,
    String? region,
    String? asin,
    int limit = 100,
    int offset = 0,
  }) async {
    final queryParams = <String, String>{
      'limit': limit.toString(),
      'offset': offset.toString(),
    };

    if (sellerId != null && sellerId.isNotEmpty) {
      queryParams['seller_id'] = sellerId;
    }
    if (region != null && region.isNotEmpty) {
      queryParams['region'] = region;
    }
    if (asin != null && asin.isNotEmpty) {
      queryParams['asin'] = asin;
    }

    final uri = Uri.parse('$baseUrl/admin/list-entries').replace(
      queryParameters: queryParams,
    );

    final response = await client.get(uri);

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return ListEntriesResponse.fromJson(json);
    } else {
      throw Exception('Failed to fetch entries: ${response.statusCode} ${response.body}');
    }
  }

  Future<PopulateMySQLResponse> populateFromMySQL({int batchSize = 1000}) async {
    final uri = Uri.parse('$baseUrl/admin/populate-from-mysql').replace(
      queryParameters: {'batch_size': batchSize.toString()},
    );

    final response = await client.post(uri);

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return PopulateMySQLResponse.fromJson(json);
    } else {
      throw Exception('Failed to populate from MySQL: ${response.statusCode} ${response.body}');
    }
  }

  Future<SendSQSResponse> sendTestSQS({
    required String messageBody,
    String queueType = 'any_offer',
  }) async {
    final uri = Uri.parse('$baseUrl/admin/send-test-sqs').replace(
      queryParameters: {'queue_type': queueType},
    );

    Map<String, dynamic> messageData;
    try {
      messageData = jsonDecode(messageBody);
    } catch (e) {
      throw Exception('Invalid JSON format: $e');
    }

    final response = await client.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(messageData),
    );

    if (response.statusCode == 200) {
      final json = jsonDecode(response.body);
      return SendSQSResponse.fromJson(json);
    } else {
      throw Exception('Failed to send SQS message: ${response.statusCode} ${response.body}');
    }
  }

  void dispose() {
    client.close();
  }
}

// Helper function to generate SQS message template
String generateSQSMessageTemplate(String asin) {
  final template = {
    "NotificationType": "ANY_OFFER_CHANGED",
    "NotificationVersion": "1.0",
    "PayloadVersion": "1.0",
    "EventTime": DateTime.now().toUtc().toIso8601String(),
    "Payload": {
      "OfferChangeTrigger": {
        "MarketplaceId": "ATVPDKIKX0DER",
        "ASIN": asin,
        "ItemCondition": "New",
        "TimeOfOfferChange": DateTime.now().toUtc().toIso8601String(),
      },
      "Summary": {
        "NumberOfOffers": [
          {"Condition": "New", "FulfillmentChannel": "Amazon", "OfferCount": 2}
        ],
        "LowestPrices": [
          {
            "Condition": "New",
            "FulfillmentChannel": "Amazon",
            "ListingPrice": {"Amount": 24.99, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 24.99, "CurrencyCode": "USD"}
          }
        ],
        "BuyBoxPrices": [
          {
            "Condition": "New",
            "ListingPrice": {"Amount": 26.50, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 26.50, "CurrencyCode": "USD"}
          }
        ]
      },
      "Offers": [
        {
          "SellerId": "A2345678901234",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 24.99, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": false,
          "FulfillmentChannel": "Merchant"
        },
        {
          "SellerId": "A3456789012345",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 26.50, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": true,
          "FulfillmentChannel": "Amazon"
        }
      ]
    }
  };

  // Return formatted JSON
  const encoder = JsonEncoder.withIndent('  ');
  return encoder.convert(template);
}