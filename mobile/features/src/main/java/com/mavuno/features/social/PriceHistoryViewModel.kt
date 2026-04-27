package com.mavuno.features.social

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.domain.model.PriceSeriesPoint
import com.mavuno.domain.repository.MarketplaceRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PriceHistoryUiState(
    val isLoading: Boolean = true,
    val series: List<PriceSeriesPoint> = emptyList(),
    val crop: String = "",
    val region: String = "",
    val todayPrice: Int = 0,
    val trend: String = "flat",
    val error: String? = null
)

@HiltViewModel
class PriceHistoryViewModel @Inject constructor(
    private val marketplaceRepository: MarketplaceRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(PriceHistoryUiState())
    val uiState = _uiState.asStateFlow()

    fun loadPriceHistory(crop: String, region: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, crop = crop, region = region)
            try {
                val data = marketplaceRepository.getMarketPrices(crop, region)
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    series = data.series,
                    todayPrice = data.today.ugx,
                    trend = data.trend
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
            }
        }
    }
}
