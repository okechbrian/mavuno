package com.mavuno.features.auth

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mavuno.core.R

@Composable
fun LoginScreen(
    role: String,
    logoResId: Int,
    onLoginSuccess: (String) -> Unit
) {
    var userId by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var isLoading by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Image(
            painter = painterResource(id = logoResId),
            contentDescription = "Mavuno Logo",
            modifier = Modifier.size(100.dp)
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "Mavuno $role Login",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(32.dp))

        if (role != "Agent") {
            OutlinedTextField(
                value = userId,
                onValueChange = { userId = it },
                label = { Text(if (role == "Farmer") "Farm ID or Phone" else "Buyer ID or Phone") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
            Spacer(modifier = Modifier.height(16.dp))
        }

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text(if (role == "Agent") "Agent Password" else "PIN") },
            modifier = Modifier.fillMaxWidth(),
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = if (role == "Agent") KeyboardType.Text else KeyboardType.NumberPassword),
            singleLine = true
        )

        error?.let {
            Spacer(modifier = Modifier.height(8.dp))
            Text(text = it, color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
        }

        Spacer(modifier = Modifier.height(32.dp))

        Button(
            onClick = {
                isLoading = true
                // In a real app, this calls the MavunoApi login endpoint
                // Mocking success for the demo based on web defaults
                if (role == "Agent" && password == "mavuno2026") {
                    onLoginSuccess("admin")
                } else if (role == "Farmer" && (userId == "UG-MBL-0001" || userId == "+256700000001") && password == "1234") {
                    onLoginSuccess("UG-MBL-0001")
                } else if (role == "Buyer" && (userId == "BUYER-MBL-001" || userId == "+256700111222") && password == "1234") {
                    onLoginSuccess("BUYER-MBL-001")
                } else {
                    error = "Invalid credentials. Please try again."
                }
                isLoading = false
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = when (role) {
                    "Farmer" -> Color(0xFF2E7D32)
                    "Buyer" -> Color(0xFF1565C0)
                    else -> Color(0xFF37474F)
                }
            )
        ) {
            if (isLoading) {
                CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
            } else {
                Text("Login")
            }
        }
    }
}
