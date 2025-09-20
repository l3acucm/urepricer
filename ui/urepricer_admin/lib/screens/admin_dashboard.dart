import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:data_table_2/data_table_2.dart';
import '../services/api_service.dart';
import '../models/api_models.dart';
import '../widgets/sqs_message_dialog.dart';

class AdminDashboard extends StatefulWidget {
  const AdminDashboard({super.key});

  @override
  State<AdminDashboard> createState() => _AdminDashboardState();
}

class _AdminDashboardState extends State<AdminDashboard> {
  final ApiService _apiService = ApiService();
  
  List<RedisEntry> _entries = [];
  bool _isLoading = false;
  bool _isPopulating = false;
  
  // Pagination
  int _currentPage = 0;
  int _totalPages = 0;
  int _itemsPerPage = 50;
  int _totalItems = 0;

  // Filters
  final TextEditingController _sellerIdController = TextEditingController();
  final TextEditingController _asinController = TextEditingController();
  String? _selectedRegion;

  @override
  void initState() {
    super.initState();
    _loadEntries();
  }

  @override
  void dispose() {
    _apiService.dispose();
    _sellerIdController.dispose();
    _asinController.dispose();
    super.dispose();
  }

  Future<void> _loadEntries() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final response = await _apiService.getEntries(
        sellerId: _sellerIdController.text.isEmpty ? null : _sellerIdController.text,
        region: _selectedRegion,
        asin: _asinController.text.isEmpty ? null : _asinController.text,
        limit: _itemsPerPage,
        offset: _currentPage * _itemsPerPage,
      );

      setState(() {
        _entries = response.entries;
        _totalItems = response.totalKeysFound;
        _totalPages = (_totalItems / _itemsPerPage).ceil();
      });

      _showToast('Loaded ${response.entriesReturned} entries');
    } catch (e) {
      _showToast('Error loading entries: $e', isError: true);
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _populateFromMySQL() async {
    setState(() {
      _isPopulating = true;
      _entries = []; // Clear table
    });

    try {
      final response = await _apiService.populateFromMySQL();
      
      _showToast('MySQL population completed: ${response.results['total_products_saved']} products saved');
      
      // Refresh entries after population
      _currentPage = 0;
      await _loadEntries();
    } catch (e) {
      _showToast('Error populating from MySQL: $e', isError: true);
    } finally {
      setState(() {
        _isPopulating = false;
      });
    }
  }

  String _formatPrice(double? price, String region) {
    if (price == null) return 'N/A';
    
    String symbol;
    switch (region.toLowerCase()) {
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

  void _showToast(String message, {bool isError = false}) {
    Fluttertoast.showToast(
      msg: message,
      toastLength: Toast.LENGTH_LONG,
      gravity: ToastGravity.TOP,
      backgroundColor: isError ? Colors.red : Colors.green,
      textColor: Colors.white,
      fontSize: 16.0,
    );
  }

  void _applyFilters() {
    _currentPage = 0;
    _loadEntries();
  }

  void _clearFilters() {
    _sellerIdController.clear();
    _asinController.clear();
    setState(() {
      _selectedRegion = null;
    });
    _applyFilters();
  }

  void _showSQSDialog(RedisEntry entry) {
    showDialog(
      context: context,
      builder: (context) => SQSMessageDialog(
        entry: entry,
        apiService: _apiService,
        onMessageSent: (message) {
          _showToast(message);
        },
      ),
    );
  }

  Future<void> _triggerReset(String sellerId) async {
    try {
      final response = await _apiService.triggerReset(sellerId);
      _showToast('Reset triggered for $sellerId: ${response.results['reset_count']} products reset');
      await _loadEntries(); // Refresh data
    } catch (e) {
      _showToast('Error triggering reset: $e', isError: true);
    }
  }

  Future<void> _triggerResume(String sellerId) async {
    try {
      final response = await _apiService.triggerResume(sellerId);
      _showToast('Resume triggered for $sellerId: ${response.results['resume_count']} products resumed');
      await _loadEntries(); // Refresh data
    } catch (e) {
      _showToast('Error triggering resume: $e', isError: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('URepricer Admin Dashboard'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Column(
        children: [
          // Filters and Actions
          Card(
            margin: const EdgeInsets.all(16),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  // Filter row
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _sellerIdController,
                          decoration: const InputDecoration(
                            labelText: 'Seller ID',
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: _asinController,
                          decoration: const InputDecoration(
                            labelText: 'ASIN',
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _selectedRegion,
                          decoration: const InputDecoration(
                            labelText: 'Region',
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                          items: const [
                            DropdownMenuItem(value: null, child: Text('All')),
                            DropdownMenuItem(value: 'uk', child: Text('UK')),
                            DropdownMenuItem(value: 'us', child: Text('US')),
                            DropdownMenuItem(value: 'amazon', child: Text('Amazon')),
                          ],
                          onChanged: (value) {
                            setState(() {
                              _selectedRegion = value;
                            });
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  // Action buttons
                  Row(
                    children: [
                      ElevatedButton(
                        onPressed: _isLoading ? null : _applyFilters,
                        child: const Text('Apply Filters'),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: _isLoading ? null : _clearFilters,
                        child: const Text('Clear Filters'),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton.icon(
                        onPressed: _isLoading ? null : _loadEntries,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Refresh'),
                      ),
                      const Spacer(),
                      ElevatedButton(
                        onPressed: _isPopulating ? null : _populateFromMySQL,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.orange,
                          foregroundColor: Colors.white,
                        ),
                        child: _isPopulating
                            ? const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                    ),
                                  ),
                                  SizedBox(width: 8),
                                  Text('Populating...'),
                                ],
                              )
                            : const Text('Populate from MySQL'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          // Pagination info
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Text(
                  'Total: $_totalItems entries | Page ${_currentPage + 1} of $_totalPages',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const Spacer(),
                IconButton(
                  onPressed: _currentPage > 0 ? () {
                    setState(() {
                      _currentPage--;
                    });
                    _loadEntries();
                  } : null,
                  icon: const Icon(Icons.chevron_left),
                ),
                IconButton(
                  onPressed: _currentPage < _totalPages - 1 ? () {
                    setState(() {
                      _currentPage++;
                    });
                    _loadEntries();
                  } : null,
                  icon: const Icon(Icons.chevron_right),
                ),
              ],
            ),
          ),

          // Data table
          Expanded(
            child: Card(
              margin: const EdgeInsets.all(16),
              child: _isLoading || _isPopulating
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          CircularProgressIndicator(),
                          SizedBox(height: 16),
                          Text('Loading data...'),
                        ],
                      ),
                    )
                  : _entries.isEmpty
                      ? const Center(child: Text('No entries found'))
                      : DataTable2(
                          columnSpacing: 12,
                          horizontalMargin: 12,
                          minWidth: 1200,
                          columns: const [
                            DataColumn2(label: Text('ASIN'), size: ColumnSize.L),
                            DataColumn2(label: Text('Seller ID & Controls'), size: ColumnSize.L),
                            DataColumn2(label: Text('SKU'), size: ColumnSize.M),
                            DataColumn2(label: Text('Region'), size: ColumnSize.S),
                            DataColumn2(label: Text('Min Price'), size: ColumnSize.S),
                            DataColumn2(label: Text('Listed Price'), size: ColumnSize.S),
                            DataColumn2(label: Text('Max Price'), size: ColumnSize.S),
                            DataColumn2(label: Text('Strategy'), size: ColumnSize.M),
                            DataColumn2(label: Text('Status'), size: ColumnSize.S),
                            DataColumn2(label: Text('Repricing'), size: ColumnSize.S),
                            DataColumn2(label: Text('Calculated Price'), size: ColumnSize.S),
                          ],
                          rows: _entries.map((entry) {
                            return DataRow2(
                              onTap: () => _showSQSDialog(entry),
                              cells: [
                                DataCell(Text(entry.asin)),
                                DataCell(
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(entry.sellerId, style: const TextStyle(fontSize: 12)),
                                      const SizedBox(height: 4),
                                      Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          ElevatedButton(
                                            onPressed: () => _triggerReset(entry.sellerId),
                                            style: ElevatedButton.styleFrom(
                                              backgroundColor: Colors.orange,
                                              foregroundColor: Colors.white,
                                              minimumSize: const Size(60, 24),
                                              padding: const EdgeInsets.symmetric(horizontal: 8),
                                            ),
                                            child: const Text('Reset', style: TextStyle(fontSize: 10)),
                                          ),
                                          const SizedBox(width: 4),
                                          ElevatedButton(
                                            onPressed: () => _triggerResume(entry.sellerId),
                                            style: ElevatedButton.styleFrom(
                                              backgroundColor: Colors.green,
                                              foregroundColor: Colors.white,
                                              minimumSize: const Size(60, 24),
                                              padding: const EdgeInsets.symmetric(horizontal: 8),
                                            ),
                                            child: const Text('Resume', style: TextStyle(fontSize: 10)),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                                DataCell(Text(entry.sku)),
                                DataCell(Text(entry.region ?? 'N/A')),
                                DataCell(Text(_formatPrice(entry.productData.minPrice, entry.region ?? 'us'))),
                                DataCell(Text(_formatPrice(entry.productData.listedPrice, entry.region ?? 'us'))),
                                DataCell(Text(_formatPrice(entry.productData.maxPrice, entry.region ?? 'us'))),
                                DataCell(Text(entry.strategy?.type ?? 'N/A')),
                                DataCell(Text(entry.productData.status ?? 'N/A')),
                                DataCell(
                                  entry.repricingPaused
                                      ? const Icon(Icons.pause_circle, color: Colors.red, size: 16)
                                      : const Icon(Icons.play_circle, color: Colors.green, size: 16),
                                ),
                                DataCell(Text(_formatPrice(entry.calculatedPrice?.newPrice, entry.region ?? 'us'))),
                              ],
                            );
                          }).toList(),
                        ),
            ),
          ),
        ],
      ),
    );
  }
}