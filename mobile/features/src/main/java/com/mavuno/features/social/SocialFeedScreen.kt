package com.mavuno.features.social

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ShowChart
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshContainer
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import com.mavuno.core.ui.YpsMeter
import com.mavuno.core.ui.getYpsColor
import com.mavuno.core.util.ImageCompressor
import com.mavuno.domain.model.SocialPost
import java.io.File

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SocialFeedScreen(
    viewModel: SocialFeedViewModel,
    userRole: String // "farmer", "buyer", "agent"
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    var showCreateDialog by remember { mutableStateOf(false) }
    var selectedCropForTrends by remember { mutableStateOf<Pair<String, String>?>(null) }
    
    val pullRefreshState = rememberPullToRefreshState()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    if (pullRefreshState.isRefreshing) {
        LaunchedEffect(true) {
            viewModel.refresh()
        }
    }

    LaunchedEffect(uiState.isRefreshing) {
        if (uiState.isRefreshing) {
            pullRefreshState.startRefresh()
        } else {
            pullRefreshState.endRefresh()
        }
    }

    val errorMessage = uiState.error
    LaunchedEffect(errorMessage) {
        errorMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearError()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Mavuno Community", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1B4332),
                    titleContentColor = Color(0xFFFDF6E3)
                )
            )
        },
        floatingActionButton = {
            if (userRole == "farmer" || userRole == "agent") {
                FloatingActionButton(
                    onClick = { showCreateDialog = true },
                    containerColor = Color(0xFFD35400),
                    contentColor = Color.White
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Create Post")
                }
            }
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        containerColor = Color(0xFFFDF6E3)
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .nestedScroll(pullRefreshState.nestedScrollConnection)
        ) {
            if (uiState.isLoading) {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    items(5) { ShimmerPostCard() }
                }
            } else if (uiState.posts.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("No updates yet. Be the first to share!", color = Color.Gray)
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    items(uiState.posts, key = { it.id }) { post ->
                        SocialPostCard(
                            post = post,
                            onLike = { viewModel.reactToPost(post.id, "👍") },
                            onViewTrends = { selectedCropForTrends = post.crop to post.district }
                        )
                    }
                }
            }

            PullToRefreshContainer(
                state = pullRefreshState,
                modifier = Modifier.align(Alignment.TopCenter),
                containerColor = Color.White,
                contentColor = Color(0xFF1B4332)
            )
        }
    }

    if (showCreateDialog) {
        CreatePostDialog(
            onDismiss = { showCreateDialog = false },
            onConfirm = { body, isVerified ->
                viewModel.createPost(body, isVerified)
                showCreateDialog = false
            }
        )
    }

    if (selectedCropForTrends != null) {
        ModalBottomSheet(
            onDismissRequest = { selectedCropForTrends = null },
            containerColor = Color(0xFFFDF6E3)
        ) {
            PriceHistoryScreen(
                viewModel = hiltViewModel(),
                crop = selectedCropForTrends!!.first,
                region = selectedCropForTrends!!.second
            )
        }
    }
}

@Composable
fun SocialPostCard(
    post: SocialPost,
    onLike: () -> Unit,
    onViewTrends: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(Color(0xFFE8F5E9)),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = post.farmerName.take(1),
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1B4332)
                    )
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(text = post.farmerName, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                        if (post.isVerified) {
                            Spacer(modifier = Modifier.width(4.dp))
                            Icon(
                                Icons.Default.Verified,
                                contentDescription = "Verified",
                                tint = Color(0xFFD35400),
                                modifier = Modifier.size(16.dp)
                            )
                        }
                    }
                    Text(text = "${post.district} • ${post.crop}", fontSize = 12.sp, color = Color.Gray)
                }
                Spacer(modifier = Modifier.weight(1f))
                post.yps?.let { yps ->
                    YpsMeter(
                        score = yps,
                        size = 36.dp,
                        strokeWidth = 4.dp,
                        accentColor = getYpsColor(yps)
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            if (post.body.startsWith("🌱 Public Query:")) {
                Surface(
                    color = Color(0xFFF1F8E9),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = post.body,
                        modifier = Modifier.padding(12.dp),
                        fontSize = 14.sp,
                        fontStyle = FontStyle.Italic,
                        color = Color(0xFF1B4332)
                    )
                }
            } else {
                Text(text = post.body, fontSize = 15.sp, lineHeight = 20.sp, color = Color.Black)
            }

            if (!post.photoUrl.isNullOrEmpty()) {
                Spacer(modifier = Modifier.height(16.dp))
                AsyncImage(
                    model = post.photoUrl,
                    contentDescription = "Post Image",
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(200.dp)
                        .clip(RoundedCornerShape(16.dp)),
                    contentScale = ContentScale.Crop
                )
            }

            Spacer(modifier = Modifier.height(16.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    val likes = post.reactions["👍"] ?: 0
                    AssistChip(
                        onClick = onLike,
                        label = { Text("👍 $likes") },
                        colors = AssistChipDefaults.assistChipColors(
                            containerColor = if (likes > 0) Color(0xFFE8F5E9) else Color.Transparent
                        )
                    )
                    
                    AssistChip(
                        onClick = { /* TODO: Comments */ },
                        label = { Text("💬") }
                    )
                }
                
                TextButton(onClick = onViewTrends) {
                    Icon(Icons.AutoMirrored.Filled.ShowChart, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Trends", fontSize = 12.sp)
                }
            }
        }
    }
}

@Composable
fun ShimmerPostCard() {
    val shimmerColors = listOf(
        Color.LightGray.copy(alpha = 0.6f),
        Color.LightGray.copy(alpha = 0.2f),
        Color.LightGray.copy(alpha = 0.6f),
    )

    val transition = rememberInfiniteTransition(label = "shimmer")
    val translateAnim by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1000f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "translate"
    )

    val brush = Brush.linearGradient(
        colors = shimmerColors,
        start = Offset.Zero,
        end = Offset(x = translateAnim, y = translateAnim)
    )

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(modifier = Modifier.size(40.dp).clip(CircleShape).background(brush))
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Box(modifier = Modifier.width(100.dp).height(14.dp).background(brush, RoundedCornerShape(4.dp)))
                    Spacer(modifier = Modifier.height(6.dp))
                    Box(modifier = Modifier.width(60.dp).height(10.dp).background(brush, RoundedCornerShape(4.dp)))
                }
            }
            Spacer(modifier = Modifier.height(16.dp))
            Box(modifier = Modifier.fillMaxWidth().height(16.dp).background(brush, RoundedCornerShape(4.dp)))
            Spacer(modifier = Modifier.height(8.dp))
            Box(modifier = Modifier.fillMaxWidth(0.7f).height(16.dp).background(brush, RoundedCornerShape(4.dp)))
            Spacer(modifier = Modifier.height(16.dp))
            Box(modifier = Modifier.fillMaxWidth().height(150.dp).background(brush, RoundedCornerShape(16.dp)))
        }
    }
}

@Composable
fun CreatePostDialog(onDismiss: () -> Unit, onConfirm: (String, Boolean) -> Unit) {
    val context = LocalContext.current
    var text by remember { mutableStateOf("") }
    var isVerified by remember { mutableStateOf(false) }
    var capturedImageUri by remember { mutableStateOf<Uri?>(null) }
    
    val tempFile = remember { File.createTempFile("social_capture_", ".jpg", context.cacheDir) }
    val tempUri = remember { 
        FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", tempFile)
    }

    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture(),
        onResult = { success ->
            if (success) capturedImageUri = tempUri
        }
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Share Farm Update", fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = text,
                    onValueChange = { text = it },
                    placeholder = { Text("What's happening on the farm?") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 3,
                    shape = RoundedCornerShape(12.dp)
                )
                
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.clickable { isVerified = !isVerified }
                ) {
                    Checkbox(checked = isVerified, onCheckedChange = { isVerified = it })
                    Text("Verified Harvest", fontSize = 14.sp)
                }

                if (isVerified) {
                    if (capturedImageUri != null) {
                        AsyncImage(
                            model = capturedImageUri,
                            contentDescription = "Captured Proof",
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(150.dp)
                                .clip(RoundedCornerShape(12.dp)),
                            contentScale = ContentScale.Crop
                        )
                        OutlinedButton(
                            onClick = { cameraLauncher.launch(tempUri) },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Icon(Icons.Default.CameraAlt, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text("Retake Photo")
                        }
                    } else {
                        Button(
                            onClick = { cameraLauncher.launch(tempUri) },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(8.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B4332))
                        ) {
                            Icon(Icons.Default.CameraAlt, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text("Capture Proof Photo")
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { 
                    if (isVerified && capturedImageUri != null) {
                        ImageCompressor.compressToWebp(context, capturedImageUri!!)
                    }
                    onConfirm(text, isVerified) 
                },
                enabled = text.isNotBlank() && (!isVerified || capturedImageUri != null),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B4332))
            ) {
                Text("Post")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel", color = Color.Gray)
            }
        }
    )
}
