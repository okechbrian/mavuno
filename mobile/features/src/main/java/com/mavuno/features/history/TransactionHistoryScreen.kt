package com.mavuno.features.history

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.SimpleDateFormat
import java.util.*

data class Transaction(
    val id: String,
    val type: String,
    val amount: String,
    val date: Long,
    val status: String
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TransactionHistoryScreen(
    title: String = "History",
    transactions: List<Transaction> = emptyList()
) {
    Scaffold(
        topBar = {
            TopAppBar(title = { Text(title) })
        }
    ) { padding ->
        if (transactions.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = androidx.compose.ui.Alignment.Center) {
                Text("No transactions found", color = Color.Gray)
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(transactions) { tx ->
                    TransactionCard(tx)
                }
            }
        }
    }
}

@Composable
fun TransactionCard(tx: Transaction) {
    val sdf = SimpleDateFormat("dd MMM, HH:mm", Locale.getDefault())
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(modifier = Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Icon(Icons.Default.Receipt, contentDescription = null, tint = Color.Gray)
            Column(modifier = Modifier.weight(1f)) {
                Text(text = tx.type, fontWeight = FontWeight.Bold)
                Text(text = sdf.format(Date(tx.date)), fontSize = 12.sp, color = Color.Gray)
            }
            Column(horizontalAlignment = androidx.compose.ui.Alignment.End) {
                Text(text = tx.amount, fontWeight = FontWeight.Bold, color = if (tx.amount.startsWith("+")) Color(0xFF2E7D32) else Color.Black)
                Text(text = tx.status, fontSize = 10.sp, color = Color.Gray)
            }
        }
    }
}
