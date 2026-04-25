package com.mavuno.features.farmer

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mavuno.core.R

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FarmerDashboardScreen(
    viewModel: FarmerDashboardViewModel,
    farmId: String
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(farmId) {
        viewModel.loadDashboard(farmId)
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text(stringResource(R.string.farmer_app_title), fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = Color(0xFF2E7D32),
                    titleContentColor = Color.White
                )
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(Color(0xFFF1F8E9))
        ) {
            if (uiState.isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    uiState.farmer?.let { farmer ->
                        FarmerInfoCard(farmer.name, farmer.farmId)
                        YpsScoreCard(farmer.ypsScore)
                    }

                    uiState.ectBalance?.let { balance ->
                        EctBalanceCard(balance.balance)
                    }
                    
                    Spacer(modifier = Modifier.weight(1f))
                    
                    Button(
                        onClick = { /* Navigate to CRP Chat */ },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(64.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32))
                    ) {
                        Text(stringResource(R.string.chat_agronomist), fontSize = 18.sp)
                    }
                }
            }
        }
    }
}

@Composable
fun FarmerInfoCard(name: String, farmId: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = stringResource(R.string.welcome_back), fontSize = 14.sp, color = Color.Gray)
            Text(text = name, fontSize = 24.sp, fontWeight = FontWeight.Bold, color = Color.Black)
            Text(text = stringResource(R.string.farm_id_label, farmId), fontSize = 12.sp, color = Color.Gray)
        }
    }
}

@Composable
fun YpsScoreCard(score: Int) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F5E9)),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(text = stringResource(R.string.yps_title), fontSize = 14.sp, color = Color.DarkGray)
                Text(text = "$score%", fontSize = 32.sp, fontWeight = FontWeight.ExtraBold, color = Color(0xFF2E7D32))
            }
        }
    }
}

@Composable
fun EctBalanceCard(balance: Double) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1B5E20)),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = stringResource(R.string.ect_balance_title), fontSize = 14.sp, color = Color.White.copy(alpha = 0.7f))
            Text(text = "${String.format("%.2f", balance)} ECT", fontSize = 36.sp, fontWeight = FontWeight.Bold, color = Color.White)
            Text(text = stringResource(R.string.approx_ugx, String.format("%.0f", balance * 1000)), fontSize = 14.sp, color = Color.White.copy(alpha = 0.9f))
        }
    }
}
