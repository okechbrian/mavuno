package com.mavuno.core.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun YpsMeter(
    score: Int,
    maxScore: Int = 100,
    size: Dp = 80.dp,
    strokeWidth: Dp = 8.dp,
    accentColor: Color = Color(0xFF2E7D32)
) {
    val sweepAngle by animateFloatAsState(
        targetValue = (score.toFloat() / maxScore.toFloat()) * 360f,
        animationSpec = tween(durationMillis = 1000),
        label = "YpsSweep"
    )

    Box(contentAlignment = Alignment.Center, modifier = Modifier.size(size)) {
        Canvas(modifier = Modifier.size(size)) {
            drawArc(
                color = Color.LightGray.copy(alpha = 0.3f),
                startAngle = -90f,
                sweepAngle = 360f,
                useCenter = false,
                style = Stroke(width = strokeWidth.toPx(), cap = StrokeCap.Round)
            )
            drawArc(
                color = accentColor,
                startAngle = -90f,
                sweepAngle = sweepAngle,
                useCenter = false,
                style = Stroke(width = strokeWidth.toPx(), cap = StrokeCap.Round)
            )
        }
        Text(
            text = score.toString(),
            fontSize = (size.value * 0.25).sp,
            fontWeight = FontWeight.Bold,
            color = Color.Black
        )
    }
}

fun getYpsColor(score: Int, maxScore: Int = 100): Color {
    val percentage = (score.toFloat() / maxScore.toFloat())
    return when {
        percentage >= 0.8f -> Color(0xFF2E7D32) // Excellent - Green
        percentage >= 0.5f -> Color(0xFFFFA000) // Good - Amber
        else -> Color(0xFFD32F2F) // Poor - Red
    }
}

fun getYpsLabel(score: Int, maxScore: Int = 100): String {
    val percentage = (score.toFloat() / maxScore.toFloat())
    return when {
        percentage >= 0.8f -> "Excellent"
        percentage >= 0.5f -> "Good"
        else -> "Poor"
    }
}
