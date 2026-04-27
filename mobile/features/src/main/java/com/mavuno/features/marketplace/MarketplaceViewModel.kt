package com.mavuno.features.marketplace

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.domain.model.MarketPrices
import com.mavuno.domain.model.Offer
import com.mavuno.domain.repository.MarketplaceRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MarketplaceUiState(
    val isLoading: Boolean = true,
    val offers: List<Offer> = emptyList(),
    val error: String? = null,
    val isPlacingBid: Boolean = false,
    val bidError: String? = null
)

@HiltViewModel
class MarketplaceViewModel @Inject constructor(
    private val repository: MarketplaceRepository
) : ViewModel() {

    private val _searchQuery = MutableStateFlow("")
    val searchQuery = _searchQuery.asStateFlow()

    private val _selectedCategory = MutableStateFlow("All")
    val selectedCategory = _selectedCategory.asStateFlow()

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing = _isRefreshing.asStateFlow()

    private val _marketPrices = MutableStateFlow<MarketPrices?>(null)
    val marketPrices = _marketPrices.asStateFlow()
    
    private val _baseUiState = MutableStateFlow(MarketplaceUiState())

    val uiState: StateFlow<MarketplaceUiState> = combine(
        repository.getOpenOffers(),
        _searchQuery,
        _selectedCategory,
        _baseUiState
    ) { offers, query, category, baseState ->
        val filtered = offers.filter { offer ->
            val matchesQuery = offer.crop.contains(query, ignoreCase = true) || 
                               offer.farmerName.contains(query, ignoreCase = true)
            val matchesCategory = category == "All" || offer.crop.equals(category, ignoreCase = true)
            matchesQuery && matchesCategory
        }
        baseState.copy(isLoading = false, offers = filtered)
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = MarketplaceUiState()
    )

    fun onSearchQueryChanged(query: String) {
        _searchQuery.value = query
    }

    fun onCategorySelected(category: String) {
        _selectedCategory.value = category
    }

    fun refresh() {
        viewModelScope.launch {
            _isRefreshing.value = true
            repository.syncMarketplace()
            delay(1000) // Simulated UX delay for network jitter
            _isRefreshing.value = false
        }
    }

    fun loadPriceHistory(crop: String, region: String) {
        viewModelScope.launch {
            try {
                _marketPrices.value = repository.getMarketPrices(crop, region)
            } catch (e: Exception) {
                _marketPrices.value = null
            }
        }
    }

    fun placeBid(offerId: String, msisdn: String, onResult: (Boolean) -> Unit) {
        viewModelScope.launch {
            _baseUiState.value = _baseUiState.value.copy(isPlacingBid = true, bidError = null)
            repository.placeBid(offerId, msisdn).catch { e ->
                _baseUiState.value = _baseUiState.value.copy(
                    isPlacingBid = false,
                    bidError = e.message ?: "An unexpected error occurred"
                )
                onResult(false)
            }.collect { success ->
                if (success) {
                    _baseUiState.value = _baseUiState.value.copy(isPlacingBid = false)
                } else {
                    _baseUiState.value = _baseUiState.value.copy(
                        isPlacingBid = false,
                        bidError = "Failed to place bid. Please verify payment details."
                    )
                }
                onResult(success)
            }
        }
    }
    
    fun clearBidError() {
        _baseUiState.value = _baseUiState.value.copy(bidError = null)
    }
}
