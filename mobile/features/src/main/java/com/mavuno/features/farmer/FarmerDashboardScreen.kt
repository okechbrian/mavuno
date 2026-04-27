package com.mavuno.features.farmer

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mavuno.core.R
import com.mavuno.core.ui.YpsMeter
import com.mavuno.core.ui.getYpsColor
import com.mavuno.core.ui.getYpsLabel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FarmerDashboardScreen(
    viewModel: FarmerDashboardViewModel,
    farmId: String,
    onNavigateToTraining: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    var showChatDialog by remember { mutableStateOf(false) }
    var chatQuestion by remember { mutableStateOf("") }

    LaunchedEffect(farmId) {
        viewModel.loadDashboard(farmId)
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Mavuno Workspace", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = Color(0xFF1B4332),
                    titleContentColor = Color.White
                ),
                actions = {
                    IconButton(onClick = { showChatDialog = true }) {
                        Icon(Icons.Default.SmartToy, contentDescription = "Ask AI", tint = Color.White)
                    }
                }
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(Color(0xFFFDF6E3))
        ) {
            if (uiState.isLoading) {
                CircularProgressIndicator(color = Color(0xFF1B4332), modifier = Modifier.align(Alignment.Center))
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(20.dp)
                ) {
                    item {
                        uiState.farmer?.let { farmer ->
                            TopGreeting(name = farmer.name, farmId = farmer.farmId, ypsScore = farmer.ypsScore)
                        }
                    }

                    item {
                        QuickStatsRow(
                            totalHarvests = uiState.totalHarvestsCount,
                            activeOffers = uiState.activeOffersCount,
                            ectBalance = uiState.ectBalance?.balance ?: 0.0
                        )
                    }

                    item {
                        QuickActionGrid(
                            onNavigateToTraining = onNavigateToTraining,
                            onPingSensor = { viewModel.pingSensor(farmId) }
                        )
                    }

                    item {
                        uiState.marketPrices?.let { prices ->
                            MarketInsightCard(prices)
                        }
                    }

                    item {
                        RecentActivitySection()
                    }
                }
            }

            uiState.error?.let {
                Snackbar(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(16.dp)
                ) { Text(it) }
            }
        }
    }

    if (showChatDialog) {
        AlertDialog(
            onDismissRequest = { 
                showChatDialog = false 
                viewModel.clearAiAnswer()
            },
            title = { Text("Ask Mavuno AI", color = Color(0xFF1B4332), fontWeight = FontWeight.Bold) },
            text = {
                Column {
                    OutlinedTextField(
                        value = chatQuestion,
                        onValueChange = { chatQuestion = it },
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("How can I improve my yield?") },
                        minLines = 3
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    uiState.aiAnswer?.let { answer ->
                        Surface(
                            color = Color(0xFFE8F5E9),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = answer,
                                modifier = Modifier.padding(12.dp),
                                fontSize = 14.sp
                            )
                        }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = { viewModel.askAdvisor(farmId, chatQuestion) },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32))
                ) {
                    Text("Ask AI")
                }
            },
            dismissButton = {
                TextButton(onClick = { 
                    showChatDialog = false
                    viewModel.clearAiAnswer()
                }) {
                    Text("Close", color = Color.Gray)
                }
            }
        )
    }
}

@Composable
fun TopGreeting(name: String, farmId: String, ypsScore: Int) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column {
            Text(text = "Welcome back,", fontSize = 14.sp, color = Color.Gray)
            Text(text = name, fontSize = 24.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1B4332))
            Text(text = "Farm ID: $farmId", fontSize = 12.sp, color = Color.Gray)
        }
        
        // Small YPS badge
        Surface(
            color = Color.White,
            shape = RoundedCornerShape(12.dp),
            shadowElevation = 2.dp
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                YpsMeter(score = ypsScore, size = 40.dp, strokeWidth = 4.dp, accentColor = getYpsColor(ypsScore))
                Column {
                    Text("YPS", fontSize = 10.sp, color = Color.Gray, fontWeight = FontWeight.Bold)
                    Text(getYpsLabel(ypsScore), fontSize = 12.sp, fontWeight = FontWeight.Bold, color = getYpsColor(ypsScore))
                }
            }
        }
    }
}

@Composable
fun QuickStatsRow(totalHarvests: Int, activeOffers: Int, ectBalance: Double) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        StatCard(
            modifier = Modifier.weight(1f),
            title = "Harvests",
            value = totalHarvests.toString(),
            icon = Icons.Default.Agriculture,
            color = Color(0xFFD35400)
        )
        StatCard(
            modifier = Modifier.weight(1f),
            title = "Offers",
            value = activeOffers.toString(),
            icon = Icons.Default.Store,
            color = Color(0xFF1565C0)
        )
        StatCard(
            modifier = Modifier.weight(1f),
            title = "ECT Bal",
            value = String.format("%.1f", ectBalance),
            icon = Icons.Default.Bolt,
            color = Color(0xFF2E7D32)
        )
    }
}

@Composable
fun StatCard(modifier: Modifier = Modifier, title: String, value: String, icon: androidx.compose.ui.graphics.vector.ImageVector, color: Color) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(24.dp))
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = value, fontSize = 20.sp, fontWeight = FontWeight.ExtraBold, color = Color.Black)
            Text(text = title, fontSize = 10.sp, color = Color.Gray, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
fun QuickActionGrid(onNavigateToTraining: () -> Unit, onPingSensor: () -> Unit) {
    Text(text = "Quick Actions", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1B4332), modifier = Modifier.padding(bottom = 8.dp))
    
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        ActionCard(
            modifier = Modifier.weight(1f),
            title = "List Produce",
            icon = Icons.Default.AddShoppingCart,
            color = Color(0xFF1565C0),
            onClick = { /* TODO: List offer */ }
        )
        ActionCard(
            modifier = Modifier.weight(1f),
            title = "Academy",
            icon = Icons.Default.School,
            color = Color(0xFF2E7D32),
            onClick = onNavigateToTraining
        )
    }
    Spacer(modifier = Modifier.height(12.dp))
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        ActionCard(
            modifier = Modifier.weight(1f),
            title = "Community",
            icon = Icons.Default.Groups,
            color = Color(0xFFD35400),
            onClick = { /* App handles bottom nav */ }
        )
        ActionCard(
            modifier = Modifier.weight(1f),
            title = "Ping Sensor",
            icon = Icons.Default.Sensors,
            color = Color(0xFF37474F),
            onClick = onPingSensor
        )
    }
}

@Composable
fun ActionCard(modifier: Modifier = Modifier, title: String, icon: androidx.compose.ui.graphics.vector.ImageVector, color: Color, onClick: () -> Unit) {
    Card(
        modifier = modifier.clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = RoundedCornerShape(16.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = color.copy(alpha = 0.1f)
            ) {
                Icon(icon, contentDescription = null, tint = color, modifier = Modifier.padding(8.dp).size(24.dp))
            }
            Spacer(modifier = Modifier.width(12.dp))
            Text(text = title, fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color.Black)
        }
    }
}

@Composable
fun MarketInsightCard(marketPrices: com.mavuno.domain.model.MarketPrices) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("Market Insights", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = Color(0xFF1B4332))
                Surface(color = Color(0xFFE8F5E9), shape = RoundedCornerShape(4.dp)) {
                    Text(marketPrices.crop.uppercase(), fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color(0xFF2E7D32), modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp))
                }
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Row(verticalAlignment = Alignment.Bottom) {
                Text("UGX ${marketPrices.today.ugx}", fontSize = 28.sp, fontWeight = FontWeight.ExtraBold, color = Color.Black)
                Text("/${marketPrices.unit}", fontSize = 14.sp, color = Color.Gray, modifier = Modifier.padding(bottom = 4.dp, start = 4.dp))
            }
            
            val trendColor = if (marketPrices.trend == "up") Color(0xFF2E7D32) else if (marketPrices.trend == "down") Color(0xFFC62828) else Color.Gray
            Text("7d Avg: UGX ${marketPrices.last7Avg} • ${marketPrices.trend.uppercase()}", fontSize = 12.sp, color = trendColor, fontWeight = FontWeight.Medium)
            
            Spacer(modifier = Modifier.height(16.dp))
            
            // Simplified mini-chart placeholder using simple boxes or just a text note for now to avoid Vico alpha issues
            Box(modifier = Modifier.fillMaxWidth().height(60.dp).background(Color(0xFFF1F8E9), RoundedCornerShape(8.dp)), contentAlignment = Alignment.Center) {
                Text("Vico Chart Placeholder", fontSize = 10.sp, color = Color.Gray)
            }
        }
    }
}

@Composable
fun RecentActivitySection() {
    Text(text = "Recent Activity", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1B4332), modifier = Modifier.padding(bottom = 8.dp))
    
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(0.dp)) {
            ActivityRow(icon = Icons.Default.CheckCircle, title = "Offer Accepted", desc = "500 KG Coffee by NABASUMBA", time = "2 hrs ago", color = Color(0xFF2E7D32))
            HorizontalDivider(color = Color.LightGray.copy(alpha = 0.3f))
            ActivityRow(icon = Icons.Default.Bolt, title = "ECT Issued", desc = "+12.5 kWh based on YPS", time = "1 day ago", color = Color(0xFFD35400))
            HorizontalDivider(color = Color.LightGray.copy(alpha = 0.3f))
            ActivityRow(icon = Icons.Default.Verified, title = "Certification", desc = "Regenerative Cultivation", time = "3 days ago", color = Color(0xFF1565C0))
        }
    }
}

@Composable
fun ActivityRow(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, desc: String, time: String, color: Color) {
    Row(
        modifier = Modifier.padding(16.dp).fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(20.dp))
        Spacer(modifier = Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(text = title, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Text(text = desc, fontSize = 12.sp, color = Color.Gray, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        Text(text = time, fontSize = 10.sp, color = Color.Gray)
    }
}
