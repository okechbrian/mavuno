package com.mavuno.features.social

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.TrendingDown
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mavuno.domain.model.PriceSeriesPoint

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PriceHistoryScreen(
    viewModel: PriceHistoryViewModel,
    crop: String,
    region: String
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(crop, region) {
        viewModel.loadPriceHistory(crop, region)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Price Trends: ${crop.uppercase()}") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1B4332),
                    titleContentColor = Color.White
                )
            )
        }
    ) { padding ->
        if (uiState.isLoading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Color(0xFF1B4332))
            }
        } else {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                PriceSummaryCard(uiState)
                
                Spacer(modifier = Modifier.height(32.dp))
                
                Text(
                    text = "7-Day Price History",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.align(Alignment.Start)
                )
                
                Spacer(modifier = Modifier.height(16.dp))

                if (uiState.series.isNotEmpty()) {
                    SimpleLineChart(points = uiState.series)
                }
                
                Spacer(modifier = Modifier.height(24.dp))
                
                Text(
                    text = "Local market data for ${uiState.region} region. Updated daily.",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.Gray
                )
            }
        }
    }
}

@Composable
fun SimpleLineChart(points: List<PriceSeriesPoint>) {
    val maxVal = points.maxOfOrNull { it.ugx }?.toFloat() ?: 1f
    val minVal = points.minOfOrNull { it.ugx }?.toFloat() ?: 0f
    val range = (maxVal - minVal).coerceAtLeast(1f)
    
    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(200.dp)
            .padding(16.dp)
    ) {
        val width = size.width
        val height = size.height
        val xStep = width / (points.size - 1).coerceAtLeast(1)
        
        val path = Path()
        points.forEachIndexed { index, point ->
            val x = index * xStep
            val normalizedY = 1f - ((point.ugx - minVal) / range)
            val y = normalizedY * height
            
            if (index == 0) {
                path.moveTo(x, y)
            } else {
                path.lineTo(x, y)
            }
        }
        
        drawPath(
            path = path,
            color = Color(0xFF1B4332),
            style = Stroke(
                width = 4.dp.toPx(),
                cap = StrokeCap.Round,
                join = StrokeJoin.Round
            )
        )
    }
}

@Composable
fun PriceSummaryCard(state: PriceHistoryUiState) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier.padding(24.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Text(text = "Current Price", fontSize = 12.sp, color = Color.Gray)
                Text(
                    text = "UGX ${state.todayPrice}/KG",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color = Color(0xFF1B4332)
                )
            }
            
            val trendColor = when(state.trend) {
                "up" -> Color(0xFF2E7D32)
                "down" -> Color(0xFFC62828)
                else -> Color.Gray
            }
            
            val trendIcon = when(state.trend) {
                "up" -> Icons.Default.TrendingUp
                "down" -> Icons.Default.TrendingDown
                else -> null
            }

            Surface(
                color = trendColor.copy(alpha = 0.1f),
                shape = RoundedCornerShape(12.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (trendIcon != null) {
                        Icon(trendIcon, contentDescription = null, tint = trendColor, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                    }
                    Text(
                        text = state.trend.uppercase(),
                        fontWeight = FontWeight.Bold,
                        fontSize = 12.sp,
                        color = trendColor
                    )
                }
            }
        }
    }
}
