package com.mavuno.features.training

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.domain.model.TrainingModule
import com.mavuno.domain.repository.TrainingRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.onStart
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface TrainingUiState {
    object Loading : TrainingUiState
    data class Success(val modules: List<TrainingModule>) : TrainingUiState
    data class Error(val message: String) : TrainingUiState
}

@HiltViewModel
class TrainingViewModel @Inject constructor(
    private val repository: TrainingRepository
) : ViewModel() {

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    val uiState: StateFlow<TrainingUiState> = repository.getTrainingModules()
        .map { modules ->
            _isRefreshing.value = false
            TrainingUiState.Success(modules) as TrainingUiState
        }
        .onStart { emit(TrainingUiState.Loading) }
        .catch { e ->
            _isRefreshing.value = false
            emit(TrainingUiState.Error(e.message ?: "Unknown error occurred"))
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = TrainingUiState.Loading
        )

    fun onMarkCompleted(moduleId: String) {
        viewModelScope.launch {
            repository.markModuleCompleted(moduleId).collect { success ->
                // The Room DB update triggers the underlying flow to re-emit seamlessly.
                // We could emit a side-effect here (like a snackbar trigger) if needed.
            }
        }
    }

    fun refresh() {
        _isRefreshing.value = true
        // This simulates a pull-to-refresh. In a production scenario, you would expose 
        // a `sync()` method on the repository to forcefully re-fetch from the network.
        viewModelScope.launch {
            kotlinx.coroutines.delay(1000)
            _isRefreshing.value = false
        }
    }
}
