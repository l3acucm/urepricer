import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:convert';
import '../services/api_service.dart';
import '../models/api_models.dart';

class Offer {
  String sellerId;
  String subCondition;
  double listingPriceAmount;
  double landedPriceAmount;
  String currencyCode;
  bool isBuyBoxWinner;
  String fulfillmentChannel;

  Offer({
    required this.sellerId,
    this.subCondition = 'New',
    required this.listingPriceAmount,
    required this.landedPriceAmount,
    this.currencyCode = 'USD',
    this.isBuyBoxWinner = false,
    this.fulfillmentChannel = 'Merchant',
  });

  Map<String, dynamic> toJson() {
    return {
      'SellerId': sellerId,
      'SubCondition': subCondition,
      'ListingPrice': {'Amount': listingPriceAmount, 'CurrencyCode': currencyCode},
      'LandedPrice': {'Amount': landedPriceAmount, 'CurrencyCode': currencyCode},
      'IsBuyBoxWinner': isBuyBoxWinner,
      'FulfillmentChannel': fulfillmentChannel,
    };
  }
}

class SQSMessageDialog extends StatefulWidget {
  final RedisEntry entry;
  final ApiService apiService;
  final Function(String) onMessageSent;

  const SQSMessageDialog({
    super.key,
    required this.entry,
    required this.apiService,
    required this.onMessageSent,
  });

  @override
  State<SQSMessageDialog> createState() => _SQSMessageDialogState();
}

class _SQSMessageDialogState extends State<SQSMessageDialog> {
  bool _isSending = false;
  String _selectedQueueType = 'any_offer';
  List<Offer> _offers = [];
  ResetRules? _resetRules;
  bool _isLoadingResetRules = false;

  @override
  void initState() {
    super.initState();
    // Initialize with default offers
    _offers = [
      Offer(
        sellerId: 'A2345678901234',
        listingPriceAmount: 24.99,
        landedPriceAmount: 24.99,
        currencyCode: 'USD',
        isBuyBoxWinner: false,
        fulfillmentChannel: 'Merchant',
      ),
      Offer(
        sellerId: 'A3456789012345',
        listingPriceAmount: 26.50,
        landedPriceAmount: 26.50,
        currencyCode: 'USD',
        isBuyBoxWinner: true,
        fulfillmentChannel: 'Amazon',
      ),
    ];
    
    // Load reset rules for this seller
    _loadResetRules();
  }

  Future<void> _loadResetRules() async {
    setState(() {
      _isLoadingResetRules = true;
    });

    try {
      final response = await widget.apiService.getResetRules(widget.entry.sellerId);
      setState(() {
        _resetRules = response.resetRules;
      });
    } catch (e) {
      // Reset rules are optional, so don't show error for this
      setState(() {
        _resetRules = null;
      });
    } finally {
      setState(() {
        _isLoadingResetRules = false;
      });
    }
  }

  Map<String, dynamic> _generateMessageData() {
    // Calculate summary data from offers
    final offerCount = _offers.length;
    final lowestPrice = _offers.map((o) => o.listingPriceAmount).reduce((a, b) => a < b ? a : b);
    final buyBoxOffer = _offers.firstWhere((o) => o.isBuyBoxWinner, orElse: () => _offers.first);

    return {
      "NotificationType": "ANY_OFFER_CHANGED",
      "NotificationVersion": "1.0",
      "PayloadVersion": "1.0",
      "EventTime": DateTime.now().toUtc().toIso8601String(),
      "Payload": {
        "OfferChangeTrigger": {
          "MarketplaceId": "ATVPDKIKX0DER",
          "ASIN": widget.entry.asin,
          "ItemCondition": "New",
          "TimeOfOfferChange": DateTime.now().toUtc().toIso8601String(),
        },
        "Summary": {
          "NumberOfOffers": [
            {"Condition": "New", "FulfillmentChannel": "Amazon", "OfferCount": offerCount}
          ],
          "LowestPrices": [
            {
              "Condition": "New",
              "FulfillmentChannel": "Amazon",
              "ListingPrice": {"Amount": lowestPrice, "CurrencyCode": _offers.first.currencyCode},
              "LandedPrice": {"Amount": lowestPrice, "CurrencyCode": _offers.first.currencyCode}
            }
          ],
          "BuyBoxPrices": [
            {
              "Condition": "New",
              "ListingPrice": {"Amount": buyBoxOffer.listingPriceAmount, "CurrencyCode": buyBoxOffer.currencyCode},
              "LandedPrice": {"Amount": buyBoxOffer.landedPriceAmount, "CurrencyCode": buyBoxOffer.currencyCode}
            }
          ]
        },
        "Offers": _offers.map((offer) => offer.toJson()).toList()
      }
    };
  }

  Future<void> _sendMessage() async {
    // Validate that only one offer is buybox winner
    final buyBoxWinners = _offers.where((o) => o.isBuyBoxWinner).length;
    if (buyBoxWinners != 1) {
      _showError('Exactly one offer must be the BuyBox winner');
      return;
    }

    setState(() {
      _isSending = true;
    });

    try {
      final messageData = _generateMessageData();
      const encoder = JsonEncoder.withIndent('  ');
      final messageBody = encoder.convert(messageData);

      final response = await widget.apiService.sendTestSQS(
        messageBody: messageBody,
        queueType: _selectedQueueType,
      );

      widget.onMessageSent('SQS message sent successfully: ${response.messageId}');
      Navigator.of(context).pop();
    } catch (e) {
      _showError('Failed to send SQS message: $e');
    } finally {
      setState(() {
        _isSending = false;
      });
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  Future<void> _copyToClipboard(String value) async {
    await Clipboard.setData(ClipboardData(text: value));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Copied: $value'),
        backgroundColor: Colors.green,
        duration: const Duration(seconds: 1),
      ),
    );
  }

  Future<void> _clearCalculatedPrice() async {
    try {
      final response = await widget.apiService.clearCalculatedPrice(
        widget.entry.asin,
        widget.entry.sellerId,
        widget.entry.sku,
      );
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Calculated price cleared successfully'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to clear calculated price: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  String _formatPrice(double? price, String region) {
    if (price == null) return 'N/A';
    
    String symbol;
    switch (region?.toLowerCase()) {
      case 'uk':
        symbol = '£';
        break;
      case 'us':
        symbol = '\$';
        break;
      case 'eu':
      case 'de':
      case 'fr':
      case 'it':
      case 'es':
        symbol = '€';
        break;
      default:
        symbol = '\$'; // Default to USD
    }
    
    return '$symbol${price.toStringAsFixed(2)}';
  }

  Widget _buildCopyableField(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Expanded(
            child: Text('$label: $value'),
          ),
          IconButton(
            onPressed: () => _copyToClipboard(value),
            icon: const Icon(Icons.copy, size: 16),
            tooltip: 'Copy $label',
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
        ],
      ),
    );
  }

  void _addOffer() {
    setState(() {
      _offers.add(Offer(
        sellerId: 'A${(1000000000000 + _offers.length).toString()}',
        listingPriceAmount: 25.00,
        landedPriceAmount: 25.00,
        currencyCode: _offers.isNotEmpty ? _offers.first.currencyCode : 'USD',
      ));
    });
  }

  void _removeOffer(int index) {
    if (_offers.length > 1) {
      setState(() {
        _offers.removeAt(index);
      });
    }
  }

  void _moveOfferUp(int index) {
    if (index > 0) {
      setState(() {
        final offer = _offers.removeAt(index);
        _offers.insert(index - 1, offer);
      });
    }
  }

  void _moveOfferDown(int index) {
    if (index < _offers.length - 1) {
      setState(() {
        final offer = _offers.removeAt(index);
        _offers.insert(index + 1, offer);
      });
    }
  }

  Widget _buildOfferCard(int index) {
    final offer = _offers[index];
    
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with controls
            Row(
              children: [
                Text(
                  'Offer ${index + 1}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const Spacer(),
                IconButton(
                  onPressed: index > 0 ? () => _moveOfferUp(index) : null,
                  icon: const Icon(Icons.keyboard_arrow_up),
                  tooltip: 'Move up',
                ),
                IconButton(
                  onPressed: index < _offers.length - 1 ? () => _moveOfferDown(index) : null,
                  icon: const Icon(Icons.keyboard_arrow_down),
                  tooltip: 'Move down',
                ),
                IconButton(
                  onPressed: _offers.length > 1 ? () => _removeOffer(index) : null,
                  icon: const Icon(Icons.delete),
                  tooltip: 'Remove offer',
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            // First row: Seller ID, Sub Condition, Currency
            Row(
              children: [
                Expanded(
                  flex: 2,
                  child: TextFormField(
                    initialValue: offer.sellerId,
                    decoration: const InputDecoration(
                      labelText: 'Seller ID',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    onChanged: (value) {
                      offer.sellerId = value;
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: offer.subCondition,
                    decoration: const InputDecoration(
                      labelText: 'Condition',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: const [
                      DropdownMenuItem(value: 'New', child: Text('New')),
                      DropdownMenuItem(value: 'Used', child: Text('Used')),
                      DropdownMenuItem(value: 'Refurbished', child: Text('Refurbished')),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        setState(() {
                          offer.subCondition = value;
                        });
                      }
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: offer.currencyCode,
                    decoration: const InputDecoration(
                      labelText: 'Currency',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: const [
                      DropdownMenuItem(value: 'USD', child: Text('USD')),
                      DropdownMenuItem(value: 'EUR', child: Text('EUR')),
                      DropdownMenuItem(value: 'GBP', child: Text('GBP')),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        setState(() {
                          offer.currencyCode = value;
                        });
                      }
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            // Second row: Prices and Fulfillment
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    initialValue: offer.listingPriceAmount.toStringAsFixed(2),
                    decoration: const InputDecoration(
                      labelText: 'Listing Price',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    keyboardType: TextInputType.number,
                    inputFormatters: [
                      FilteringTextInputFormatter.allow(RegExp(r'^\d+\.?\d{0,2}')),
                    ],
                    onChanged: (value) {
                      final price = double.tryParse(value);
                      if (price != null) {
                        offer.listingPriceAmount = price;
                      }
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextFormField(
                    initialValue: offer.landedPriceAmount.toStringAsFixed(2),
                    decoration: const InputDecoration(
                      labelText: 'Landed Price',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    keyboardType: TextInputType.number,
                    inputFormatters: [
                      FilteringTextInputFormatter.allow(RegExp(r'^\d+\.?\d{0,2}')),
                    ],
                    onChanged: (value) {
                      final price = double.tryParse(value);
                      if (price != null) {
                        offer.landedPriceAmount = price;
                      }
                    },
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: offer.fulfillmentChannel,
                    decoration: const InputDecoration(
                      labelText: 'Fulfillment',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: const [
                      DropdownMenuItem(value: 'Amazon', child: Text('Amazon')),
                      DropdownMenuItem(value: 'Merchant', child: Text('Merchant')),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        setState(() {
                          offer.fulfillmentChannel = value;
                        });
                      }
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            // BuyBox Winner checkbox
            CheckboxListTile(
              title: const Text('BuyBox Winner'),
              value: offer.isBuyBoxWinner,
              onChanged: (value) {
                setState(() {
                  // Ensure only one buybox winner
                  if (value == true) {
                    for (var o in _offers) {
                      o.isBuyBoxWinner = false;
                    }
                  }
                  offer.isBuyBoxWinner = value ?? false;
                });
              },
              controlAffinity: ListTileControlAffinity.leading,
              dense: true,
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: MediaQuery.of(context).size.width * 0.9,
        height: MediaQuery.of(context).size.height * 0.9,
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Icon(
                  Icons.send,
                  size: 32,
                  color: Theme.of(context).primaryColor,
                ),
                const SizedBox(width: 12),
                Text(
                  'Send Test SQS Message',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const Spacer(),
                IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Entry info
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Entry Details',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 12),
                    // First row: Basic info
                    Row(
                      children: [
                        Expanded(
                          child: _buildCopyableField('ASIN', widget.entry.asin),
                        ),
                        Expanded(
                          child: _buildCopyableField('Seller ID', widget.entry.sellerId),
                        ),
                        Expanded(
                          child: _buildCopyableField('SKU', widget.entry.sku),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    // Second row: Region and Strategy
                    Row(
                      children: [
                        Expanded(
                          child: _buildCopyableField('Region', widget.entry.region ?? 'N/A'),
                        ),
                        Expanded(
                          child: _buildCopyableField('Strategy', widget.entry.strategy?.type ?? 'N/A'),
                        ),
                        Expanded(
                          child: _buildCopyableField('Status', widget.entry.productData.status ?? 'N/A'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    // Third row: Prices
                    Row(
                      children: [
                        Expanded(
                          child: _buildCopyableField('Min Price', _formatPrice(widget.entry.productData.minPrice, widget.entry.region ?? 'us')),
                        ),
                        Expanded(
                          child: _buildCopyableField('Listed Price', _formatPrice(widget.entry.productData.listedPrice, widget.entry.region ?? 'us')),
                        ),
                        Expanded(
                          child: _buildCopyableField('Max Price', _formatPrice(widget.entry.productData.maxPrice, widget.entry.region ?? 'us')),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    // Fourth row: Additional info
                    Row(
                      children: [
                        Expanded(
                          child: _buildCopyableField('Default Price', _formatPrice(widget.entry.productData.defaultPrice, widget.entry.region ?? 'us')),
                        ),
                        Expanded(
                          child: Row(
                            children: [
                              Expanded(
                                child: _buildCopyableField('Calculated Price', _formatPrice(widget.entry.calculatedPrice?.newPrice, widget.entry.region ?? 'us')),
                              ),
                              if (widget.entry.calculatedPrice?.newPrice != null)
                                IconButton(
                                  onPressed: _clearCalculatedPrice,
                                  icon: const Icon(Icons.clear, size: 16),
                                  tooltip: 'Clear calculated price',
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                ),
                            ],
                          ),
                        ),
                        Expanded(
                          child: _buildCopyableField('Quantity', widget.entry.productData.quantity?.toString() ?? 'N/A'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    // Fifth row: Strategy properties and repricing status
                    Row(
                      children: [
                        Expanded(
                          child: _buildCopyableField('Beat By', widget.entry.strategy?.beatBy ?? 'N/A'),
                        ),
                        Expanded(
                          child: _buildCopyableField('Min Price Rule', widget.entry.strategy?.minPriceRule ?? 'N/A'),
                        ),
                        Expanded(
                          child: _buildCopyableField('Max Price Rule', widget.entry.strategy?.maxPriceRule ?? 'N/A'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    // Sixth row: Repricing status
                    Row(
                      children: [
                        Expanded(
                          child: Row(
                            children: [
                              Text('Repricing Status: '),
                              Icon(
                                widget.entry.repricingPaused ? Icons.pause_circle : Icons.play_circle,
                                color: widget.entry.repricingPaused ? Colors.red : Colors.green,
                                size: 16,
                              ),
                              const SizedBox(width: 4),
                              Text(widget.entry.repricingPaused ? 'PAUSED' : 'ACTIVE'),
                            ],
                          ),
                        ),
                        if (_isLoadingResetRules)
                          const Expanded(
                            child: Row(
                              children: [
                                Text('Reset Rules: '),
                                SizedBox(width: 8),
                                SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                ),
                              ],
                            ),
                          )
                        else if (_resetRules != null)
                          Expanded(
                            flex: 2,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Reset Rules:', style: Theme.of(context).textTheme.labelMedium),
                                const SizedBox(height: 4),
                                Text('Enabled: ${_resetRules!.priceResetEnabled ? "Yes" : "No"}', style: const TextStyle(fontSize: 12)),
                                if (_resetRules!.priceResetEnabled) ...[
                                  Text('Reset: ${_resetRules!.priceResetTime.toString().padLeft(2, '0')}:00', style: const TextStyle(fontSize: 12)),
                                  Text('Resume: ${_resetRules!.priceResumeTime.toString().padLeft(2, '0')}:00', style: const TextStyle(fontSize: 12)),
                                  Text('Market: ${_resetRules!.market.toUpperCase()}', style: const TextStyle(fontSize: 12)),
                                ],
                              ],
                            ),
                          )
                        else
                          const Expanded(
                            child: Text('Reset Rules: No rules found'),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Queue type and Add offer button
            Row(
              children: [
                Text(
                  'Queue Type:',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(width: 16),
                DropdownButton<String>(
                  value: _selectedQueueType,
                  items: const [
                    DropdownMenuItem(
                      value: 'any_offer',
                      child: Text('Any Offer Changed'),
                    ),
                    DropdownMenuItem(
                      value: 'feed_processing',
                      child: Text('Feed Processing'),
                    ),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      setState(() {
                        _selectedQueueType = value;
                      });
                    }
                  },
                ),
                const Spacer(),
                ElevatedButton.icon(
                  onPressed: _addOffer,
                  icon: const Icon(Icons.add),
                  label: const Text('Add Offer'),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Offers list
            Text(
              'Offers (${_offers.length}):',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            
            Expanded(
              child: ListView.builder(
                itemCount: _offers.length,
                itemBuilder: (context, index) => _buildOfferCard(index),
              ),
            ),

            // Actions
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _isSending ? null : _sendMessage,
                  child: _isSending
                      ? const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                            SizedBox(width: 8),
                            Text('Sending...'),
                          ],
                        )
                      : const Text('Send Message'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}