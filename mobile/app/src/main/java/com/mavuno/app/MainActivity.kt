package com.mavuno.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.navigation.compose.rememberNavController
import com.mavuno.app.navigation.MavunoNavGraph
import com.mavuno.core.R
import com.mavuno.features.auth.LoginScreen
import com.mavuno.features.verification.TokenVerifier
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var tokenVerifier: TokenVerifier

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                var loggedInFarmId by remember { mutableStateOf<String?>(null) }

                if (loggedInFarmId == null) {
                    LoginScreen(
                        role = "Farmer",
                        logoResId = R.drawable.ic_farmer_logo,
                        onLoginSuccess = { loggedInFarmId = it }
                    )
                } else {
                    val navController = rememberNavController()
                    MavunoNavGraph(
                        navController = navController,
                        tokenVerifier = tokenVerifier,
                        farmId = loggedInFarmId!!
                    )
                }
            }
        }
    }
}
