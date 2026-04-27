package com.mavuno.features.social

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mavuno.domain.model.SocialPost
import com.mavuno.domain.repository.SocialRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SocialFeedUiState(
    val isLoading: Boolean = true,
    val posts: List<SocialPost> = emptyList(),
    val isRefreshing: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class SocialFeedViewModel @Inject constructor(
    private val socialRepository: SocialRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(SocialFeedUiState())
    val uiState: StateFlow<SocialFeedUiState> = _uiState.asStateFlow()

    init {
        loadFeed(isInitial = true)
    }

    fun loadFeed(district: String? = null, isInitial: Boolean = false) {
        viewModelScope.launch {
            if (isInitial) {
                _uiState.value = _uiState.value.copy(isLoading = true)
            } else {
                _uiState.value = _uiState.value.copy(isRefreshing = true)
            }
            
            try {
                socialRepository.syncFeed(district)
            } catch (e: Exception) {
                // Ignore sync errors, fall back to cache
            }

            socialRepository.getFeed(district)
                .catch { e ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isRefreshing = false,
                        error = e.message
                    )
                }
                .collect { posts ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        isRefreshing = false,
                        posts = posts
                    )
                }
        }
    }

    fun refresh(district: String? = null) {
        loadFeed(district, isInitial = false)
    }

    fun createPost(body: String, isVerified: Boolean = false) {
        viewModelScope.launch {
            try {
                socialRepository.createPost(body, null, isVerified)
                refresh() // Refresh feed after posting
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message)
            }
        }
    }

    fun reactToPost(postId: String, emoji: String) {
        viewModelScope.launch {
            try {
                socialRepository.reactToPost(postId, emoji)
                // Local state is updated via the repository flow
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message)
            }
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
